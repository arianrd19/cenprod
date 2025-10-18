from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required, role_required
from services.google_sheet_service import gs_service

datos_bp = Blueprint('datos', __name__, url_prefix='/datos')

@datos_bp.route('/')
@login_required
def lista():
    """Lista todos los datos del libro 'datos'"""
    try:
        # Usar el libro 'datos' con la hoja 'principal' (ajusta el nombre si aplica)
        datos = gs_service.get_all_records(
            book_name='datos',
            worksheet_name='principal'
        )
        return render_template('datos/lista.html', datos=datos)
    except Exception as e:
        flash('Error al cargar los datos', 'error')
        print(f"❌ Error: {e}")
        return render_template('datos/lista.html', datos=[])

@datos_bp.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    """Agrega un nuevo registro al libro 'datos'"""
    if request.method == 'POST':
        # Ajusta estos campos según las columnas de tu hoja
        campo1 = request.form.get('campo1')
        campo2 = request.form.get('campo2')
        campo3 = request.form.get('campo3')
        
        if not campo1:
            flash('El campo 1 es obligatorio', 'error')
            return render_template('datos/agregar.html')
        
        try:
            # Agregar al libro 'datos', hoja 'principal'
            exito = gs_service.add_record(
                book_name='datos',
                worksheet_name='principal',
                data=[campo1, campo2, campo3]  # Ajusta según tus columnas
            )
            
            if exito:
                flash('✅ Registro agregado exitosamente', 'success')
                return redirect(url_for('datos.lista'))
            else:
                flash('❌ Error al agregar el registro', 'error')
        except Exception as e:
            flash('Error al procesar la solicitud', 'error')
            print(f"❌ Error: {e}")
    
    return render_template('datos/agregar.html')

@datos_bp.route('/buscar')
@login_required
def buscar():
    """Busca registros en el libro 'datos'"""
    query = request.args.get('q', '').strip()
    campo = request.args.get('campo', 'nombre')
    
    if not query:
        return redirect(url_for('datos.lista'))
    
    try:
        # Buscar en el libro 'datos', hoja 'principal'
        resultados = gs_service.find_all_records(
            book_name='datos',
            worksheet_name='principal',
            column=campo,
            value=query
        )
        
        if not resultados:
            flash(f'No se encontraron resultados para "{query}"', 'info')
        
        return render_template('datos/lista.html', datos=resultados)
    except Exception as e:
        flash('Error al buscar', 'error')
        print(f"❌ Error: {e}")
        return redirect(url_for('datos.lista'))

# Ruta protegida por rol (solo admin)
@datos_bp.route('/admin/limpiar')
@login_required
@role_required('admin', 'administrador')
def limpiar_cache():
    """Limpia el cache de Google Sheets (solo admin)"""
    try:
        gs_service.clear_cache()
        flash('Cache limpiado exitosamente', 'success')
    except Exception as e:
        flash('Error al limpiar cache', 'error')
        print(f"❌ Error: {e}")
    
    return redirect(url_for('datos.lista'))

# API endpoint para obtener datos en JSON
@datos_bp.route('/api/lista')
@login_required
def api_lista():
    """Devuelve los datos en formato JSON"""
    try:
        datos = gs_service.get_all_records(
            book_name='datos',
            worksheet_name='principal'
        )
        return jsonify({'success': True, 'datos': datos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Ejemplo: Trabajar con otra hoja del mismo libro
@datos_bp.route('/reportes')
@login_required
def reportes():
    """Muestra datos de la hoja 'reportes' del libro 'datos'"""
    try:
        reportes = gs_service.get_all_records(
            book_name='datos',
            worksheet_name='reportes'
        )
        return render_template('datos/reportes.html', reportes=reportes)
    except Exception as e:
        flash('Error al cargar reportes', 'error')
        print(f"❌ Error: {e}")
        return redirect(url_for('dashboard.index'))
