# routes/dashboard_admin.py
from flask import Blueprint, render_template, session, flash, redirect, url_for
from services.google_sheet_service import gs_service
from .auth import login_required, role_required

admin_bp = Blueprint("dashboard_admin", __name__, url_prefix="/dashboard-admin")


@admin_bp.route("/")
@login_required
@role_required("admin")
def admin_dashboard():
    user = session.get("user", {}) or {}

    try:
        credenciales = gs_service.get_all_records(
            book_name="credenciales",
            worksheet_name="usuarios"
        )
        asesores = [
            {
                "codigo": (row.get("Codigo") or row.get("Código") or "").strip(),
                "nombre": row.get("Nombres y Apellidos") or row.get("Nombre") or "",
                "email": row.get("Email") or "",
                "rol": row.get("Rol", "usuario"),
                "volumen": row.get("Volumen") or "",
                "ventas": row.get("Ventas") or "",
            }
            for row in credenciales
            if (row.get("Codigo") or row.get("Código"))
        ]
        # opcional: ordenar por nombre o codigo
        asesores = sorted(asesores, key=lambda a: a["nombre"])
    except Exception as e:
        print(f"❌ Error cargando asesores: {e}")
        flash("No se pudieron cargar los usuarios desde CREDENCIALES.", "error")
        asesores = []

    return render_template(
        "dashboard/admin.html",
        admin=user,
        asesores=asesores,
    )
