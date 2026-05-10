from flask import render_template, flash, redirect, url_for, request
from app import app, db

from app.forms import (
    LoginForm,
    RegistrationForm,
    EditProfileForm,
    EmptyForm,
    PostForm,
    RecommendationForm
)

from app.models import User, Post, Recommendation

from flask_login import (
    current_user,
    login_user,
    logout_user,
    login_required
)

import sqlalchemy as sa
from urllib.parse import urlsplit


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():

        user = db.session.scalar(
            sa.select(User).where(
                User.username == form.username.data
            )
        )

        if user is None or not user.check_password(form.password.data):

            return render_template(
                'auth.html',
                title='Sign In',
                form=form,
                mode='login',
                error='Invalid username or password'
            )

        login_user(
            user,
            remember=form.remember_me.data
        )

        next_page = request.args.get('next')

        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')

        flash("Welcome back!")

        return redirect(next_page)

    return render_template(
        'auth.html',
        title='Sign In',
        form=form,
        mode='login',
        error=None
    )


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────
@app.route('/logout')
@login_required
def logout():

    logout_user()

    flash("You have been logged out.")

    return redirect(url_for('login'))


# ─────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────
@app.route('/')
@app.route('/index')
@login_required
def index():

    recommendations = db.session.scalars(
        sa.select(Recommendation)
        .order_by(Recommendation.id.desc())
    ).all()

    featured = db.session.scalar(
        sa.select(Recommendation)
        .order_by(Recommendation.id.desc())
    )

    top_stores = db.session.scalars(
        sa.select(Recommendation)
        .order_by(Recommendation.id.desc())
        .limit(4)
    ).all()

    return render_template(
        'index.html',
        recommendations=recommendations,
        featured=featured,
        top_stores=top_stores
    )


# ─────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():

    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()

    if form.validate_on_submit():

        user = User(
            username=form.username.data,
            email=form.email.data
        )

        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash('Account created successfully!')

        return redirect(url_for('login'))

    return render_template(
        'auth.html',
        title='Register',
        form=form,
        mode='register',
        error=None
    )


# ─────────────────────────────────────────────
# ADD RECOMMENDATION
# ─────────────────────────────────────────────
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():

    form = RecommendationForm()

    form.category.choices = [
        ('restaurant', 'Restaurant'),
        ('cafe', 'Cafe'),
        ('store', 'Store'),
        ('attraction', 'Attraction')
    ]

    if form.validate_on_submit():

        new_rec = Recommendation(
            title=form.title.data,
            category=form.category.data,
            description=form.description.data,
            location=form.location.data,
            reason=form.reason.data,
            hours=form.hours.data,
            contact=form.contact.data,
            user_id=current_user.id
        )

        db.session.add(new_rec)
        db.session.commit()

        flash("Recommendation added successfully!")

        return redirect(url_for('index'))

    return render_template(
        'add.html',
        form=form,
        success=False,
        error=None
    )


# ─────────────────────────────────────────────
# EDIT RECOMMENDATION
# ─────────────────────────────────────────────
@app.route('/edit_rec/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_rec(id):

    rec = db.session.get(Recommendation, id)

    if rec is None:
        flash("Recommendation not found.")
        return redirect(url_for('index'))

    # SECURITY CHECK
    if rec.user_id != current_user.id:
        flash("You cannot edit this recommendation.")
        return redirect(url_for('index'))

    form = RecommendationForm()

    form.category.choices = [
        ('restaurant', 'Restaurant'),
        ('cafe', 'Cafe'),
        ('store', 'Store'),
        ('attraction', 'Attraction')
    ]

    if form.validate_on_submit():

        rec.title = form.title.data
        rec.category = form.category.data
        rec.description = form.description.data
        rec.location = form.location.data
        rec.reason = form.reason.data
        rec.hours = form.hours.data
        rec.contact = form.contact.data

        db.session.commit()

        flash("Recommendation updated successfully!")

        return redirect(url_for('store_detail', id=rec.id))

    elif request.method == 'GET':

        form.title.data = rec.title
        form.category.data = rec.category
        form.description.data = rec.description
        form.location.data = rec.location
        form.reason.data = rec.reason
        form.hours.data = rec.hours
        form.contact.data = rec.contact

    return render_template(
        'add.html',
        form=form,
        success=False,
        error=None
    )


# ─────────────────────────────────────────────
# DELETE RECOMMENDATION
# ─────────────────────────────────────────────
@app.route('/delete_rec/<int:id>', methods=['POST'])
@login_required
def delete_rec(id):

    rec = db.session.get(Recommendation, id)

    if rec is None:
        flash("Recommendation not found.")
        return redirect(url_for('index'))

    # SECURITY CHECK
    if rec.user_id != current_user.id:
        flash("You cannot delete this recommendation.")
        return redirect(url_for('index'))

    db.session.delete(rec)
    db.session.commit()

    flash("Recommendation deleted successfully.")

    return redirect(url_for('index'))


# ─────────────────────────────────────────────
# STORE DETAIL PAGE
# ─────────────────────────────────────────────
@app.route('/store/<int:id>')
@login_required
def store_detail(id):

    store = db.session.get(Recommendation, id)

    if store is None:
        flash("Store not found.")
        return redirect(url_for('index'))

    return render_template(
        'store_detail.html',
        store=store
    )


# ─────────────────────────────────────────────
# CATEGORY PAGES
# ─────────────────────────────────────────────
@app.route('/restaurants')
@login_required
def restaurants():

    stores = db.session.scalars(
        sa.select(Recommendation)
        .where(Recommendation.category == 'restaurant')
        .order_by(Recommendation.id.desc())
    ).all()

    return render_template(
        'listing.html',
        stores=stores,
        title='Restaurants',
        category='restaurant'
    )


@app.route('/cafes')
@login_required
def cafes():

    stores = db.session.scalars(
        sa.select(Recommendation)
        .where(Recommendation.category == 'cafe')
        .order_by(Recommendation.id.desc())
    ).all()

    return render_template(
        'listing.html',
        stores=stores,
        title='Cafes',
        category='cafe'
    )


@app.route('/attractions')
@login_required
def attractions():

    stores = db.session.scalars(
        sa.select(Recommendation)
        .where(Recommendation.category == 'attraction')
        .order_by(Recommendation.id.desc())
    ).all()

    return render_template(
        'listing.html',
        stores=stores,
        title='Attractions',
        category='attraction'
    )
