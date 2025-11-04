# routes/cobranza.py
from flask import Blueprint, render_template, session, current_app, flash, request
from datetime import date, timedelta
from services.google_sheet_service import gs_service
from .auth import login_required

bp = Blueprint("cobranza", __name__, url_prefix="/mi-cobranza")

def _month_range_today():
    """Devuelve (hoy, primer_día_mes_actual, último_día_mes_actual)."""
    today = date.today()
    first = today.replace(day=1)
    if today.month == 12:
        next_first = date(today.year + 1, 1, 1)
    else:
        next_first = date(today.year, today.month + 1, 1)
    last = next_first - timedelta(days=1)
    return today, first, last
@bp.route("/")
@login_required
def mi_cobranza():
    # --- Usuario en sesión
    user = session.get("user", {})
    username = (user.get("name") or user.get("nombre") or "").strip()

    # --- Rango del mes actual
    today, first_day, last_day = _month_range_today()

    # Overrides por querystring para debug rápido
    codigo_override = request.args.get("codigo", "").strip()
    nofilter = request.args.get("nofilter") == "1"
    if nofilter:
        first_day = date(1900, 1, 1)
        last_day = date(2999, 12, 31)

    # --- Servicio
    svc = gs_service

    # --- 1) Código del usuario
    codigo = (user.get("codigo") or "").strip()
    if codigo_override:
        codigo = codigo_override
    if not codigo:
        codigo = svc.get_user_code(username, current_app.config)
    if not codigo:
        flash("No se encontró el Código del usuario en CREDENCIALES. Verifica tu registro.", "error")
        return render_template("cobranza/mi_cobranza.html", cobranzas=[])

    # --- 2) Obtener la lista de cobranzas (PERSONAL == codigo y MONTO TOTAL != MONTO DEPOSITADO)
    stats = svc.get_cobranzas_by_code(codigo, first_day, last_day, current_app.config)
    cobranzas = stats.get("cobranzas", [])

    # --- Renderizar la plantilla con la lista de cobranzas
    return render_template(
        "cobranza/mi_cobranza.html",
        cobranzas=cobranzas,
        codigo=codigo,
        nofilter=nofilter,
        username=username or "Usuario",
        month=today.strftime("%B %Y").title(),
    )
