"""
SQLAlchemy database instance.
Import `db` from here in models and wherever db.session is needed.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
