# config.py
import os
from dotenv import load_dotenv
from datetime import timedelta
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_change_this')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=int(os.getenv('SESSION_SECONDS', '3600')))

    SHEETS = {
        'credenciales': {
            'nombre': 'DATOS DE ASESOR - CENTRO PROFESIONAL DOCENTE',
            'id': os.getenv('SHEET_CREDENCIALES_ID', '148ihDOBboVOf7vDOFnqaqDSXH1dO3yB_yXiX5454UCY'),
            'worksheets': {'usuarios': 'CREDENCIALES'},
        },
        'ventas': {
            'id': '15sZo9tyeF-hw0Pgd8YrDgJBNkUPXBF0u6BTEj8-p3Fw',
            'worksheets': {'registro': 'QUERYS'},
        },
        'dashboard': {
            'id': '1oH5ta9J3anG78SbdrU6m4iF0SmIbJpR3GaN9vztVA5w',
            'worksheets': {'registro': 'OCTUBRE-2025'},
        },
    }

    # Preferimos Secret File en Render; fallback a GOOGLE_APPLICATION_CREDENTIALS; último a SERVICE_ACCOUNT_FILE
    SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SA_FILE', '/etc/secrets/sa.json')

    # (Opcional) JSON completo de SA como env var, si algún entorno lo usa
    SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT')
