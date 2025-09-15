# src/create_db.py
from demo.website import create_app
from demo.website.extensions import db

app = create_app()
with app.app_context():
    from demo.website import models  # ensure models are imported
    db.create_all()
    print("Tables created at:", app.config["SQLALCHEMY_DATABASE_URI"])
