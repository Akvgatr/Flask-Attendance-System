from flask import Flask
from .extensions import db, migrate, login_manager
from pathlib import Path

def create_app(config_class=None):
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
        static_url_path="/static"
    )

    if config_class is not None:
        app.config.from_object(config_class)
    else:
        BASE = Path(__file__).resolve().parent
        INSTANCE = BASE.parents[2] / "instance"
        INSTANCE.mkdir(parents=True, exist_ok=True)

        db_path = (INSTANCE / "attendance.db")
        db_uri = f"sqlite:///{db_path.as_posix()}"

        app.config.update(
            SQLALCHEMY_DATABASE_URI=db_uri,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY="dev-secret",  # replace in prod
            DEBUG=True,
        )

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    login_manager.login_view = "web.student_login"

    from . import models

    # register blueprints
    from .views import web_bp
    from .api import api_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()

    return app
