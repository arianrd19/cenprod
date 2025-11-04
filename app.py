# app.py
from flask import Flask
from config import Config
from routes import register_blueprints
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Registrar filtro personalizado para Jinja2
    @app.template_filter('parse_date')
    def parse_date_filter(s):
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except Exception:
            return datetime.now().date()  # Fecha por defecto si falla el parseo

    # Registrar todos los blueprints (incluye la raíz "/")
    register_blueprints(app)

    # Variables disponibles en todas las plantillas Jinja
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {"now": datetime.now()}

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
