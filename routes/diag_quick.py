# routes/diag_quick.py
from flask import Blueprint
from services.google_sheet_service import GoogleSheetService

diag_quick_bp = Blueprint("diag_quick", __name__, url_prefix="/diag-quick")

@diag_quick_bp.route("/peek")
def peek():
    svc = GoogleSheetService()
    rows = svc.get_all_records('dashboard', 'registro')
    print("=== DIAG QUICK ===")
    if rows:
        headers = list(rows[0].keys())
        print("HEADERS DASH:", headers)
        print("PERSONAL sample:", [(r.get('PERSONAL') or r.get('PERSONAL  ')) for r in rows[:10]])
        print("FECHA sample:", [r.get('FECHA DE LA VENTA') or r.get('Marca temporal') for r in rows[:10]])
        print("MONTO sample:", [r.get('MONTO DEPOSITADO') for r in rows[:10]])
    else:
        print("No hay rows en dashboard/registro")
    return "OK (revisa la consola del servidor)", 200
