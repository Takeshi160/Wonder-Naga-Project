from app import db
from flask_login import UserMixin


# =========================
# USER MODEL (REQUIRED FIX)
# =========================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

    def __repr__(self):
        return f'<User {self.username}>'


# =========================
# PLACE MODEL (YOUR ORIGINAL)
# =========================

class Place(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    location = db.Column(
        db.String(200),
        nullable=False
    )

    category = db.Column(
        db.String(50),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    hours = db.Column(
        db.String(100)
    )

    image_url = db.Column(
        db.String(300)
    )

    avg_rating = db.Column(
        db.Float,
        default=5
    )

    def __repr__(self):
        return f'<Place {self.name}>'
