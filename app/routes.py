from flask import render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from app import app, db
from app.models import Place, Recommendation, User, Report, SubCategory, RecommendationImage
from app.forms import RecommendationForm, LoginForm, RegistrationForm
from werkzeug.utils import secure_filename
from flask_login import login_required, login_user, logout_user, current_user
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
import base64


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

def admin_required(f):
    """Decorator to check if current user is admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

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
        return jsonify({'token': token, 'username': user.username, 'role': user.role})
    
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
    return jsonify({'token': token, 'username': user.username, 'role': user.role})

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    return jsonify({'message': 'Logged out'})

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def api_me():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'id': user.id,
        'username': user.username,
        'role': user.role
    })

# =========================================
# STORE API ROUTES (FOR VUE APP)
# =========================================

@app.route('/api/stores/featured', methods=['GET'])
def api_featured():
    rec = Recommendation.query.first()
    if not rec:
        return jsonify({})
    
    return jsonify({
        'id': rec.id,
        'name': rec.title,
        'image_url': rec.image_url,
        'category': rec.category,
        'location': rec.location,
        'description': rec.description,
        'hours': rec.hours,
        'avg_rating': rec.avg_rating,
        'contact': rec.contact,
        'reason': rec.reason,
        'sub_category': {
            'name': rec.sub_category.name,
            'icon': rec.sub_category.icon
        } if rec.sub_category else None
    })

@app.route('/api/stores/top', methods=['GET'])
def api_top_stores():
    recs = Recommendation.query.all()
    return jsonify([
        {
            'id': r.id,
            'name': r.title,
            'location': r.location,
            'category': r.category,
            'description': r.description,
            'hours': r.hours,
            'image_url': r.image_url,
            'avg_rating': r.avg_rating,
            'contact': r.contact,
            'reason': r.reason,
            'author': r.author.username if r.author else 'Unknown',
            'sub_category': {
                'name': r.sub_category.name,
                'icon': r.sub_category.icon
            } if r.sub_category else None
        }
        for r in recs
    ])

@app.route('/api/stores', methods=['GET'])
def api_stores():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    sub_category = request.args.get('sub_category', '')
    
    query = Recommendation.query
    
    if category:
        query = query.filter_by(category=category)
    
    if sub_category:
        query = query.filter_by(sub_category_id=sub_category)
    
    if search:
        query = query.filter(
            Recommendation.title.ilike(f"%{search}%") | 
            Recommendation.description.ilike(f"%{search}%") |
            Recommendation.location.ilike(f"%{search}%")
        )
    
    recs = query.all()
    return jsonify([
        {
            'id': r.id,
            'name': r.title,
            'location': r.location,
            'category': r.category,
            'description': r.description,
            'hours': r.hours,
            'image_url': r.image_url,
            'avg_rating': r.avg_rating,
            'contact': r.contact,
            'reason': r.reason,
            'author': r.author.username if r.author else 'Unknown',
            'sub_category': {
                'name': r.sub_category.name,
                'icon': r.sub_category.icon
            } if r.sub_category else None
        }
        for r in recs
    ])

@app.route('/api/stores/<int:id>', methods=['GET'])
def api_store_detail(id):
    rec = Recommendation.query.get_or_404(id)
    
    images = [img.url for img in rec.images.all()] if hasattr(rec, 'images') else []
    
    return jsonify({
        'id': rec.id,
        'name': rec.title,
        'location': rec.location,
        'category': rec.category,
        'description': rec.description,
        'hours': rec.hours,
        'image_url': rec.image_url,
        'avg_rating': rec.avg_rating,
        'contact': rec.contact,
        'reason': rec.reason,
        'author': rec.author.username if rec.author else 'Unknown',
        'sub_category': {
            'name': rec.sub_category.name,
            'icon': rec.sub_category.icon
        } if rec.sub_category else None,
        'gallery': images,
        'reviews': []
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

@app.route('/api/sub-categories', methods=['GET'])
def api_sub_categories():
    category = request.args.get('category', '')
    query = SubCategory.query
    if category:
        query = query.filter_by(category=category)
    subs = query.all()
    return jsonify([
        {
            'id': s.id,
            'name': s.name,
            'icon': s.icon,
            'category': s.category
        }
        for s in subs
    ])

# =========================================
# RECOMMENDATION API ROUTES (CREATE/UPDATE/DELETE)
# =========================================

@app.route('/api/recommendations', methods=['POST'])
def api_add_recommendation():
    name = request.form.get('name')
    location = request.form.get('location')
    category = request.form.get('category')
    description = request.form.get('description')
    hours = request.form.get('hours')
    reason = request.form.get('reason')
    contact = request.form.get('contact')
    sub_category_id = request.form.get('sub_category_id')

    image_url = None
    files = request.files.getlist('images')

    if files and files[0]:
        file = files[0]
        if file and allowed_file(file.filename):
            # Convert image to Base64
            file_data = file.read()
            base64_string = base64.b64encode(file_data).decode('utf-8')
            ext = file.filename.rsplit('.', 1)[1].lower()
            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'webp': 'image/webp'
            }
            mime = mime_types.get(ext, 'image/jpeg')
            image_url = f"data:{mime};base64,{base64_string}"

    rec = Recommendation(
        title=name,
        reason=reason,
        location=location,
        category=category,
        sub_category_id=sub_category_id if sub_category_id else None,
        description=description,
        hours=hours,
        contact=contact,
        image_url=image_url,
        avg_rating=5,
        user_id=current_user.id if current_user.is_authenticated else 1
    )

    db.session.add(rec)
    db.session.commit()

    return jsonify({'message': 'Recommendation added successfully', 'id': rec.id})

@app.route('/api/recommendations/<int:id>', methods=['PUT'])
@jwt_required()
def api_edit_recommendation(id):
    user_id = get_jwt_identity()
    rec = Recommendation.query.get_or_404(id)
    
    # Check if user owns this recommendation or is admin
    user = User.query.get(int(user_id))
    if rec.user_id != user.id and user.role != 'admin':
        return jsonify({'error': 'Not authorized'}), 403
    
    # Update fields
    rec.title = request.form.get('name', rec.title)
    rec.location = request.form.get('location', rec.location)
    rec.category = request.form.get('category', rec.category)
    rec.description = request.form.get('description', rec.description)
    rec.hours = request.form.get('hours', rec.hours)
    rec.reason = request.form.get('reason', rec.reason)
    rec.contact = request.form.get('contact', rec.contact)
    
    sub_category_id = request.form.get('sub_category_id')
    if sub_category_id:
        rec.sub_category_id = sub_category_id
    
    # Handle new image if uploaded
    files = request.files.getlist('images')
    if files and files[0]:
        file = files[0]
        if file and allowed_file(file.filename):
            file_data = file.read()
            base64_string = base64.b64encode(file_data).decode('utf-8')
            ext = file.filename.rsplit('.', 1)[1].lower()
            mime_types = {
                'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'gif': 'image/gif', 'webp': 'image/webp'
            }
            mime = mime_types.get(ext, 'image/jpeg')
            rec.image_url = f"data:{mime};base64,{base64_string}"
    
    db.session.commit()
    return jsonify({'message': 'Recommendation updated successfully'})

@app.route('/api/recommendations/<int:id>', methods=['DELETE'])
@jwt_required()
def api_delete_recommendation(id):
    user_id = get_jwt_identity()
    rec = Recommendation.query.get_or_404(id)
    
    user = User.query.get(int(user_id))
    if rec.user_id != user.id and user.role != 'admin':
        return jsonify({'error': 'Not authorized'}), 403
    
    db.session.delete(rec)
    db.session.commit()
    return jsonify({'message': 'Recommendation deleted successfully'})

# =========================================
# REPORT API ROUTES
# =========================================

@app.route('/api/reports', methods=['POST'])
@jwt_required()
def api_create_report():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    store_id = data.get('store_id')
    reason = data.get('reason')
    
    if not store_id or not reason:
        return jsonify({'error': 'Store ID and reason are required'}), 400
    
    # Check if already reported by this user
    existing = Report.query.filter_by(store_id=store_id, reporter_id=user_id).first()
    if existing:
        return jsonify({'error': 'You have already reported this store'}), 400
    
    report = Report(
        store_id=store_id,
        reporter_id=user_id,
        reason=reason,
        status='pending'
    )
    db.session.add(report)
    db.session.commit()
    
    return jsonify({'message': 'Report submitted successfully'})

@app.route('/api/reports', methods=['GET'])
@jwt_required()
@admin_required
def api_get_reports():
    reports = Report.query.filter_by(status='pending').all()
    return jsonify([
        {
            'id': r.id,
            'store_id': r.store_id,
            'store_name': r.reported_rec.title if r.reported_rec else 'Unknown',
            'reporter': r.reporter.username if r.reporter else 'Unknown',
            'reason': r.reason,
            'status': r.status,
            'created_at': r.created_at.isoformat() if r.created_at else None
        }
        for r in reports
    ])

@app.route('/api/reports/<int:id>/dismiss', methods=['POST'])
@jwt_required()
@admin_required
def api_dismiss_report(id):
    report = Report.query.get_or_404(id)
    report.status = 'dismissed'
    db.session.commit()
    return jsonify({'message': 'Report dismissed'})

@app.route('/api/reports/<int:id>/resolve', methods=['POST'])
@jwt_required()
@admin_required
def api_resolve_report(id):
    report = Report.query.get_or_404(id)
    report.status = 'resolved'
    db.session.commit()
    return jsonify({'message': 'Report resolved'})

# =========================================
# ADMIN API ROUTES
# =========================================

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
@admin_required
def api_admin_users():
    users = User.query.all()
    return jsonify([
        {
            'id': u.id,
            'username': u.username,
            'role': u.role,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'recommendation_count': u.recommendations.count()
        }
        for u in users
    ])

@app.route('/api/admin/users/<int:id>/promote', methods=['POST'])
@jwt_required()
@admin_required
def api_promote_user(id):
    user = User.query.get_or_404(id)
    user.role = 'admin'
    db.session.commit()
    return jsonify({'message': f'User {user.username} promoted to admin'})

@app.route('/api/admin/users/<int:id>/demote', methods=['POST'])
@jwt_required()
@admin_required
def api_demote_user(id):
    user = User.query.get_or_404(id)
    user.role = 'user'
    db.session.commit()
    return jsonify({'message': f'User {user.username} demoted to user'})

@app.route('/api/admin/users/<int:id>', methods=['DELETE'])
@jwt_required()
@admin_required
def api_delete_user(id):
    user = User.query.get_or_404(id)
    if user.id == get_jwt_identity():
        return jsonify({'error': 'Cannot delete yourself'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'User {user.username} deleted'})

@app.route('/api/admin/sub-categories', methods=['POST'])
@jwt_required()
@admin_required
def api_add_sub_category():
    data = request.get_json()
    name = data.get('name')
    icon = data.get('icon', '📌')
    category = data.get('category')
    
    if not name or not category:
        return jsonify({'error': 'Name and category are required'}), 400
    
    sub = SubCategory(name=name, icon=icon, category=category)
    db.session.add(sub)
    db.session.commit()
    return jsonify({'message': 'Sub-category added', 'id': sub.id})

@app.route('/api/admin/sub-categories/<int:id>', methods=['DELETE'])
@jwt_required()
@admin_required
def api_delete_sub_category(id):
    sub = SubCategory.query.get_or_404(id)
    db.session.delete(sub)
    db.session.commit()
    return jsonify({'message': 'Sub-category deleted'})

# =========================================
# MAIN ROUTE - SERVE VUE APP
# =========================================

@app.route('/')
def home():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(project_root, 'index.html')

# =========================================
# HTML PAGE ROUTES (FOR JINJA2 TEMPLATES)
# =========================================

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
                file_data = file.read()
                base64_string = base64.b64encode(file_data).decode('utf-8')
                ext = file.filename.rsplit('.', 1)[1].lower()
                mime_types = {
                    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                    'gif': 'image/gif', 'webp': 'image/webp'
                }
                mime = mime_types.get(ext, 'image/jpeg')
                image_url = f"data:{mime};base64,{base64_string}"
        
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
