# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.google_sheet_service import gs_service
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def _norm_pwd(x):
    """
    Normaliza el valor de contraseña proveniente de Sheets para compararlo de forma robusta.
    - Convierte int/float a str sin '.0'
    - Hace strip de espacios
    """
    if x is None:
        return ''
    try:
        # Si viene como float (p. ej. 12345678.0), quita .0
        if isinstance(x, float):
            if x.is_integer():
                return str(int(x))
            return str(x).strip()
        # Si viene como int, a str
        if isinstance(x, int):
            return str(x)
    except Exception:
        pass
    return str(x).strip()


def _norm_commission_to_float(pct_raw):
    """Convierte '10' o '10%' o 0.1 -> float 0.1; si falla, None."""
    try:
        s = str(pct_raw).strip().replace('%', '')
        if s == '':
            return None
        val = float(s)
        return val / 100.0 if val > 1 else val
    except Exception:
        return None


def _safe_float(v, default=0.0):
    """Convierte '1,234.50' o 'S/ 1,234.50' a float. Si falla, default."""
    try:
        return float(str(v).replace('S/', '').replace(',', '').strip())
    except Exception:
        return default


def _safe_int(v, default=0):
    """Convierte '10', '10.0', '  10 ' a int. Si falla, default."""
    try:
        s = str(v).strip()
        if s == '':
            return default
        return int(float(s))
    except Exception:
        return default

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está logueado, redirigir
    if 'user' in session:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not email or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('auth/login.html')
        try:
            # Buscar usuario en 'credenciales' -> hoja lógica 'usuarios' (CREDENCIALES)
            user = gs_service.find_record(
                book_name='credenciales',
                worksheet_name='usuarios',
                column='Email',
                value=email
            )
            if user:
                entered = (password or '').strip()
                stored = _norm_pwd(user.get('Contraseña'))
                ok = (entered == stored)
                if not ok:
                    ok = (entered.lstrip('0') == stored.lstrip('0'))
                # Si tus contraseñas son de longitud fija, puedes reforzar con zfill(n)
                if ok:
                    # Verificar estado
                    if user.get('Estado', '').strip().lower() != 'activo':
                        flash('Tu cuenta está inactiva. Contacta al administrador.', 'error')
                        return render_template('auth/login.html')
                    # Normalizar comisión y código
                    comision_float = _norm_commission_to_float(user.get('Comisión'))
                    if comision_float is None:
                        comision_float = 0.10  # fallback estándar si no hay dato
                    codigo = (user.get('Codigo') or user.get('Código') or '').strip()
                    # 🆕 Nuevos campos desde CREDENCIALES
                    raw_posicion = user.get('Posicion') or user.get('Posición')
                    posicion = str(raw_posicion).strip().title() if raw_posicion not in (None, '') else ''
                    volumen = _safe_float(user.get('Volumen'), default=0.0)  # número (S/)
                    ventas = _safe_int(user.get('Ventas'), default=0)        # entero (# de ventas)
                    # Guardar sesión
                    session['user'] = {
                        'email':    user.get('Email'),
                        'username': user.get('Username'),
                        'nombre':   user.get('Nombres y Apellidos'),
                        'rol':      user.get('Rol', 'usuario'),
                        'comision': comision_float,  # float 0–1
                        'codigo':   codigo,          # <--- MUY IMPORTANTE
                        # 🆕 Campos añadidos
                        'posicion': posicion,        # str (ej. "Asesor Senior")
                        'volumen':  volumen,         # float (S/)
                        'ventas':   ventas,          # int
                    }
                    session.permanent = True
                    # flash(f'¡Bienvenido {user.get("Nombres y Apellidos")}!', 'success')  # Comenta o elimina esta línea
                    return redirect(url_for('dashboard.index'))
                else:
                    flash('Contraseña incorrecta', 'error')
            else:
                flash('Usuario no encontrado', 'error')
        except Exception as e:
            flash('Error al conectar con el servidor. Intenta nuevamente.', 'error')
            print(f"❌ Error en login: {e}")
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    nombre = session.get('user', {}).get('nombre', 'Usuario')
    session.clear()
    # flash(f'Hasta luego {nombre}', 'info')  # Comenta o elimina esta línea
    return redirect(url_for('auth.login'))


# Decorador para proteger rutas
def login_required(f):
    """Decorador para requerir autenticación en las rutas"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorador para requerir roles específicos"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Debes iniciar sesión primero', 'error')
                return redirect(url_for('auth.login'))

            user_role = session['user'].get('rol', '').lower()
            allowed_roles = [role.lower() for role in roles]

            if user_role not in allowed_roles:
                flash('No tienes permisos para acceder a esta página', 'error')
                return redirect(url_for('dashboard.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator
