from datetime import datetime, timezone

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
