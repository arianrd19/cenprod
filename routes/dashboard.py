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

        if usuarios_ordenados:
            primero = usuarios_ordenados[0]

            if usuario_actual:
                idx = usuarios_ordenados.index(usuario_actual)

                # Si eres el #1 → top 3 como antes
                if idx == 0:
                    leaderboard = usuarios_ordenados[:3]
                else:
                    # Siempre anclamos el primer puesto
                    leaderboard.append(primero)
                    usados = {primero['codigo']}

                    # Tu posición
                    if usuario_actual['codigo'] not in usados:
                        leaderboard.append(usuario_actual)
                        usados.add(usuario_actual['codigo'])

                    # El que va después de ti (si existe)
                    next_idx = idx + 1
                    if next_idx < len(usuarios_ordenados):
                        siguiente = usuarios_ordenados[next_idx]
                        if siguiente['codigo'] not in usados:
                            leaderboard.append(siguiente)
            else:
                # Si no encontramos al usuario actual, mostramos top 3 por defecto
                leaderboard = usuarios_ordenados[:3]

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
