# routes/__init__.py
from flask import Blueprint, redirect, url_for
from .ventas import ventas_bp
# Blueprint "core" para rutas generales (como la raíz "/")
core_bp = Blueprint("core", __name__)
from .dashboard_user import bp as dashboard_user_bp
from .diag_quick import diag_quick_bp
from .diag import diag_bp

@core_bp.route("/")
def index():
    """Redirige al dashboard si hay sesión, si no al login."""
    from flask import session  # import local para evitar ciclos
    if "user" in session:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))

def register_blueprints(app):
    """Registra todos los blueprints del proyecto."""
    # Importes locales para evitar import circular
    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .datos import datos_bp

    app.register_blueprint(core_bp)        # raíz /
    app.register_blueprint(auth_bp)        # /auth/...
    app.register_blueprint(dashboard_bp)   # /dashboard/...
    app.register_blueprint(datos_bp)       # /datos/...
    app.register_blueprint(ventas_bp)
    app.register_blueprint(dashboard_user_bp)
    app.register_blueprint(diag_quick_bp)
    app.register_blueprint(diag_bp)