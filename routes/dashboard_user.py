# routes/dashboard_user.py
from flask import Blueprint, render_template, session, current_app, flash, request
from datetime import date, timedelta
from services.google_sheet_service import gs_service
from .auth import login_required

bp = Blueprint("dashboard_user", __name__, url_prefix="/mi-dashboard")

MESES = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "SETIEMBRE": 9,
    "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}

def _month_bounds(y: int, m: int):
    first = date(y, m, 1)
    if m == 12:
        next_first = date(y + 1, 1, 1)
    else:
        next_first = date(y, m + 1, 1)
    last = next_first - timedelta(days=1)
    return first, last

def _bounds_from_tab(tab_title: str):
    """
    Convierte 'OCTUBRE-2025' -> (2025-10-01, 2025-10-31) y devuelve también el label.
    Si falla, usa mes actual.
    """
    try:
        nombre, anio = tab_title.split("-", 1)
        m = MESES[nombre.strip().upper()]
        y = int(anio.strip())
        d_start, d_end = _month_bounds(y, m)
        return d_start, d_end, tab_title
    except Exception:
        today = date.today()
        d_start, d_end = _month_bounds(today.year, today.month)
        return d_start, d_end, today.strftime("%B %Y").title()

@bp.route("/")
@login_required
def me_dashboard():
    # --- Usuario en sesión
    user = session.get("user", {}) or {}
    username = (user.get("name") or user.get("nombre") or "").strip()
    user_email = (user.get("email") or user.get("correo") or "").strip()

    # --- Config del dashboard para leer el título de la pestaña (p.ej. 'OCTUBRE-2025')
    dash_cfg = current_app.config["SHEETS"]["dashboard"]
    tab_title = dash_cfg["worksheets"]["registro"]

    # --- Overrides por querystring
    # ?anio=2025&mes=11   -> fija el rango explícitamente
    # ?codigo=C002        -> fuerza código
    # ?nofilter=1         -> ignora el filtro de fechas (toma todo)
    q_anio = request.args.get("anio")
    q_mes = request.args.get("mes")
    codigo_override = request.args.get("codigo", "").strip()
    nofilter = request.args.get("nofilter") == "1"

    if nofilter:
        d_start, d_end = date(1900, 1, 1), date(2999, 12, 31)
        month_label = "Todos"
    elif q_anio and q_mes:
        try:
            d_start, d_end = _month_bounds(int(q_anio), int(q_mes))
            month_label = f"{int(q_mes):02d}/{q_anio}"
        except Exception:
            d_start, d_end, month_label = _bounds_from_tab(tab_title)
    else:
        # Por defecto: usa el mes de la pestaña configurada (ej. OCTUBRE-2025)
        d_start, d_end, month_label = _bounds_from_tab(tab_title)

    # --- Resolver código del usuario (prioriza email)
    codigo = (user.get("codigo") or "").strip()
    if codigo_override:
        codigo = codigo_override
    if not codigo:
        key_for_lookup = user_email or username
        if key_for_lookup:
            codigo = gs_service.get_user_code(key_for_lookup, current_app.config)
    if not codigo:
        flash("No se encontró el Código del usuario en CREDENCIALES. Verifica tu registro.", "error")
        stats = {"count": 0, "total_monto": 0.0, "ventas": []}
        pct = 0.0
    else:
        # --- Ventas en rango (lee hoja 'dashboard' y filtra por FECHA DE LA VENTA)
        stats = gs_service.get_sales_by_code(codigo, d_start, d_end, current_app.config)
        # Comisión
        pct = user.get("comision")
        if pct is None:
            key_for_lookup = user_email or username
            pct = gs_service.get_user_commission_pct(key_for_lookup, current_app.config)

    # --- KPIs
    total = stats.get("total_monto", 0.0)
    count = stats.get("count", 0)
    commission = round(total * (pct or 0.0), 2)
    avg_ticket = round(total / count, 2) if count else 0.0
    ultimas = stats.get("ventas", [])[:10]

    return render_template(
        "dashboard/usuario.html",
        username=(username or user_email or "Usuario"),
        month=month_label,
        count=count,
        total=total,
        commission=commission,
        pct=int((pct or 0.0) * 100),
        avg_ticket=avg_ticket,
        ultimas=ultimas,
        codigo=codigo,
        nofilter=nofilter,
        # Extras de credenciales
        posicion=user.get('posicion'),
        volumen_cred=user.get('volumen'),
        ventas_cred=user.get('ventas'),
        d_start=d_start,
        d_end=d_end,
    )
