import os
import sqlalchemy as sa

from flask import (
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash
)

from werkzeug.utils import secure_filename

from flask_login import (
    login_user,
    logout_user,
    current_user,
    login_required
)

from app import app, db
from app.models import User, Recommendation

# ─────────────────────────────────────────────
# UPLOAD CONFIG
# ─────────────────────────────────────────────
UPLOAD_FOLDER = 'app/static/uploads'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {
    'png',
    'jpg',
    'jpeg',
    'gif'
}

def allowed_file(filename):

    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─────────────────────────────────────────────
# FRONTEND
# ─────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')


# ─────────────────────────────────────────────
# AUTH API
# ─────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def api_register():

    data = request.get_json()

    existing = db.session.scalar(
        sa.select(User).where(
            User.username == data.get('username')
        )
    )

    if existing:
        return jsonify({
            "message": "Username already exists"
        }), 400

    user = User(
        username=data.get('username'),
        email=f"{data.get('username')}@gmail.com"
    )

    user.set_password(data.get('password'))

    db.session.add(user)
    db.session.commit()

    login_user(user)

    return jsonify({
        "message": "Registered successfully",
        "token": "logged-in"
    })


@app.route('/api/auth/login', methods=['POST'])
def api_login():

    data = request.get_json()

    user = db.session.scalar(
        sa.select(User).where(
            User.username == data.get('username')
        )
    )

    if user is None:
        return jsonify({
            "message": "User not found"
        }), 401

    if not user.check_password(data.get('password')):
        return jsonify({
            "message": "Invalid password"
        }), 401

    login_user(user)

    return jsonify({
        "message": "Login successful",
        "token": "logged-in"
    })


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():

    logout_user()

    return jsonify({
        "message": "Logged out"
    })


# ─────────────────────────────────────────────
# FEATURED STORE
# ─────────────────────────────────────────────
@app.route('/api/stores/featured')
def featured_store():

    store = db.session.scalar(
        sa.select(Recommendation)
        .order_by(Recommendation.rating.desc())
    )

    if not store:
        return jsonify(None)

    return jsonify(store.to_dict())


# ─────────────────────────────────────────────
# TOP STORES
# ─────────────────────────────────────────────
@app.route('/api/stores/top')
def top_stores():

    stores = db.session.scalars(
        sa.select(Recommendation)
        .order_by(Recommendation.rating.desc())
        .limit(8)
    ).all()

    return jsonify([
        store.to_dict()
        for store in stores
    ])


# ─────────────────────────────────────────────
# GET STORES
# ─────────────────────────────────────────────
@app.route('/api/stores')
def get_stores():

    category = request.args.get('category')

    search = request.args.get('search', '')

    sort = request.args.get('sort')

    query = sa.select(Recommendation)

    if category:

        query = query.where(
            Recommendation.category == category
        )

    if search:

        query = query.where(
            Recommendation.title.ilike(f"%{search}%")
        )

    if sort == 'az':

        query = query.order_by(
            Recommendation.title.asc()
        )

    elif sort == 'za':

        query = query.order_by(
            Recommendation.title.desc()
        )

    elif sort == 'rating':

        query = query.order_by(
            Recommendation.rating.desc()
        )

    stores = db.session.scalars(query).all()

    return jsonify([
        store.to_dict()
        for store in stores
    ])


# ─────────────────────────────────────────────
# STORE DETAIL
# ─────────────────────────────────────────────
@app.route('/api/stores/<int:id>')
def store_detail(id):

    store = db.session.get(
        Recommendation,
        id
    )

    if not store:

        return jsonify({
            "message": "Store not found"
        }), 404

    return jsonify(store.to_dict())


# ─────────────────────────────────────────────
# ADD RECOMMENDATION
# ─────────────────────────────────────────────
@app.route('/api/recommendations', methods=['POST'])
@login_required
def add_recommendation():

    image_url = None

    if 'images' in request.files:

        image = request.files['images']

        if image and allowed_file(image.filename):

            filename = secure_filename(
                image.filename
            )

            filepath = os.path.join(
                UPLOAD_FOLDER,
                filename
            )

            image.save(filepath)

            image_url = f"/static/uploads/{filename}"

    recommendation = Recommendation(

        title=request.form.get('name'),

        category=request.form.get('category'),

        subcategory=request.form.get('subcategory'),

        description=request.form.get('description'),

        location=request.form.get('location'),

        reason=request.form.get('reason'),

        hours=request.form.get('hours'),

        contact=request.form.get('contact'),

        image=image_url,

        rating=5,

        user_id=current_user.id
    )

    db.session.add(recommendation)

    db.session.commit()

    return jsonify({
        "message": "Recommendation added successfully"
    })


# ─────────────────────────────────────────────
# ADMIN PAGE
# ─────────────────────────────────────────────
@app.route('/admin')
@login_required
def admin():

    if not current_user.is_admin:

        flash("Access denied.")

        return redirect(url_for('home'))

    stores = db.session.scalars(
        sa.select(Recommendation)
    ).all()

    return render_template(
        'admin.html',
        stores=stores
    )


# ─────────────────────────────────────────────
# DELETE STORE
# ─────────────────────────────────────────────
@app.route('/delete/<int:id>')
@login_required
def delete_store(id):

    if not current_user.is_admin:

        flash("Access denied.")

        return redirect(url_for('home'))

    store = db.session.get(
        Recommendation,
        id
    )

    if store:

        db.session.delete(store)

        db.session.commit()

    return redirect(url_for('admin'))
