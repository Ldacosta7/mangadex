"""
app/__init__.py — v2
Flask-Session pour isoler les conversations par utilisateur.
"""

from flask import Flask
from flask_session import Session
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__, template_folder="templates")

    # Clé secrète pour signer les cookies de session
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "mangabot-dev-secret-change-in-prod"
    )

    # Flask-Session — stockage serveur (filesystem)
    app.config["SESSION_TYPE"]      = "filesystem"
    app.config["SESSION_FILE_DIR"]  = ".flask_sessions"
    app.config["SESSION_PERMANENT"] = False

    Session(app)

    from app.routes import bp
    app.register_blueprint(bp)

    return app