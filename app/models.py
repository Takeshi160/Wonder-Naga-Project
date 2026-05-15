from app import db
from flask_login import UserMixin
from datetime import datetime

# =========================
# USER MODEL
# =========================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    places = db.relationship('Place', backref='author', lazy='dynamic')
    recommendations = db.relationship('Recommendation', backref='author', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

# =========================
# PLACE MODEL
# =========================

class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    hours = db.Column(db.String(100))
    image_url = db.Column(db.String(300))
    avg_rating = db.Column(db.Float, default=5)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    images = db.relationship('PlaceImage', backref='place', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Place {self.name}>'

class PlaceImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =========================
# RECOMMENDATION MODEL
# =========================

class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    reason = db.Column(db.Text)
    location = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    hours = db.Column(db.String(100))
    contact = db.Column(db.String(100))
    image_url = db.Column(db.Text)  # Changed from String(300) to Text for Base64
    avg_rating = db.Column(db.Float, default=5)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    images = db.relationship('RecommendationImage', backref='recommendation', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Recommendation {self.title}>'

class RecommendationImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendation.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
