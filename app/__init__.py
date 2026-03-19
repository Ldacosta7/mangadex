from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    """Crée et configure l'application Flask."""
    app = Flask(__name__, template_folder="../app/templates")

    # Enregistre les routes
    from app.routes import bp
    app.register_blueprint(bp)

    return app