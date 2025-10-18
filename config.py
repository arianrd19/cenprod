import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_change_this')

    # Configuración de sesión
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=int(os.getenv('SESSION_SECONDS', '3600')))

    # Google Sheets — IDs de documentos
    SHEETS = {
        'credenciales': {
            'nombre': 'DATOS DE ASESOR - CENTRO PROFESIONAL DOCENTE',
            'id': os.getenv('SHEET_CREDENCIALES_ID', '148ihDOBboVOf7vDOFnqaqDSXH1dO3yB_yXiX5454UCY'),
            'worksheets': {
                'usuarios': 'CREDENCIALES',
            },
        },
        'ventas': {
            'id': '15sZo9tyeF-hw0Pgd8YrDgJBNkUPXBF0u6BTEj8-p3Fw',  # ID de tu URL
            'worksheets': {
                'registro': 'QUERYS'  # cambia si tu pestaña se llama distinto
                }
            },
        'dashboard': {
            'id': '1oH5ta9J3anG78SbdrU6m4iF0SmIbJpR3GaN9vztVA5w',  # ID de tu URL
            'worksheets': {
                'registro': 'OCTUBRE-2025'  # cambia si tu pestaña se llama distinto
                }
            },
    }

    # Ruta al JSON del service account
    SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'service_account.json')
