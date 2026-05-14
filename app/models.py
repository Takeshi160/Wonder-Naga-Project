from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ─────────────────────────────────────────────
# USER MODEL
# ─────────────────────────────────────────────
class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(64),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(256)
    )

    is_admin = db.Column(
        db.Boolean,
        default=False
    )

    recommendations = db.relationship(
        'Recommendation',
        backref='author',
        lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


# ─────────────────────────────────────────────
# RECOMMENDATION MODEL
# ─────────────────────────────────────────────
class Recommendation(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(100),
        nullable=False
    )

    category = db.Column(
        db.String(50),
        nullable=False
    )

    subcategory = db.Column(
        db.String(50)
    )

    description = db.Column(
        db.String(500),
        nullable=False
    )

    location = db.Column(
        db.String(200)
    )

    image = db.Column(
        db.String(300)
    )

    latitude = db.Column(
        db.Float
    )

    longitude = db.Column(
        db.Float
    )

    rating = db.Column(
        db.Float,
        default=5.0
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    reason = db.Column(
        db.String(200)
    )

    hours = db.Column(
        db.String(50)
    )

    contact = db.Column(
        db.String(50)
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id')
    )

    def to_dict(self):

        return {
            "id": self.id,
            "name": self.title,
            "category": self.category,
            "subcategory": self.subcategory,
            "description": self.description,
            "location": self.location,
            "image_url": self.image,
            "hours": self.hours,
            "contact": self.contact,
            "avg_rating": self.rating,
            "latitude": self.latitude,
            "longitude": self.longitude
        }

    def __repr__(self):
        return f'<Recommendation {self.title}>'
