# routes/dashboard.py
from flask import Blueprint, render_template, session, flash
from routes.auth import login_required
from services.google_sheet_service import gs_service
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    user = session.get('user') or {}
    user_posicion = int(user.get('posicion', 0))  # Posición del usuario actual
    total_registros = None
    error_fuente = None

    # --- Lógica para el leaderboard ---
    try:
        credenciales = gs_service.get_all_records(
            book_name='credenciales',
            worksheet_name='usuarios'
        )
        usuarios = [
            {
                'nombre': row.get('Nombres y Apellidos'),
                'posicion': int(row.get('Posicion', 0)),
                'volumen': float(row.get('Volumen', 0)),
                'codigo': row.get('Codigo')
            }
            for row in credenciales
            if row.get('Posicion') and row.get('Volumen')
        ]
        usuarios_ordenados = sorted(usuarios, key=lambda x: x['posicion'])
        usuario_actual = next(
            (u for u in usuarios_ordenados if u['codigo'] == user.get('codigo')),
            None
        )
        leaderboard = []
        if usuario_actual:
            idx = usuarios_ordenados.index(usuario_actual)
            if idx == 0:  # Si es el #1, mostrar 2 y 3
                leaderboard = usuarios_ordenados[idx:idx+3]
            else:
                leaderboard = usuarios_ordenados[max(0, idx-1):idx+2]
    except Exception as e:
        print(f"❌ Error al cargar leaderboard: {e}")
        leaderboard = []

    # --- Lógica para total_registros (como en tu código original) ---
    try:
        datos = gs_service.get_all_records(book_name='datos', worksheet_name='datos')
        total_registros = len(datos)
    except Exception as e:
        error_fuente = "datos"
        try:
            datos = gs_service.get_all_records(book_name='dashboard', worksheet_name='registro')
            total_registros = len(datos)
            error_fuente = None
        except Exception as e2:
            try:
                datos = gs_service.get_all_records(book_name='ventas', worksheet_name='registro')
                total_registros = len(datos)
                error_fuente = None
            except Exception as e3:
                total_registros = 0
                print(f"❌ No se pudo cargar recuento: {e} | {e2} | {e3}")

    if error_fuente == "datos":
        flash("Aviso: El libro 'datos' no está configurado. Mostrando conteo desde otra fuente.", "info")

    # --- Obtener la fecha y hora actual ---
    now = datetime.now()

    # --- Renderizar el template con todos los datos ---
    return render_template(
        'dashboard/index.html',
        user=user,
        total_registros=total_registros,
        now=now,
        leaderboard=leaderboard
    )
