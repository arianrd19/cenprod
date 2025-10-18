# routes/ventas.py
from flask import Blueprint, render_template, request, flash, jsonify
from routes.auth import login_required
from services.google_sheet_service import gs_service

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

def _only_digits(s: str) -> str:
    return ''.join(ch for ch in (s or '') if ch.isdigit())

def _row_to_view(row: dict) -> dict:
    """Normaliza un registro para mostrar en la vista."""
    return {
        'fecha_venta'   : row.get(COL_FECHA) or row.get(COL_TIMESTAMP) or '',
        'cliente'       : row.get(COL_CLIENTE, ''),
        'dni'           : str(row.get(COL_DNI, '')).strip(),
        'celular'       : str(row.get(COL_CELULAR, '')).strip(),
        'correo'        : row.get(COL_CORREO, ''),
        'monto_total'   : row.get(COL_MONTO_TOTAL, ''),
        'monto_depositado': row.get(COL_DEPOSITADO, ''),
        'comprobante'   : row.get(COL_COMP, ''),
        'operacion'     : row.get(COL_OPERACION, ''),
        'entidad'       : row.get(COL_ENTIDAD, ''),
        'cuotas'        : row.get(COL_CUOTAS, ''),
        'producto'      : row.get(COL_PRODUCTO, ''),
        'especialidad'  : row.get(COL_ESPECIALIDAD, ''),
        'asesor'        : row.get(COL_PERSONAL, ''),  # "quién es su asesor"
        'observaciones' : row.get(COL_OBS, ''),
        'marca_temporal': row.get(COL_TIMESTAMP, ''),
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

                match = False
                if tipo == 'dni':
                    # match exacto o por "contiene" en caso de ruido
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

    # Render: usa tu propia plantilla Jinja
    # Variables disponibles: q, tipo, resultados, total
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
