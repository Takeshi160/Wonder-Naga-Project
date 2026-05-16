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
    reports = db.relationship('Report', backref='reporter', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'


# =========================
# PLACE MODEL (admin-curated stores)
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
# SUB-CATEGORY MODEL
# =========================

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(10), default='📌')
    category = db.Column(db.String(50), nullable=False)  # parent category
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SubCategory {self.name}>'


# =========================
# RECOMMENDATION MODEL (user submissions)
# =========================

class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)  # Store name
    reason = db.Column(db.Text)  # Why they recommend it
    location = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    hours = db.Column(db.String(100))
    contact = db.Column(db.String(100))
    image_url = db.Column(db.Text)  # Base64 or URL
    avg_rating = db.Column(db.Float, default=5)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    images = db.relationship('RecommendationImage', backref='recommendation', lazy='dynamic', cascade='all, delete-orphan')
    sub_category = db.relationship('SubCategory', backref='recommendations', lazy=True)
    reports = db.relationship('Report', backref='reported_rec', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Recommendation {self.title}>'


class RecommendationImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendation.id'), nullable=False)
    url = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# REPORT MODEL
# =========================

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('recommendation.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'dismissed', 'resolved'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Report {self.id}>'


# =========================
# REVIEW MODEL (ratings & comments)
# =========================

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendation.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1–5 stars
    comment = db.Column(db.Text, nullable=True)       # optional comment text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = db.relationship('User', backref='reviews', lazy=True)
    recommendation = db.relationship('Recommendation', backref='reviews', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('recommendation_id', 'user_id', name='uix_one_review_per_user'),
    )

    def __repr__(self):
        return f'<Review {self.rating}★ by {self.user_id}>'
