from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os

app = Flask(__name__)

# =========================
# CONFIG
# =========================

basedir = os.path.abspath(os.path.dirname(__file__))

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Fix Render PostgreSQL URL
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    # Local development: SQLite in project folder
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "wondernaga-secret-key"
app.config["JWT_SECRET_KEY"] = "wondernaga-jwt-secret"

# JWT Token Expiry Settings:
# - Remember Me checked: permanent (no expiry)
# - Remember Me unchecked: 24 hours
# This is controlled in the login route based on user choice
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # Default: permanent (can be overridden per-token)

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

# FIXED: CORS with credentials support for Vue frontend
CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": "*",
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    }
})

# =========================
# IMPORT MODELS FIRST
# =========================

from app import models

# =========================
# USER LOADER (FIX)
# =========================

from app.models import User

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# AUTO-CREATE MISSING TABLES (safe for Render)
# =========================

with app.app_context():
    db.create_all()

# =========================
# ROUTES
# =========================

from app import routes
