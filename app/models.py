from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from hashlib import md5
followers = sa.Table(
'followers',
db.metadata,
sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'),
primary_key=True),
sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'),
primary_key=True)
)
class User(UserMixin, db.Model):
id: so.Mapped[int] = so.mapped_column(primary_key=True)
username: so.Mapped[str] = so.mapped_column(
sa.String(64),
index=True,
unique=True
)
email: so.Mapped[str] = so.mapped_column(
sa.String(120),
index=True,
unique=True
)
password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
is_admin: so.Mapped[bool] = so.mapped_column(default=False)
about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
default=lambda: datetime.now(timezone.utc)
)
posts: so.Mapped[list['Post']] = so.relationship(back_populates='author')
recommendations: so.Mapped[list['Recommendation']] = so.relationship(
back_populates='author'
)
following: so.WriteOnlyMapped['User'] = so.relationship(
secondary=followers,
primaryjoin=(followers.c.follower_id == id),
secondaryjoin=(followers.c.followed_id == id),
back_populates='followers'
)
followers: so.WriteOnlyMapped['User'] = so.relationship(
secondary=followers,
primaryjoin=(followers.c.followed_id == id),
secondaryjoin=(followers.c.follower_id == id),
back_populates='following'
)
def set_password(self, password):
self.password_hash = generate_password_hash(password)
def check_password(self, password):
return check_password_hash(self.password_hash, password)
def avatar(self, size):
digest = md5(self.email.lower().encode('utf-8')).hexdigest()
return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
def __repr__(self):
return f'<User {self.username}>'
class Post(db.Model):
id: so.Mapped[int] = so.mapped_column(primary_key=True)
body: so.Mapped[str] = so.mapped_column(sa.String(140))
timestamp: so.Mapped[datetime] = so.mapped_column(
index=True,
default=lambda: datetime.now(timezone.utc)
)
user_id: so.Mapped[int] = so.mapped_column(
sa.ForeignKey(User.id),
index=True
)
author: so.Mapped[User] = so.relationship(back_populates='posts')
class Recommendation(db.Model):
id = db.Column(db.Integer, primary_key=True)
title = db.Column(db.String(100), nullable=False)
category = db.Column(db.String(50), nullable=False)
subcategory = db.Column(db.String(50))
description = db.Column(db.Text, nullable=False)
location = db.Column(db.String(200))
reason = db.Column(db.String(300))
hours = db.Column(db.String(100))
contact = db.Column(db.String(100))
image_url = db.Column(db.String(500))
rating = db.Column(db.Float, default=5.0)
latitude = db.Column(db.Float)
longitude = db.Column(db.Float)
timestamp = db.Column(db.DateTime, default=datetime.utcnow)
user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
author = db.relationship('User', back_populates='recommendations')
def to_dict(self):
return {
'id': self.id,
'name': self.title,
'category': self.category,
'subcategory': self.subcategory,
'description': self.description,
'location': self.location,
'reason': self.reason,
'hours': self.hours,
'contact': self.contact,
'image_url': self.image_url,
'avg_rating': self.rating,
'latitude': self.latitude,
'longitude': self.longitude
}
def __repr__(self):
return f'<Recommendation {self.title}>'
@login.user_loader
def load_user(id):
return db.session.get(User, int(id))
