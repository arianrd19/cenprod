# routes/ventas.py
from flask import Blueprint, render_template, request, flash, jsonify
from routes.auth import login_required
from services.google_sheet_service import gs_service
from datetime import datetime, date, timedelta

ventas_bp = Blueprint('ventas', __name__, url_prefix='/ventas')

# Mapeo de columnas según tu hoja
COL_TIMESTAMP   = 'Marca temporal'
COL_PERSONAL    = 'PERSONAL'  # Asesor
COL_CLIENTE     = 'NOMBRE COMPLETO DEL CLIENTE'
COL_DNI         = 'DNI DEL CLIENTE'
COL_CELULAR     = 'CELULAR DEL CLIENTE'
COL_CORREO      = 'CORREO DEL CLIENTE'
COL_FECHA       = 'FECHA DE LA VENTA'
COL_MONTO_TOTAL = 'MONTO DEPOSITADO'
COL_DEPOSITADO  = 'MONTO DEPOSITADO'
COL_COMP        = 'COMPROBANTE DE PAGO'
COL_OPERACION   = 'NUMERO DE OPERACIÓN'
COL_ENTIDAD     = 'ENTIDAD FINANCIERA'
COL_CUOTAS      = 'CUOTAS'
COL_PRODUCTO    = 'TIPO DE PRODUCTO'
COL_ESPECIALIDAD= 'ESPECIALIDAD'
COL_OBS         = 'OBSERVACIONES'

MESES_ES = ['enero','febrero','marzo','abril','mayo','junio','julio',
            'agosto','septiembre','octubre','noviembre','diciembre']

def _only_digits(s: str) -> str:
    return ''.join(ch for ch in (s or '') if ch.isdigit())

def _fecha_spanish(dt: datetime) -> str:
    return f"{dt.day:02d} de {MESES_ES[dt.month-1]} de {dt.year}"

def _formatea_fecha(value) -> str:
    """Convierte múltiples formatos de 'value' a 'DD de <mes> de YYYY'."""
    if value in (None, ''):
        return ''

    # datetime / date
    if isinstance(value, datetime):
        return _fecha_spanish(value)
    if isinstance(value, date):
        return _fecha_spanish(datetime(value.year, value.month, value.day))

    s = str(value).strip()

    # ISO: YYYY-MM-DD o YYYY-MM-DD HH:MM:SS(.ms)
    try:
        dt = datetime.fromisoformat(s[:19])
        return _fecha_spanish(dt)
    except Exception:
        pass

    # Formatos comunes
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d", "%d/%m/%y"):
        try:
            dt = datetime.strptime(s[:10], fmt)
            return _fecha_spanish(dt)
        except Exception:
            continue

    # Solo dígitos
    if s.isdigit():
        # YYYYMMDD
        if len(s) == 8:
            try:
                y, m, d = int(s[0:4]), int(s[4:6]), int(s[6:8])
                return _fecha_spanish(datetime(y, m, d))
            except Exception:
                pass

        # Epoch (segundos o milisegundos)
        try:
            ts = int(s)
            if ts > 1_000_000_000_000:  # milisegundos
                ts = ts / 1000.0
            # rango razonable para fechas modernas
            if 946684800 <= ts <= 4102444800:  # 2000-01-01 .. 2100-01-01
                dt = datetime.fromtimestamp(ts)
                return _fecha_spanish(dt)
        except Exception:
            pass

        # Serial de Excel (~días desde 1899-12-30)
        try:
            serial = int(s)
            if 20000 < serial < 60000:  # aprox. 1954..2064
                base = datetime(1899, 12, 30)
                dt = base + timedelta(days=serial)
                return _fecha_spanish(dt)
        except Exception:
            pass

    # Fallback: devolver tal cual si no se reconoce
    return s

def _row_to_view(row: dict) -> dict:
    """Normaliza un registro para mostrar en la vista."""
    fecha_raw = row.get(COL_FECHA) or row.get(COL_TIMESTAMP) or ''
    return {
        'fecha_venta'      : fecha_raw,
        'fecha_venta_fmt'  : _formatea_fecha(fecha_raw),   # <-- listo para el template
        'cliente'          : row.get(COL_CLIENTE, ''),
        'dni'              : str(row.get(COL_DNI, '')).strip(),
        'celular'          : str(row.get(COL_CELULAR, '')).strip(),
        'correo'           : row.get(COL_CORREO, ''),
        'monto_total'      : row.get(COL_MONTO_TOTAL, ''),
        'monto_depositado' : row.get(COL_DEPOSITADO, ''),
        'comprobante'      : row.get(COL_COMP, ''),
        'operacion'        : row.get(COL_OPERACION, ''),
        'entidad'          : row.get(COL_ENTIDAD, ''),
        'cuotas'           : row.get(COL_CUOTAS, ''),
        'producto'         : row.get(COL_PRODUCTO, ''),
        'especialidad'     : row.get(COL_ESPECIALIDAD, ''),
        'asesor'           : row.get(COL_PERSONAL, ''),  # "quién es su asesor"
        'observaciones'    : row.get(COL_OBS, ''),
        'marca_temporal'   : row.get(COL_TIMESTAMP, ''),
    }

@ventas_bp.route('/consulta')
@login_required
def consulta():
    """
    Página de 'Consulta de ventas' por DNI o Celular.
    Parámetros GET:
      - q: query (dni o celular)
      - tipo: 'dni' (default) o 'celular'
    """
    q = (request.args.get('q') or '').strip()
    tipo = (request.args.get('tipo') or 'dni').lower()
    resultados = []
    total = 0

    if q:
        try:
            # Obtiene todos los registros de la hoja de ventas
            rows = gs_service.get_all_records(book_name='ventas', worksheet_name='registro')

            # Normaliza la query a dígitos si es DNI/CEL
            q_digits = _only_digits(q)

            for r in rows:
                dni_digits = _only_digits(str(r.get(COL_DNI, '')))
                cel_digits = _only_digits(str(r.get(COL_CELULAR, '')))

                if tipo == 'dni':
                    match = (q_digits == dni_digits) or (q_digits and q_digits in dni_digits)
                else:
                    match = (q_digits == cel_digits) or (q_digits and q_digits in cel_digits)

                if match:
                    resultados.append(_row_to_view(r))

            total = len(resultados)
            if total == 0:
                flash('No se encontraron ventas para la búsqueda.', 'info')

        except Exception as e:
            flash('Error al consultar ventas.', 'error')
            print(f"❌ Error consulta ventas: {e}")

    # Render
    return render_template('ventas/consulta.html', q=q, tipo=tipo, resultados=resultados, total=total)

@ventas_bp.route('/api/consulta')
@login_required
def api_consulta():
    """Endpoint JSON para la misma búsqueda."""
    q = (request.args.get('q') or '').strip()
    tipo = (request.args.get('tipo') or 'dni').lower()
    data = []
    try:
        if q:
            rows = gs_service.get_all_records(book_name='ventas', worksheet_name='registro')
            q_digits = _only_digits(q)
            for r in rows:
                dni_digits = _only_digits(str(r.get(COL_DNI, '')))
                cel_digits = _only_digits(str(r.get(COL_CELULAR, '')))
                if tipo == 'dni':
                    match = (q_digits == dni_digits) or (q_digits and q_digits in dni_digits)
                else:
                    match = (q_digits == cel_digits) or (q_digits and q_digits in cel_digits)
                if match:
                    data.append(_row_to_view(r))
        return jsonify({'success': True, 'total': len(data), 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
