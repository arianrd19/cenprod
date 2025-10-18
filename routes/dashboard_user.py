# routes/dashboard_user.py
from flask import Blueprint, render_template, session, current_app, flash, request
from datetime import date, timedelta
from services.google_sheet_service import GoogleSheetService
from .auth import login_required

bp = Blueprint("dashboard_user", __name__, url_prefix="/mi-dashboard")


def _month_range_today():
    """Devuelve (hoy, primer_dia_mes_actual, ultimo_dia_mes_actual)."""
    today = date.today()  # TZ: America/Lima
    first = today.replace(day=1)
    if today.month == 12:
        next_first = date(today.year + 1, 1, 1)
    else:
        next_first = date(today.year, today.month + 1, 1)
    last = next_first - timedelta(days=1)
    return today, first, last


@bp.route("/")
@login_required
def me_dashboard():
    # --- Usuario en sesión
    user = session.get("user", {})
    username = ( user.get("name") or user.get("nombre") or "").strip()

    # --- Rango del mes actual
    today, first_day, last_day = _month_range_today()

    # Overrides por querystring para debug rápido:
    #   ?codigo=00123   -> fuerza el código
    #   ?nofilter=1     -> ignora el filtro de fechas (toma todo)
    codigo_override = request.args.get("codigo", "").strip()
    nofilter = request.args.get("nofilter") == "1"
    if nofilter:
        first_day = date(1900, 1, 1)
        last_day = date(2999, 12, 31)

    # --- Servicio
    svc = GoogleSheetService()

    # --- 1) Código del usuario
    codigo = (user.get("codigo") or "").strip()
    if codigo_override:
        codigo = codigo_override
    if not codigo:
        codigo = svc.get_user_code(username, current_app.config)

    if not codigo:
        flash("No se encontró el Código del usuario en CREDENCIALES. Verifica tu registro.", "error")
        stats = {"count": 0, "total_monto": 0.0, "ventas": []}
    else:
        # --- 2) Ventas del mes (PERSONAL == codigo)
        stats = svc.get_sales_by_code(codigo, first_day, last_day, current_app.config)

    # --- 3) Comisión (float 0–1): usar la de sesión; si no, hoja/default
    pct = user.get("comision")
    if pct is None:
        pct = svc.get_user_commission_pct(username, current_app.config)

    # --- 4) KPIs
    total = stats.get("total_monto", 0.0)
    count = stats.get("count", 0)
    commission = round(total * (pct or 0.0), 2)
    avg_ticket = round(total / count, 2) if count else 0.0
    ultimas = stats.get("ventas", [])[:10]

    return render_template(
    "dashboard/usuario.html",
    username=username or "Usuario",
    month=today.strftime("%B %Y").title(),
    count=count,
    total=total,
    commission=commission,
    pct=int((pct or 0.0) * 100),
    avg_ticket=avg_ticket,
    ultimas=ultimas,
    codigo=codigo,
    nofilter=nofilter,

    # Extras de credenciales
    posicion=session.get('user',{}).get('posicion'),
    volumen_cred=session.get('user',{}).get('volumen'),
    ventas_cred=session.get('user',{}).get('ventas'),
)

