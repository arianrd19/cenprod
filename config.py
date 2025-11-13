# config.py
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()  # carga .env en local; en Render no estorba

ROOT = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_change_this')

    # Sesión
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(
        seconds=int(os.getenv('SESSION_SECONDS', '3600'))
    )

    # IDs de Sheets (deja los tuyos)
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
            'id': '17HJ1796Y9OuF21L8X_aveY0sic-evFda7YCLUnoHTLY',
            'worksheets': {'registro': 'NOVIEMBRE-2025'},
        },
        'menciones': {
        'id': '1zaFo7ZJq0yAIjNwcTWJiCr3odCzs6ZYL_ibRE8yrkeM',
        'worksheets': {
            'registro': 'MENCIONES'},
    },
        "cobranzas": {
            "id": "15sZo9tyeF-hw0Pgd8YrDgJBNkUPXBF0u6BTEj8-p3Fw",  # ID de la hoja de Google Sheets
            "worksheets": {
                "registro": 'QUERYS',  # Ej: "Cobranzas 2024"
            }
    }

}

    # Resuelve credenciales de Google en este orden:
    # 1) GOOGLE_SA_FILE (ruta a archivo: /etc/secrets/sa.json en Render, ./service_account.json en local)
    # 2) GOOGLE_APPLICATION_CREDENTIALS (convención Google)
    # 3) ./service_account.json si existe (solo local)
    SERVICE_ACCOUNT_FILE = (
        os.getenv('GOOGLE_SA_FILE')
        or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        or (str(ROOT / 'service_account.json') if (ROOT / 'service_account.json').exists() else None)
    )

    # 4) Alternativa: JSON completo en env (si algún entorno lo usa)
    SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT')
