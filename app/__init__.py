from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os

app = Flask(__name__)

# =========================
# CONFIG
# =========================

DATABASE_URL = os.environ.get("DATABASE_URL")

# Fix Render PostgreSQL URL
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg://",
        1
    )

elif DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "wondernaga-secret-key"
app.config["JWT_SECRET_KEY"] = "wondernaga-jwt-secret"

app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path,
    "static/uploads"
)

# =========================
# EXTENSIONS
# =========================

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login = LoginManager(app)
jwt = JWTManager(app)

CORS(app)

# =========================
# IMPORT MODELS FIRST
# =========================

from app import models

# =========================
# USER LOADER (FIX)
# =========================

from app.models import User  # IMPORTANT (you must have this model)

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# ROUTES
# =========================

from app import routes
