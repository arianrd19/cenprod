# services/google_sheet_service.py
# -*- coding: utf-8 -*-
import os
import json
import time
import random
import unicodedata
import logging
from functools import wraps
from datetime import date, datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

try:
    import requests
except Exception:
    requests = None

try:
    from googleapiclient.errors import HttpError as GHttpError
except Exception:
    GHttpError = None

from config import Config

_log = logging.getLogger(__name__)  # logging en vez de print()


class GoogleSheetService:
    """Cliente de Google Sheets con caché, reintentos y conexión perezosa (lazy connect)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GoogleSheetService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Scopes mínimos para Sheets
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            # "https://www.googleapis.com/auth/drive.readonly",
        ]

        self.creds = None
        self.client = None
        self._sheet_cache = {}
        self._ws_cache = {}

        # Lazy connect: conecta recién en la primera operación
        self._initialized = True

    # ----------------------------------------------------------
    # Conexión
    # ----------------------------------------------------------
    def _connect(self):
        """
        Conecta usando:
          1) Archivo indicado por Config.SERVICE_ACCOUNT_FILE, o
          2) JSON completo en env (Config.SERVICE_ACCOUNT_JSON o GOOGLE_SERVICE_ACCOUNT).
        Valida token antes de autorizar gspread para atrapar errores temprano.
        """
        try:
            sa_path = getattr(Config, "SERVICE_ACCOUNT_FILE", None)
            if sa_path and os.path.exists(sa_path):
                self.creds = Credentials.from_service_account_file(sa_path, scopes=self.scopes)
            else:
                raw = getattr(Config, "SERVICE_ACCOUNT_JSON", None) or os.getenv("GOOGLE_SERVICE_ACCOUNT")
                if not raw:
                    raise FileNotFoundError("No hay credenciales: ni archivo ni JSON en env.")
                info = json.loads(raw)
                self.creds = Credentials.from_service_account_info(info, scopes=self.scopes)

            probe = self.creds.with_scopes(self.scopes)
            probe.refresh(Request())

            self.client = gspread.authorize(self.creds)
            _log.info("Conexión con Google Sheets establecida")
        except Exception as e:
            _log.error("Error al conectar con Google Sheets: %s", e, exc_info=True)
            raise

    def __ensure_client(self):
        """Asegura que la conexión esté lista antes de cualquier operación."""
        if self.client is None:
            self._connect()

    # ----------------------------------------------------------
    # Utilidades de reintento
    # ----------------------------------------------------------
    @staticmethod
    def _is_quota_error(e: Exception) -> bool:
        s = str(e).upper()
        return ("RESOURCE_EXHAUSTED" in s) or ("429" in s) or ("RATE_LIMIT" in s)

    @staticmethod
    def retry_on_quota(func):
        """Reintenta en caso de error de cuota o HTTP/API con backoff exponencial."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            max_retries = 4
            base = 1.4
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except gspread.exceptions.APIError as e:
                    if attempt < max_retries - 1 and GoogleSheetService._is_quota_error(e):
                        delay = (base ** attempt) + random.uniform(0, 0.5)
                        _log.debug("APIError (cuota). Reintento %s en %.2fs", attempt + 1, delay)
                        time.sleep(delay)
                        continue
                    raise
                except Exception as e:
                    is_http_err = (
                        (requests and isinstance(e, requests.exceptions.HTTPError)) or
                        (GHttpError and isinstance(e, GHttpError))
                    )
                    if attempt < max_retries - 1 and (is_http_err or GoogleSheetService._is_quota_error(e)):
                        delay = (base ** attempt) + random.uniform(0, 0.5)
                        _log.debug("HTTP/API error. Reintento %s en %.2fs", attempt + 1, delay)
                        time.sleep(delay)
                        continue
                    raise
        return wrapper

    # ----------------------------------------------------------
    # Apertura de libros / hojas
    # ----------------------------------------------------------
    @retry_on_quota
    def get_sheet_by_key(self, sheet_key):
        """Obtiene un Spreadsheet por ID con caché."""
        self.__ensure_client()
        try:
            if sheet_key in self._sheet_cache:
                return self._sheet_cache[sheet_key]
            spreadsheet = self.client.open_by_key(sheet_key)
            self._sheet_cache[sheet_key] = spreadsheet
            return spreadsheet
        except Exception as e:
            _log.warning("No se pudo abrir el libro %s: %s", sheet_key, e)
            return None

    @retry_on_quota
    def get_worksheet(self, book_name, worksheet_name):
        """
        Obtiene una hoja específica usando:
          Config.SHEETS[book_name]['id'] y
          Config.SHEETS[book_name]['worksheets'][worksheet_name]
        """
        self.__ensure_client()
        try:
            sheets_cfg = getattr(Config, "SHEETS", {}) or {}
            if book_name not in sheets_cfg:
                _log.debug("Libro '%s' no encontrado en configuración", book_name)
                return None

            book_config = sheets_cfg[book_name]
            sheet_id = book_config.get("id")
            if not sheet_id:
                _log.debug("ID no configurado para el libro '%s'", book_name)
                return None

            real_title = book_config.get("worksheets", {}).get(worksheet_name)
            if not real_title:
                _log.debug("Hoja lógica '%s' no encontrada en '%s'", worksheet_name, book_name)
                return None

            cache_key = (sheet_id, real_title)
            if cache_key in self._ws_cache:
                return self._ws_cache[cache_key]

            spreadsheet = self.get_sheet_by_key(sheet_id)
            if spreadsheet:
                ws = spreadsheet.worksheet(real_title)
                self._ws_cache[cache_key] = ws
                return ws
            return None
        except Exception as e:
            _log.warning("Error al obtener hoja '%s' del libro '%s': %s",
                         worksheet_name, book_name, e)
            return None

    # ----------------------------------------------------------
    # Lectura / escritura
    # ----------------------------------------------------------
    def _records_from_ws(self, ws):
        """Convierte la hoja a lista de dicts (1ra fila como encabezado)."""
        try:
            values = ws.get_all_values(value_render_option="UNFORMATTED_VALUE")
            if not values:
                return []
            headers = [h.strip() if isinstance(h, str) else h for h in (values[0] or [])]
            rows = values[1:]
            out = []
            for r in rows:
                if len(r) < len(headers):
                    r = r + [""] * (len(headers) - len(r))
                elif len(r) > len(headers):
                    r = r[:len(headers)]
                out.append(dict(zip(headers, r)))
            return out
        except Exception as e:
            _log.warning("Error al mapear registros: %s", e)
            return []

    @retry_on_quota
    def get_all_records(self, book_name, worksheet_name):
        ws = self.get_worksheet(book_name, worksheet_name)
        if not ws:
            return []
        return self._records_from_ws(ws)

    @retry_on_quota
    def find_record(self, book_name, worksheet_name, column, value,
                    case_insensitive=True, strip=True):
        """Busca el primer registro que cumpla column == value."""
        records = self.get_all_records(book_name, worksheet_name)
        if strip:
            value = (value or "").strip()
        for rec in records:
            v = rec.get(column)
            if v is None:
                continue
            v_cmp = v.strip() if (strip and isinstance(v, str)) else v
            if case_insensitive and isinstance(v_cmp, str) and isinstance(value, str):
                if v_cmp.lower() == value.lower():
                    return rec
            else:
                if v_cmp == value:
                    return rec
        return None

    @retry_on_quota
    def add_record(self, book_name, worksheet_name, data):
        """Agrega una fila al final. `data` es lista en el orden de columnas."""
        ws = self.get_worksheet(book_name, worksheet_name)
        if not ws:
            return False
        try:
            ws.append_row(data, value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            _log.warning("Error al agregar registro: %s", e)
            return False

    def clear_cache(self):
        self._sheet_cache.clear()
        self._ws_cache.clear()
        _log.info("Cache de Google Sheets limpiado")

    # ----------------------------------------------------------
    # Helpers de normalización / parsing
    # ----------------------------------------------------------
    @staticmethod
    def _parse_date_any(v):
        """
        Convierte string/datetime/serial de Google Sheets a date.
        Acepta:
          - datetime/date
          - str en %d/%m/%Y, %Y-%m-%d, %d-%m-%Y, %m/%d/%Y, %Y/%m/%d, ISO
          - serial de Sheets/Excel (float/int; base 1899-12-30) o string numérico
        """
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        if v is None or v == "":
            return None

        # Serial number directo (evita confundir "2025")
        if isinstance(v, (int, float)):
            n = float(v)
            if 20000 <= n <= 60000:  # rango aprox 1954–2064
                base = date(1899, 12, 30)
                return base + timedelta(days=n)

        s = str(v).strip()
        # string numérico como serial
        if s.replace(".", "", 1).isdigit():
            try:
                n = float(s)
                if 20000 <= n <= 60000:
                    base = date(1899, 12, 30)
                    return base + timedelta(days=n)
            except Exception:
                pass

        # formatos comunes
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue

        # Texto largo: "24 de marzo del 2025"
        try:
            import re
            meses = {
                "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
                "julio": 7, "agosto": 8, "setiembre": 9, "septiembre": 9,
                "octubre": 10, "noviembre": 11, "diciembre": 12
            }
            m = re.match(r"(\d{1,2})\s+de\s+(\w+)(?:\s+del\s+(\d{4}))?", s, re.IGNORECASE)
            if m:
                dia = int(m.group(1))
                mes = meses.get(m.group(2).lower())
                ano = int(m.group(3)) if m.group(3) else datetime.now().year
                if mes:
                    return date(ano, mes, dia)
        except Exception:
            pass

        # ISO parcial
        try:
            return datetime.fromisoformat(s.split()[0]).date()
        except Exception:
            return None

    @staticmethod
    def _norm_code_loose(v: str) -> str:
        """lower + sin acentos + sin espacios/guiones/guion_bajo (para comparar)."""
        s = str(v or "").strip().lower()
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        for ch in (" ", "-", "_"):
            s = s.replace(ch, "")
        return s

    @staticmethod
    def _extract_code(v: str) -> str:
        """
        Extrae el código inicial de 'PERSONAL'. Ej: 'C002 - NOMBRE' -> 'C002'.
        Si no hay separador, devuelve el string tal cual (recortado y upper).
        """
        s = str(v or "").strip().upper()
        if " - " in s:
            return s.split(" - ", 1)[0].strip()
        return s

    @staticmethod
    def _norm_key(s: str) -> str:
        s = (s or "").strip().lower()
        s = s.replace(" ", "").replace("-", "").replace("_", "")
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        return s

    @staticmethod
    def _index_keys(sample_dict):
        return {GoogleSheetService._norm_key(k): k for k in sample_dict.keys()}

    @staticmethod
    def _find_key(idx, exact_candidates, contains_candidates=None):
        for cand in exact_candidates:
            nk = GoogleSheetService._norm_key(cand)
            if nk in idx:
                return idx[nk]
        if contains_candidates:
            wants = [GoogleSheetService._norm_key(x) for x in contains_candidates]
            for nk, orig in idx.items():
                if any(w in nk for w in wants):
                    return orig
        return None

    @staticmethod
    def _safe_float(v):
        try:
            return float(str(v).replace("S/", "").replace(",", "").strip())
        except Exception:
            return 0.0

    @staticmethod
    def _as_int_or_none(v):
        try:
            return int(str(v).strip().lstrip("0") or "0")
        except Exception:
            return None

    # ----------------------------------------------------------
    # CREDENCIALES: Código y Comisión
    # ----------------------------------------------------------
    def get_user_code(self, username: str, config) -> str:
        """Devuelve Código desde la hoja de credenciales."""
        try:
            cred_cfg = config["SHEETS"]["credenciales"]
            sh = self.get_sheet_by_key(cred_cfg["id"])
            if not sh:
                return ""
            ws_title = cred_cfg["worksheets"]["usuarios"]
            ws = self._ws_cache.get((cred_cfg["id"], ws_title))
            if not ws:
                ws = sh.worksheet(ws_title)
                self._ws_cache[(cred_cfg["id"], ws_title)] = ws

            rows = self._records_from_ws(ws)
            if not rows:
                return ""

            key_index = self._index_keys(rows[0])
            k_email = self._find_key(key_index, ["Email"])
            k_user = self._find_key(key_index, ["Username"])
            k_name = self._find_key(key_index, ["Nombres y Apellidos", "Nombres y apellidos"])
            k_codigo = self._find_key(key_index, ["Codigo", "Código", "codigo", "code"])
            if not k_codigo:
                return ""

            target = (username or "").strip().lower()
            for r in rows:
                cand = [
                    str(r.get(k_email, "")).strip().lower() if k_email else "",
                    str(r.get(k_user, "")).strip().lower() if k_user else "",
                    str(r.get(k_name, "")).strip().lower() if k_name else "",
                ]
                if target and target in cand:
                    val = r.get(k_codigo, "")
                    return str(val).strip() if val is not None else ""
        except Exception as e:
            _log.debug("get_user_code error: %s", e, exc_info=False)
        return ""

    def get_user_commission_pct(self, username: str, config) -> float:
        """Lee 'Comisión' desde credenciales; cae a DEFAULT_COMMISSION_PCT si no hay dato."""
        try:
            cred_cfg = config["SHEETS"]["credenciales"]
            sh = self.get_sheet_by_key(cred_cfg["id"])
            if not sh:
                return config.get("DEFAULT_COMMISSION_PCT", 0.10)
            ws_title = cred_cfg["worksheets"]["usuarios"]
            ws = self._ws_cache.get((cred_cfg["id"], ws_title))
            if not ws:
                ws = sh.worksheet(ws_title)
                self._ws_cache[(cred_cfg["id"], ws_title)] = ws

            rows = self._records_from_ws(ws)
            if not rows:
                return config.get("DEFAULT_COMMISSION_PCT", 0.10)

            key_index = self._index_keys(rows[0])
            k_email = self._find_key(key_index, ["Email"])
            k_user = self._find_key(key_index, ["Username"])
            k_name = self._find_key(key_index, ["Nombres y Apellidos", "Nombres y apellidos"])
            k_comis = self._find_key(key_index, ["Comisión", "Comision", "commission", "pct"])

            target = (username or "").strip().lower()
            for r in rows:
                cand = [
                    str(r.get(k_email, "")).strip().lower() if k_email else "",
                    str(r.get(k_user, "")).strip().lower() if k_user else "",
                    str(r.get(k_name, "")).strip().lower() if k_name else "",
                ]
                if target and target in cand:
                    if not k_comis:
                        break
                    pct = r.get(k_comis)
                    if pct is None or pct == "":
                        break
                    try:
                        return float(str(pct).replace("%", "").strip()) / 100.0
                    except Exception:
                        break
        except Exception:
            pass
        return config.get("DEFAULT_COMMISSION_PCT", 0.10)

    # ----------------------------------------------------------
    # DASHBOARD: ventas por Código (PERSONAL)
    # ----------------------------------------------------------
    def search_mentions(self, config, q=None, especialidad=None, mencion=None,
                        p_certificado=None, horas_min=None, horas_max=None,
                        f_ini_desde=None, f_ini_hasta=None,
                        f_emis_desde=None, f_emis_hasta=None,
                        limit=200):
        """
        Lee la hoja MENCIONES y filtra por los parámetros indicados.
        - q: texto en NRO, ESPECIALIDAD, MENCIÓN, P. CERTIFICADO
        - horas: se devuelve como entero si es un número entero
        """
        empty = []
        try:
            conf = config['SHEETS']['menciones']
            sh = self.get_sheet_by_key(conf['id'])
            if not sh:
                return empty
            ws_title = conf['worksheets']['registro']
            ws = self._ws_cache.get((conf['id'], ws_title))
            if not ws:
                ws = sh.worksheet(ws_title)
                self._ws_cache[(conf['id'], ws_title)] = ws
            rows = self._records_from_ws(ws)
            if not rows:
                return empty

            # Mapear encabezados
            key_index = self._index_keys(rows[0])
            k_nro   = self._find_key(key_index, ["NRO"], ["nro","numero","n°"])
            k_esp   = self._find_key(key_index, ["ESPECIALIDAD"], ["especialidad"])
            k_pcert = self._find_key(key_index, ["P. CERTIFICADO","P CERTIFICADO","PROCESO CERTIFICADO"], ["cert"])
            k_menc  = self._find_key(key_index, ["MENCIÓN","MENCION"], ["mencion"])
            k_horas = self._find_key(key_index, ["HORAS"], ["horas"])
            k_fini  = self._find_key(key_index, ["F. INICIO","FECHA INICIO"], ["inicio"])
            k_fter  = self._find_key(key_index, ["F. TÉRMINO","F. TERMINO","FECHA TERMINO","FECHA TÉRMINO"], ["termino","término"])
            k_femis = self._find_key(key_index, ["F. EMISIÓN","F. EMISION","FECHA EMISION","FECHA EMISIÓN"], ["emision","emisión"])

            q_norm = (q or "").strip().lower()
            p_cert_norm = (p_certificado or "").strip().lower() if p_certificado else None

            def parse_num(v):
                try:
                    return float(str(v).replace(",", "."))
                except Exception:
                    return None

            out = []
            for r in rows:
                # Compose record
                nro   = str(r.get(k_nro, "")).strip() if k_nro else ""
                esp   = str(r.get(k_esp, "")).strip() if k_esp else ""
                menc_ = str(r.get(k_menc, "")).strip() if k_menc else ""
                cert_raw = str(r.get(k_pcert, "")).strip() if k_pcert else ""
                horas = parse_num(r.get(k_horas, "")) if k_horas else None
                fi = self._parse_date_any(r.get(k_fini, "")) if k_fini else None
                ft = self._parse_date_any(r.get(k_fter, "")) if k_fter else None
                fe = self._parse_date_any(r.get(k_femis, "")) if k_femis else None

                # Filtros
                if q_norm:
                    blob = " ".join([nro, esp, menc_, cert_raw]).lower()
                    if q_norm not in blob:
                        continue
                if especialidad and esp.lower() != especialidad.strip().lower():
                    continue
                if mencion and menc_.lower() != mencion.strip().lower():
                    continue
                if p_cert_norm and p_cert_norm not in cert_raw.lower():
                    continue
                if horas_min is not None and (horas is None or horas < float(horas_min)):
                    continue
                if horas_max is not None and (horas is None or horas > float(horas_max)):
                    continue
                if f_ini_desde and (not fi or fi < f_ini_desde):
                    continue
                if f_ini_hasta and (not fi or fi > f_ini_hasta):
                    continue
                if f_emis_desde and (not fe or fe < f_emis_desde):
                    continue
                if f_emis_hasta and (not fe or fe > f_emis_hasta):
                    continue

                # Formatear horas como entero si es posible
                horas_display = int(horas) if horas and horas.is_integer() else horas if horas is not None else ""
                out.append({
                    "nro": nro,
                    "especialidad": esp,
                    "p_certificado": cert_raw,
                    "mencion": menc_,
                    "horas": horas_display,
                    "f_inicio": fi.strftime("%d/%m/%Y") if fi else "",
                    "f_termino": ft.strftime("%d/%m/%Y") if ft else "",
                    "f_emision": fe.strftime("%d/%m/%Y") if fe else "",
                    "_sort": (fi or fe or ft or None)
                })
                if limit is not None and len(out) >= int(limit):
                    break

            # Ordenar por fecha de inicio (o emisión) desc
            out.sort(key=lambda x: (x["_sort"] or date(1900, 1, 1)), reverse=True)
            for x in out:
                x.pop("_sort", None)
            return out
        except Exception as e:
            _log.error("search_mentions error: %s", e, exc_info=True)
            return empty

    def get_sales_by_code(self, personal_code: str, d_start, d_end, config):
        """Filtra ventas por PERSONAL == personal_code en el rango [d_start, d_end]."""
        empty = {"count": 0, "total_monto": 0.0, "ventas": []}
        if not personal_code:
            return empty
        try:
            dash_cfg = config["SHEETS"]["dashboard"]
            sh = self.get_sheet_by_key(dash_cfg["id"])
            if not sh:
                return empty
            ws_title = dash_cfg["worksheets"]["registro"]
            ws = self._ws_cache.get((dash_cfg["id"], ws_title))
            if not ws:
                ws = sh.worksheet(ws_title)
                self._ws_cache[(dash_cfg["id"], ws_title)] = ws
            rows = self._records_from_ws(ws)
            if not rows:
                return empty

            key_index = self._index_keys(rows[0])
            k_personal = self._find_key(key_index, ["PERSONAL"], ["personal", "asesor", "vendedor"])
            k_fecha = self._find_key(key_index, ["FECHA DE LA VENTA", "Marca temporal"], ["fecha"])
            k_monto = self._find_key(key_index, ["MONTO DEPOSITADO"], ["monto", "importe"])
            k_cliente = self._find_key(key_index, ["NOMBRE COMPLETO DEL CLIENTE", "CLIENTE"], ["cliente"])
            k_dni = self._find_key(key_index, ["DNI DEL CLIENTE", "DNI"], ["dni"])
            k_celular = self._find_key(key_index, ["CELULAR DEL CLIENTE", "CELULAR"], ["celular"])
            k_producto = self._find_key(key_index, ["TIPO DE PRODUCTO", "PRODUCTO"], ["producto"])
            k_operacion = self._find_key(key_index, ["NUMERO DE OPERACIÓN", "NUMERO DE OPERACION"], ["operacion"])
            if not k_personal:
                _log.debug("No se encontró columna PERSONAL en dashboard")
                return empty

            target = self._extract_code(personal_code).upper()
            ventas, total = [], 0.0
            for r in rows:
                code_val = self._extract_code(r.get(k_personal, ""))
                if code_val != target:
                    continue
                f = self._parse_date_any(r.get(k_fecha, "")) if k_fecha else None
                if not f or not (d_start <= f <= d_end):
                    continue
                monto = self._safe_float(r.get(k_monto, 0)) if k_monto else 0.0
                ventas.append({
                    "fecha": f.strftime("%d/%m/%Y"),
                    "cliente": r.get(k_cliente, "") if k_cliente else "",
                    "dni": r.get(k_dni, "") if k_dni else "",
                    "celular": r.get(k_celular, "") if k_celular else "",
                    "producto": r.get(k_producto, "") if k_producto else "",
                    "operacion": r.get(k_operacion, "") if k_operacion else "",
                    "monto": monto,
                    "_fecha_dt": f,
                })
                total += monto
            ventas.sort(key=lambda x: x["_fecha_dt"], reverse=True)
            for v in ventas:
                v.pop("_fecha_dt", None)
            return {"count": len(ventas), "total_monto": round(total, 2), "ventas": ventas}
        except Exception as e:
            _log.debug("get_sales_by_code error: %s", e, exc_info=False)
            return empty

    def get_cobranzas_by_code(self, personal_code: str, d_start, d_end, config):
        """
        Filtra cobranzas por PERSONAL == personal_code y donde
        MONTO TOTAL DE LA VENTA != MONTO DEPOSITADO.
        El rango [d_start, d_end] se aplica sobre la FECHA DE COBRO (= FECHA DE LA VENTA + 30 días).
        Devuelve: {"count": int, "total_monto": float, "cobranzas": list[dict]}
        """
        empty = {"count": 0, "total_monto": 0.0, "cobranzas": []}
        if not personal_code:
            return empty
        try:
            ventas_cfg = config["SHEETS"]["ventas"]
            sh = self.get_sheet_by_key(ventas_cfg["id"])
            if not sh:
                return empty

            ws_title = ventas_cfg["worksheets"]["registro"]
            ws = self._ws_cache.get((ventas_cfg["id"], ws_title))
            if not ws:
                ws = sh.worksheet(ws_title)
                self._ws_cache[(ventas_cfg["id"], ws_title)] = ws

            rows = self._records_from_ws(ws)
            if not rows:
                return empty

            # Mapear columnas
            key_index = self._index_keys(rows[0])
            k_personal = self._find_key(key_index, ["PERSONAL"], ["personal", "asesor"])
            k_fecha = self._find_key(key_index, ["FECHA DE LA VENTA"], ["fecha"])
            k_monto_total = self._find_key(key_index, ["MONTO TOTAL DE LA VENTA"], ["monto_total"])
            k_monto_depositado = self._find_key(key_index, ["MONTO DEPOSITADO"], ["monto_depositado"])
            k_cliente = self._find_key(key_index, ["NOMBRE COMPLETO DEL CLIENTE"], ["cliente"])
            k_dni = self._find_key(key_index, ["DNI DEL CLIENTE"], ["dni"])
            k_celular = self._find_key(key_index, ["CELULAR DEL CLIENTE"], ["celular"])
            k_correo = self._find_key(key_index, ["CORREO DEL CLIENTE"], ["correo"])
            k_especialidad = self._find_key(key_index, ["ESPECIALIDAD"], ["especialidad"])
            k_observaciones = self._find_key(key_index, ["OBSERVACIONES"], ["observaciones"])

            if not k_personal or not k_monto_total or not k_monto_depositado:
                return empty

            target = self._extract_code(personal_code).upper()
            cobranzas = []
            total = 0.0

            for r in rows:
                code_val = self._extract_code(r.get(k_personal, ""))
                if code_val != target:
                    continue

                f_venta = self._parse_date_any(r.get(k_fecha, "")) if k_fecha else None
                if not f_venta:
                    continue

                # FECHA DE COBRO = FECHA DE LA VENTA + 30 días
                fecha_de_cobro = f_venta + timedelta(days=30)
                if not (d_start <= fecha_de_cobro <= d_end):
                    continue

                # Montos
                monto_total = self._safe_float(r.get(k_monto_total, 0))
                monto_depositado = self._safe_float(r.get(k_monto_depositado, 0))

                # Solo incluir si los montos son diferentes
                if monto_total != monto_depositado:
                    cobranzas.append({
                        "fecha": f_venta.strftime("%d/%m/%Y"),
                        "fecha_de_cobro": fecha_de_cobro.strftime("%d/%m/%Y"),
                        "cliente": r.get(k_cliente, "") if k_cliente else "",
                        "dni": r.get(k_dni, "") if k_dni else "",
                        "celular": r.get(k_celular, "") if k_celular else "",
                        "correo": r.get(k_correo, "") if k_correo else "",
                        "monto_total": monto_total,
                        "monto_depositado": monto_depositado,
                        "especialidad": r.get(k_especialidad, "") if k_especialidad else "",
                        "observaciones": r.get(k_observaciones, "") if k_observaciones else "",
                        "_fecha_cobro_dt": fecha_de_cobro,
                    })
                    # Suma actual: monto depositado (si prefieres la diferencia u otro, ajusta aquí)
                    total += monto_depositado

            # Ordenar por fecha_de_cobro asc
            cobranzas.sort(key=lambda x: x["_fecha_cobro_dt"])
            for c in cobranzas:
                c.pop("_fecha_cobro_dt", None)

            return {"count": len(cobranzas), "total_monto": round(total, 2), "cobranzas": cobranzas}
        except Exception as e:
            _log.debug("get_cobranzas_by_code error: %s", e, exc_info=False)
            return empty


# Instancia global del servicio (lazy connect evita conectar al importar)
gs_service = GoogleSheetService()
