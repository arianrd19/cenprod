# routes/menciones.py
from flask import Blueprint, render_template, request, current_app, url_for
from services.google_sheet_service import GoogleSheetService
from .auth import login_required
from urllib.parse import urlencode

menciones_bp = Blueprint("menciones", __name__, url_prefix="/menciones")

@menciones_bp.route("/", methods=["GET"])
@login_required
def index():
    svc = GoogleSheetService()
    # Parámetros de búsqueda
    q = request.args.get("q", "")
    especialidad = request.args.get("especialidad", "")
    p_certificado = request.args.get("p_certificado", "")
    page = int(request.args.get("page", 1))
    per_page = 15  # Resultados por página

    # Obtener TODOS los resultados primero (sin límite)
    all_results = svc.search_mentions(
        current_app.config,
        q=q or None,
        especialidad=especialidad or None,
        p_certificado=p_certificado or None,
        limit=None  # Sin límite para obtener todos los registros
    )

    # Obtener listas únicas para los selects de especialidad y P. Certificado
    especialidades = sorted(list(set([r['especialidad'] for r in all_results if r['especialidad']])))
    p_certificados = sorted(list(set([r['p_certificado'] for r in all_results if r['p_certificado']])))

    # Calcular paginación
    total = len(all_results)
    total_pages = (total + per_page - 1) // per_page  # División con redondeo hacia arriba
    page = max(1, min(page, total_pages or 1))  # Asegurar que la página esté dentro del rango válido

    # Obtener solo los resultados de la página actual
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_results = all_results[start_idx:end_idx]

    # Construir query strings para los enlaces de paginación
    query_params = {
        'q': q,
        'especialidad': especialidad,
        'p_certificado': p_certificado
    }
    query_params_prev = {**query_params, 'page': page - 1} if page > 1 else {}
    query_params_next = {**query_params, 'page': page + 1} if page < total_pages else {}

    # Información de paginación para la plantilla
    pagination = {
        'page': page,
        'pages': total_pages,
        'total': total,
        'start': start_idx + 1 if total > 0 else 0,
        'end': min(end_idx, total),
        'query_prev': urlencode({k: v for k, v in query_params_prev.items() if v}),
        'query_next': urlencode({k: v for k, v in query_params_next.items() if v}),
        'has_prev': page > 1,
        'has_next': page < total_pages,
    }

    return render_template(
        "menciones/menciones.html",
        q=q,
        especialidad=especialidad,
        p_certificado=p_certificado,
        especialidades=especialidades,
        p_certificados=p_certificados,
        rows=paginated_results,
        pagination=pagination
    )
