#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico de Dashboard y Cobranza (Google Sheets)
---------------------------------------------------
Ejecuta pruebas equivalentes a las vistas, mostrando:
- Dataset y headers reales que ve el servicio
- Dónde se "pierden" las filas al aplicar filtros
- Diferencia entre filtrar por FECHA DE LA VENTA vs FECHA DE COBRO (+30d)
- Normalización de código PERSONAL
Guárdalo en la raíz del proyecto y ejecútalo con:
  python diagnostico_dashboard_cobranza.py --codigo ABC123 --anio 2025 --mes 11 --modo cobro
"""

from __future__ import annotations
import sys
import csv
import argparse
from datetime import datetime, date, timedelta

# Estos imports deben existir en TU proyecto
try:
    from services.google_sheet_service import gs_service
    try:
        from config import Config
    except Exception:
        Config = None
except Exception as e:
    print("❌ No pude importar tus módulos del proyecto (services/google_sheet_service.py o config.py).")
    print("   Ejecuta este script dentro del entorno de tu app (misma carpeta raíz).")
    print("   Error original:", e)
    sys.exit(2)


def parse_date_multi(s):
    """Parser tolerante para DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY."""
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def month_bounds(y: int, m: int) -> tuple[date, date]:
    """Primer y último día del mes (inclusive)."""
    first = date(y, m, 1)
    if m == 12:
        nxt = date(y + 1, 1, 1)
    else:
        nxt = date(y, m + 1, 1)
    last = nxt - timedelta(days=1)
    return first, last


def debug_header(rows):
    return list(rows[0].keys()) if rows else []


def check_dashboard():
    print("\n" + "="*80)
    print("🧭 DIAGNÓSTICO: DASHBOARD")
    print("="*80)
    if not Config:
        print("ℹ️ No hay Config; salto prueba de Dashboard.")
        return

    cfg = Config.SHEETS.get('dashboard', {})
    ss_id = cfg.get('id')
    ws_name = (cfg.get('worksheets') or {}).get('registro')

    print(f"📄 Spreadsheet ID: {ss_id}")
    print(f"📑 Worksheet (registro): {ws_name}")
    try:
        rows = gs_service.get_all_records(book_name='dashboard', worksheet_name='registro')
    except Exception as e:
        print("❌ Error leyendo dashboard/registro:", e)
        return

    print(f"✅ Filas leídas: {len(rows)}")
    print(f"📋 Encabezados: {debug_header(rows)}")
    for i, r in enumerate(rows[:3]):
        print(f"   └─ sample[{i}]:", {k: r.get(k) for k in list(r.keys())[:8]})


def check_cobranzas(codigo: str|None, anio: int, mes: int, modo: str, export_csv: bool=True):
    print("\n" + "="*80)
    print("💵 DIAGNÓSTICO: COBRANZA")
    print("="*80)

    d_start, d_end = month_bounds(anio, mes)
    print(f"📆 Rango mes: {d_start} .. {d_end}  (modo filtro: {modo})")
    if codigo:
        print(f"👤 Código (PERSONAL) buscado: {codigo!r}")

    # 1) Leer dataset base (ventas/registro -> suele mapear a QUERYS)
    try:
        raw = gs_service.get_all_records(book_name='ventas', worksheet_name='registro')
    except Exception as e:
        print("❌ Error leyendo ventas/registro:", e)
        return

    def _dbg(tag, rows): print(f"[{tag:<22}] {len(rows):>5} filas")

    _dbg("crudo", raw)
    if not raw:
        print("❌ No hay filas. Revisa Config.SHEETS['ventas']['worksheets']['registro'] (¿QUERYS?)")
        return

    # 2) Normalizar y filtrar por código PERSONAL (si se pasó)
    def norm_code(x):
        return (x or "").strip().upper()

    code_q = norm_code(codigo)
    rows2 = []
    for r in raw:
        personal = norm_code(r.get("PERSONAL"))
        r["_PERSONAL"] = personal
        rows2.append(r)
    _dbg("con PERSONAL", rows2)

    if code_q:
        rows2 = [r for r in rows2 if r["_PERSONAL"] == code_q]
        _dbg("filtrado por codigo", rows2)
        if not rows2:
            print("⚠️ No hay filas para ese código (tras normalizar). ¿Es correcto el código?")

    # 3) Parsear fecha de la venta y calcular fecha de cobro
    for r in rows2:
        f = parse_date_multi(r.get("FECHA DE LA VENTA"))
        r["_fecha_venta"] = f
        r["_fecha_cobro"] = f + timedelta(days=30) if f else None

    rows3 = [r for r in rows2 if r.get("_fecha_venta")]
    _dbg("con fecha_venta válida", rows3)

    # 4) Filtro por mes (venta o cobro)
    if modo == "venta":
        rows4 = [r for r in rows3 if d_start <= r["_fecha_venta"] <= d_end]
    else:  # "cobro" (por defecto)
        rows4 = [r for r in rows3 if r["_fecha_cobro"] and d_start <= r["_fecha_cobro"] <= d_end]
    _dbg(f"filtrado por {modo}", rows4)

    # 5) Muestra resumida
    show_cols = [
        "PERSONAL",
        "NOMBRE COMPLETO DEL CLIENTE",
        "FECHA DE LA VENTA",
        "MONTO TOTAL DE LA VENTA",
        "MONTO DEPOSITADO",
        "DNI DEL CLIENTE",
        "CELULAR DEL CLIENTE",
        "ESPECIALIDAD",
        "OBSERVACIONES",
    ]
    print("\nEjemplos (hasta 5 filas):")
    for r in rows4[:5]:
        resumen = {c: r.get(c) for c in show_cols if c in r}
        resumen["FECHA_COBRO_CALC"] = r.get("_fecha_cobro").strftime("%d/%m/%Y") if r.get("_fecha_cobro") else ""
        print(" -", resumen)

    # 6) Export opcional CSV para inspección
    if export_csv:
        out_path = f"cobranzas_debug_{anio:04d}_{mes:02d}_{modo}.csv"
        try:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["PERSONAL","CLIENTE","FECHA_VENTA","FECHA_COBRO_CALC","MONTO_TOTAL","MONTO_DEPOSITADO","DNI","CELULAR","ESPECIALIDAD","OBSERVACIONES"])
                for r in rows4:
                    writer.writerow([
                        r.get("PERSONAL",""),
                        r.get("NOMBRE COMPLETO DEL CLIENTE",""),
                        r.get("FECHA DE LA VENTA",""),
                        r.get("_fecha_cobro").strftime("%d/%m/%Y") if r.get("_fecha_cobro") else "",
                        r.get("MONTO TOTAL DE LA VENTA",""),
                        r.get("MONTO DEPOSITADO",""),
                        r.get("DNI DEL CLIENTE",""),
                        r.get("CELULAR DEL CLIENTE",""),
                        r.get("ESPECIALIDAD",""),
                        r.get("OBSERVACIONES",""),
                    ])
            print(f"\n📁 Exportado: {out_path}")
        except Exception as e:
            print("⚠️ No pude exportar CSV:", e)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnóstico de Dashboard y Cobranza (Google Sheets)")
    parser.add_argument("--codigo", help="Código/PERSONAL a filtrar (opcional)")
    parser.add_argument("--anio", type=int, default=date.today().year, help="Año para filtro de mes (por defecto: año actual)")
    parser.add_argument("--mes", type=int, default=date.today().month, help="Mes 1..12 para filtro (por defecto: mes actual)")
    parser.add_argument("--modo", choices=["venta","cobro"], default="cobro", help="Campo de fecha para filtrar el mes")
    parser.add_argument("--sin-csv", action="store_true", help="No exportar CSV de cobranzas")
    args = parser.parse_args(argv)

    check_dashboard()
    check_cobranzas(args.codigo, args.anio, args.mes, args.modo, export_csv=not args.sin_csv)


if __name__ == "__main__":
    main()
