# routes/diag.py
from flask import Blueprint, request, jsonify, current_app, session, render_template_string
from services.google_sheet_service import GoogleSheetService

diag_bp = Blueprint("diag", __name__, url_prefix="/diag")

@diag_bp.route("/sheet")
def diag_sheet():
    svc = GoogleSheetService()
    cfg = current_app.config

    rows = svc.get_all_records('dashboard', 'registro')
    headers = list(rows[0].keys()) if rows else []

    idx = svc._index_keys(rows[0]) if rows else {}
    k_personal = svc._find_key(idx, ["PERSONAL", "PERSONAL  "], ["personal", "asesor", "vendedor"]) if idx else None
    k_fecha    = svc._find_key(idx, ["FECHA DE LA VENTA", "Marca temporal"], ["fechadelaventa","fecha","marcatemporal","timestamp"]) if idx else None
    k_monto    = svc._find_key(idx, ["MONTO DEPOSITADO"], ["montototal","monto","importe"]) if idx else None

    sample_personal = [r.get(k_personal, "") for r in rows[:10]] if rows and k_personal else []
    sample_fecha    = [r.get(k_fecha, "") for r in rows[:10]] if rows and k_fecha else []
    sample_monto    = [r.get(k_monto, "") for r in rows[:10]] if rows and k_monto else []

    codigo_session = (session.get('user', {}) or {}).get('codigo', '')
    username = (session.get('user', {}) or {}).get('email') or (session.get('user', {}) or {}).get('username') or (session.get('user', {}) or {}).get('nombre') or ''
    codigo_lookup = GoogleSheetService().get_user_code(username, cfg) if username else ''
    codigo_forzado = request.args.get('debug_code', '').strip()
    codigo_efectivo = codigo_forzado or codigo_session or codigo_lookup

    if request.args.get('mode') == 'json':
        return jsonify({
            "headers": headers,
            "resolved_keys": {"PERSONAL": k_personal, "FECHA": k_fecha, "MONTO": k_monto},
            "sample_personal": sample_personal,
            "sample_fecha": sample_fecha,
            "sample_monto": sample_monto,
            "codigo": {
                "session": codigo_session,
                "lookup": codigo_lookup,
                "forced": codigo_forzado,
                "effective": codigo_efectivo
            }
        })

    html = """
    <h2>Diagnóstico de hoja Dashboard</h2>
    <p><b>Headers:</b> {{ headers }}</p>
    <p><b>Claves resueltas:</b> PERSONAL={{ k_personal }}, FECHA={{ k_fecha }}, MONTO={{ k_monto }}</p>
    <p><b>PERSONAL (10):</b> {{ sample_personal }}</p>
    <p><b>FECHA (10):</b> {{ sample_fecha }}</p>
    <p><b>MONTO (10):</b> {{ sample_monto }}</p>
    <hr>
    <h3>Código</h3>
    <ul>
      <li>session['user']['codigo']: <b>{{ codigo_session }}</b></li>
      <li>lookup por credenciales: <b>{{ codigo_lookup }}</b></li>
      <li>forzado (?debug_code=XXXX): <b>{{ codigo_forzado }}</b></li>
      <li>efectivo: <b>{{ codigo_efectivo }}</b></li>
    </ul>
    <p>Para JSON: <code>?mode=json</code> — Para forzar código: <code>?debug_code=XXXX</code></p>
    """
    return render_template_string(html,
        headers=headers, k_personal=k_personal, k_fecha=k_fecha, k_monto=k_monto,
        sample_personal=sample_personal, sample_fecha=sample_fecha, sample_monto=sample_monto,
        codigo_session=codigo_session, codigo_lookup=codigo_lookup, codigo_forzado=codigo_forzado, codigo_efectivo=codigo_efectivo
    )
