import os
from flask import Flask
from .extensions import db, migrate, login_manager
from pathlib import Path
from dotenv import load_dotenv

# Load .env locally only
load_dotenv()

def create_app(config_class=None):
    app = Flask(__name__,
                static_folder="static",
                template_folder="templates",
                static_url_path="/static")

    if config_class is not None:
        app.config.from_object(config_class)
    else:
        # Determine database URL
        db_uri = os.environ.get("DATABASE_URL")
        if not db_uri:
            # Local fallback SQLite
            BASE = Path(__file__).resolve().parent.parent.parent  # project root
            INSTANCE = BASE / "instance"
            INSTANCE.mkdir(parents=True, exist_ok=True)
            db_uri = f"sqlite:///{(INSTANCE / 'attendance.db').as_posix()}"

        secret_key = os.environ.get("SECRET_KEY", "dev-secret")

        app.config.update(
            SQLALCHEMY_DATABASE_URI=db_uri,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY=secret_key,
            DEBUG=os.environ.get("FLASK_ENV", "development") == "development"
        )

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "web.student_login"

    from . import models
    from .views import web_bp
    from .api import api_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()

    return app
