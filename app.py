# app.py
from flask import Flask
from config import Config
from routes import register_blueprints

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

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
