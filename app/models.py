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
    role = db.Column(db.String(20), default='user')  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    places = db.relationship('Place', backref='author', lazy='dynamic')
    recommendations = db.relationship('Recommendation', backref='author', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'


# =========================
# PLACE MODEL (for admin-curated stores)
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
    
    # Images relationship
    images = db.relationship('PlaceImage', backref='place', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Place {self.name}>'


# =========================
# PLACE IMAGE MODEL (multiple images per place)
# =========================

class PlaceImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# RECOMMENDATION MODEL (user submissions)
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
    image_url = db.Column(db.String(300))
    avg_rating = db.Column(db.Float, default=5)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # NEW: Sub-category
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'))
    sub_category = db.relationship('SubCategory', backref='recommendations')
    
    images = db.relationship('RecommendationImage', backref='recommendation', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Recommendation {self.title}>'


class RecommendationImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendation.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('recommendation.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reporter = db.relationship('User', backref='reports', lazy=True)
    store = db.relationship('Recommendation', backref='reports', lazy=True)

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(10), nullable=False)  # emoji like 🍕
    created_at = db.Column(db.DateTime, default=datetime.utcnow)