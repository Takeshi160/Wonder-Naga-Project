from flask import render_template, request, jsonify, redirect, url_for, flash
from app import app, db
from app.models import Place, Recommendation, User
from app.forms import RecommendationForm, LoginForm, RegistrationForm
from werkzeug.utils import secure_filename
from flask_login import login_required, login_user, logout_user, current_user
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
    
# =========================================
# UPLOAD CONFIG
# =========================================

UPLOAD_FOLDER = 'app/static/uploads'

ALLOWED_EXTENSIONS = {
    'png',
    'jpg',
    'jpeg',
    'gif',
    'webp'
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================================
# HELPERS
# =========================================

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# =========================================
# AUTH API ROUTES (FOR VUE APP)
# =========================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        token = create_access_token(identity=str(user.id))
        return jsonify({'token': token, 'username': user.username})
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    name = data.get('name', username)
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    user = User(
        username=username,
        password=generate_password_hash(password),
        role='user'
    )
    db.session.add(user)
    db.session.commit()
    
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'username': user.username})

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    return jsonify({'message': 'Logged out'})

# =========================================
# STORE API ROUTES (FOR VUE APP)
# =========================================

@app.route('/api/stores/featured', methods=['GET'])
def api_featured():
    place = Place.query.first()
    if not place:
        return jsonify({})
    
    return jsonify({
        'id': place.id,
        'name': place.name,
        'image_url': place.image_url,
        'category': place.category,
        'location': place.location,
        'description': place.description,
        'hours': place.hours,
        'avg_rating': place.avg_rating
    })

@app.route('/api/stores/top', methods=['GET'])
def api_top_stores():
    places = Place.query.all()
    return jsonify([
        {
            'id': p.id,
            'name': p.name,
            'location': p.location,
            'category': p.category,
            'description': p.description,
            'hours': p.hours,
            'image_url': p.image_url,
            'avg_rating': p.avg_rating
        }
        for p in places
    ])

@app.route('/api/stores', methods=['GET'])
def api_stores():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    query = Place.query
    
    if category:
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(
            Place.name.ilike(f"%{search}%") | 
            Place.description.ilike(f"%{search}%") |
            Place.location.ilike(f"%{search}%")
        )
    
    places = query.all()
    return jsonify([
        {
            'id': p.id,
            'name': p.name,
            'location': p.location,
            'category': p.category,
            'description': p.description,
            'hours': p.hours,
            'image_url': p.image_url,
            'avg_rating': p.avg_rating
        }
        for p in places
    ])

@app.route('/api/stores/<int:id>', methods=['GET'])
def api_store_detail(id):
    place = Place.query.get_or_404(id)
    
    # Get images
    images = [img.url for img in place.images.all()] if hasattr(place, 'images') else []
    
    return jsonify({
        'id': place.id,
        'name': place.name,
        'location': place.location,
        'category': place.category,
        'description': place.description,
        'hours': place.hours,
        'image_url': place.image_url,
        'avg_rating': place.avg_rating,
        'contact': getattr(place, 'contact', ''),
        'gallery': images,
        'reviews': []  # Add reviews later if needed
    })

@app.route('/api/categories', methods=['GET'])
def api_categories():
    return jsonify([
        {'value': 'restaurant', 'label': 'Restaurant'},
        {'value': 'cafe', 'label': 'Cafe'},
        {'value': 'shop', 'label': 'Shop'},
        {'value': 'attraction', 'label': 'Attraction'},
        {'value': 'other', 'label': 'Other'}
    ])

@app.route('/api/recommendations', methods=['POST'])
def api_add_recommendation():
    name = request.form.get('name')
    location = request.form.get('location')
    category = request.form.get('category')
    description = request.form.get('description')
    hours = request.form.get('hours')
    reason = request.form.get('reason')
    contact = request.form.get('contact')

    image_url = None
    files = request.files.getlist('images')

    if files and files[0]:
        file = files[0]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4()}_{filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(save_path)
            image_url = f"/static/uploads/{unique_name}"

    rec = Recommendation(
        title=name,
        reason=reason,
        location=location,
        category=category,
        description=description,
        hours=hours,
        contact=contact,
        image_url=image_url,
        avg_rating=5,
        user_id=1  # Default user for now
    )

    db.session.add(rec)
    db.session.commit()

    return jsonify({'message': 'Recommendation added successfully'})

# =========================================
# HTML PAGE ROUTES (FOR JINJA2 TEMPLATES)
# =========================================

@app.route('/')
def home():
    featured = Place.query.first()
    top_stores = Place.query.all()
    recommendations = Recommendation.query.all()
    
    return render_template('index.html', 
                         featured=featured, 
                         top_stores=top_stores, 
                         recommendations=recommendations)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    error = None
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('home'))
        else:
            error = 'Invalid username or password'
    
    return render_template('auth.html', mode='login', form=form, error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    error = None
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            password=generate_password_hash(form.password.data),
            role='user'
        )
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('home'))
    
    return render_template('auth.html', mode='register', form=form, error=error)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/store/<int:id>')
def store_detail(id):
    place = Place.query.get_or_404(id)
    return render_template('store_detail.html', place=place)

@app.route('/add', methods=['GET', 'POST'])
def add():
    form = RecommendationForm()
    if form.validate_on_submit():
        image_url = None
        files = request.files.getlist('images')
        
        if files and files[0]:
            file = files[0]
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4()}_{filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(save_path)
                image_url = f"/static/uploads/{unique_name}"
        
        rec = Recommendation(
            title=form.name.data,
            reason=form.reason.data,
            location=form.location.data,
            category=form.category.data,
            description=form.description.data,
            hours=form.hours.data,
            contact=form.contact.data,
            image_url=image_url,
            avg_rating=5,
            user_id=current_user.id if current_user.is_authenticated else 1
        )
        
        db.session.add(rec)
        db.session.commit()
        
        return redirect(url_for('home'))
    
    return render_template('add.html', form=form)

@app.route('/restaurants')
def restaurants():
    items = Recommendation.query.filter_by(category='restaurant').all()
    return render_template('category.html', items=items, category='restaurants', category_name='Restaurants')

@app.route('/cafes')
def cafes():
    items = Recommendation.query.filter_by(category='cafe').all()
    return render_template('category.html', items=items, category='cafes', category_name='Cafes')

@app.route('/shops')
def shops():
    items = Recommendation.query.filter_by(category='shop').all()
    return render_template('category.html', items=items, category='shops', category_name='Shops')

@app.route('/attractions')
def attractions():
    items = Recommendation.query.filter_by(category='attraction').all()
    return render_template('category.html', items=items, category='attractions', category_name='Attractions')

@app.route('/places')
def places():
    items = Recommendation.query.all()
    return render_template('category.html', items=items, category='places', category_name='All Places')

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    
    if not q:
        return redirect(url_for('home'))
    
    from sqlalchemy import or_
    
    query = Recommendation.query.filter(
        or_(
            Recommendation.title.ilike(f'%{q}%'),
            Recommendation.description.ilike(f'%{q}%'),
            Recommendation.location.ilike(f'%{q}%'),
            Recommendation.reason.ilike(f'%{q}%')
        )
    )
    
    if category:
        query = query.filter_by(category=category)
    
    items = query.all()
    
    return render_template('search.html', 
                         items=items, 
                         q=q, 
                         category=category,
                         category_name=category.capitalize() if category else 'All')

# =========================================
# OLD API ROUTES (KEEP FOR BACKWARD COMPATIBILITY)
# =========================================

@app.route('/api/stores', methods=['GET'])
def get_stores():
    places = Place.query.all()
    return jsonify([
        {
            'id': p.id,
            'name': p.name,
            'location': p.location,
            'category': p.category,
            'description': p.description,
            'hours': p.hours,
            'image_url': p.image_url,
            'avg_rating': p.avg_rating
        }
        for p in places
    ])

@app.route('/api/delete/<int:id>', methods=['DELETE'])
def delete_place(id):
    place = Place.query.get_or_404(id)
    db.session.delete(place)
    db.session.commit()
    return jsonify({'message': 'Place deleted'})

@app.route('/api/featured')
def featured_place():
    place = Place.query.first()
    if not place:
        return jsonify({})
    return jsonify({
        'id': place.id,
        'name': place.name,
        'image_url': place.image_url,
        'category': place.category,
        'location': place.location
    })

@app.route('/api/filter')
def filter_places():
    query = Place.query
    category = request.args.get('category')
    location = request.args.get('location')
    sort = request.args.get('sort')

    if category:
        query = query.filter_by(category=category)
    if location:
        query = query.filter(Place.location.ilike(f"%{location}%"))
    if sort == 'az':
        query = query.order_by(Place.name.asc())
    elif sort == 'za':
        query = query.order_by(Place.name.desc())
    elif sort == 'rating':
        query = query.order_by(Place.avg_rating.desc())

    return jsonify([
        {
            'id': p.id,
            'name': p.name,
            'location': p.location,
            'category': p.category,
            'description': p.description,
            'hours': p.hours,
            'image_url': p.image_url,
            'avg_rating': p.avg_rating
        }
        for p in query.all()
    ])
