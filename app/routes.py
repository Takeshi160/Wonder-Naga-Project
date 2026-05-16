from flask import render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from app import app, db
from app.models import Place, Recommendation, User, Report, SubCategory, RecommendationImage, Review, Favorite, Notification
from app.forms import RecommendationForm, LoginForm, RegistrationForm
from werkzeug.utils import secure_filename
from flask_login import login_required, login_user, logout_user, current_user
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
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
    """Decorator to check if current user is admin (supports both Flask-Login and JWT)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check Flask-Login first
        if current_user.is_authenticated and current_user.role == 'admin':
            return f(*args, **kwargs)
        # Then check JWT
        try:
            verify_jwt_in_request(optional=True)
            jwt_user_id = get_jwt_identity()
            if jwt_user_id:
                user = User.query.get(int(jwt_user_id))
                if user and user.role == 'admin':
                    return f(*args, **kwargs)
        except Exception:
            pass
        return jsonify({'error': 'Admin access required'}), 403
    return decorated_function

def get_current_user_for_template():
    """Get current user for template rendering (supports both Flask-Login and JWT)"""
    if current_user.is_authenticated:
        return current_user
    try:
        verify_jwt_in_request(optional=True)
        jwt_user_id = get_jwt_identity()
        if jwt_user_id:
            user = User.query.get(int(jwt_user_id))
            if user:
                return user
    except Exception:
        pass
    return None

def create_notification(user_id, message, type='general', link=None):
    """Helper to create a notification"""
    notif = Notification(
        user_id=user_id,
        message=message,
        type=type,
        link=link,
        is_read=False
    )
    db.session.add(notif)
    db.session.commit()
    return notif

# =========================================
# AUTH API ROUTES (FOR VUE APP)
# =========================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    remember_me = data.get('remember_me', False)  # NEW: Remember Me checkbox

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        # If Remember Me is checked, create permanent token (no expiry)
        # If unchecked, create 24-hour token
        if remember_me:
            token = create_access_token(identity=str(user.id), expires_delta=False)
        else:
            from datetime import timedelta
            token = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=24))

        # Also create a Flask session for Jinja2 pages
        login_user(user, remember=remember_me)
        return jsonify({
            'token': token,
            'id': user.id,
            'username': user.username,
            'name': user.name or user.username,
            'role': user.role,
            'remember_me': remember_me  # Send back so frontend knows
        })

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
        name=name,  # FIXED: save name to DB
        role='user'
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    # Also create Flask session
    login_user(user)
    return jsonify({
        'token': token,
        'id': user.id,
        'username': user.username,
        'name': user.name or username,
        'role': user.role
    })

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    logout_user()
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
        'name': user.name or user.username,
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

# =========================================
# MERGED /api/stores - handles ALL params
# =========================================
@app.route('/api/stores', methods=['GET'])
def api_stores():
    """Get stores with filtering, search, min_rating, and sorting"""
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    sub_category = request.args.get('sub_category', '')
    min_rating = request.args.get('min_rating', '')
    sort_by = request.args.get('sort_by', '')  # 'newest', 'rating_desc', 'rating_asc', 'name'

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

    if min_rating:
        try:
            query = query.filter(Recommendation.avg_rating >= float(min_rating))
        except ValueError:
            pass

    # FIXED: Handle all sort_by values from frontend
    if sort_by == 'newest':
        query = query.order_by(Recommendation.created_at.desc())
    elif sort_by == 'rating_desc':
        query = query.order_by(Recommendation.avg_rating.desc())
    elif sort_by == 'rating_asc':
        query = query.order_by(Recommendation.avg_rating.asc())
    elif sort_by == 'name':
        query = query.order_by(Recommendation.title.asc())

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
            'name': r.sub_category.name,
            'icon': r.sub_category.icon
        } if rec.sub_category else None,
        'gallery': images,
        'reviews': []
    })

@app.route('/api/stores/all', methods=['GET'])
def api_all_places():
    """Get all places regardless of category"""
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
            'contact': r.contact
        }
        for r in recs
    ])

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
# RECOMMENDATION API ROUTES
# =========================================

@app.route('/api/recommendations', methods=['GET'])
def api_get_recommendations():
    """Public endpoint to get all recommendations (for home page)"""
    recs = Recommendation.query.all()
    return jsonify([
        {
            'id': r.id,
            'title': r.title,
            'name': r.title,
            'reason': r.reason,
            'location': r.location,
            'category': r.category,
            'description': r.description,
            'hours': r.hours,
            'contact': r.contact,
            'image_url': r.image_url,
            'avg_rating': r.avg_rating,
            'user_id': r.user_id,
            'author': r.author.username if r.author else 'Unknown'
        }
        for r in recs
    ])

@app.route('/api/recommendations', methods=['POST'])
@jwt_required()
def api_add_recommendation():
    user_id = get_jwt_identity()
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
        user_id=user_id
    )

    db.session.add(rec)
    db.session.commit()

    return jsonify({'message': 'Recommendation added successfully', 'id': rec.id})

@app.route('/api/recommendations/<int:id>', methods=['PUT'])
@jwt_required()
def api_edit_recommendation(id):
    user_id = get_jwt_identity()
    rec = Recommendation.query.get_or_404(id)

    user = User.query.get(int(user_id))
    if rec.user_id != user.id and user.role != 'admin':
        return jsonify({'error': 'Not authorized'}), 403

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

    # Notify reporter
    if report.reporter_id:
        create_notification(
            report.reporter_id,
            f"Your report on '{report.reported_rec.title if report.reported_rec else 'a store'}' was dismissed.",
            type='report',
            link=f"/store/{report.store_id}"
        )

    return jsonify({'message': 'Report dismissed'})

@app.route('/api/reports/<int:id>/resolve', methods=['POST'])
@jwt_required()
@admin_required
def api_resolve_report(id):
    report = Report.query.get_or_404(id)
    report.status = 'resolved'
    db.session.commit()

    # Notify reporter
    if report.reporter_id:
        create_notification(
            report.reporter_id,
            f"Your report on '{report.reported_rec.title if report.reported_rec else 'a store'}' was resolved.",
            type='report',
            link=f"/store/{report.store_id}"
        )

    return jsonify({'message': 'Report resolved'})

# =========================================
# ADMIN API ROUTES
# =========================================

@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
@admin_required
def api_admin_stats():
    users = User.query.count()
    recommendations = Recommendation.query.count()
    reports = Report.query.filter_by(status='pending').count()
    return jsonify({
        'users': users,
        'recommendations': recommendations,
        'reports': reports
    })

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

@app.route('/api/admin/stores', methods=['GET'])
@jwt_required()
@admin_required
def api_admin_stores():
    recs = Recommendation.query.all()
    return jsonify([
        {
            'id': r.id,
            'title': r.title,
            'name': r.title,
            'category': r.category,
            'location': r.location,
            'author': r.author.username if r.author else 'Unknown',
            'user_id': r.user_id,
            'image_url': r.image_url,
            'avg_rating': r.avg_rating
        }
        for r in recs
    ])

@app.route('/api/admin/users/<int:id>/promote', methods=['POST'])
@jwt_required()
@admin_required
def api_promote_user(id):
    user = User.query.get_or_404(id)
    user.role = 'admin'
    db.session.commit()

    # Notify user
    create_notification(
        user.id,
        "You have been promoted to Admin!",
        type='admin'
    )

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
    if user.id == int(get_jwt_identity()):
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

# Catch-all route: serve Vue app for any non-API, non-static paths
# This fixes "Internal Server Error" when navigating from /admin back to Vue pages
@app.route('/<path:path>')
def catch_all(path):
    # Don't intercept API routes or static files
    if path.startswith('api/') or path.startswith('static/'):
        return jsonify({'error': 'Not found'}), 404
    # Serve the Vue app for all other routes (Vue Router handles client-side navigation)
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
    try:
        # Support both Flask-Login session and JWT token
        user = get_current_user_for_template()

        if not user or user.role != 'admin':
            return render_template('admin.html', 
                current_user=user,
                total_users=0,
                total_stores=0,
                pending_reports=[],
                users=[],
                all_stores=[],
                dynamic_subcats=[]
            )

        total_users = User.query.count()
        total_stores = Recommendation.query.count()
        pending_reports = Report.query.filter_by(status='pending').all()
        users = User.query.all()
        all_stores = Recommendation.query.all()
        dynamic_subcats = SubCategory.query.all()

        return render_template('admin.html',
            current_user=user,
            total_users=total_users,
            total_stores=total_stores,
            pending_reports=pending_reports,
            users=users,
            all_stores=all_stores,
            dynamic_subcats=dynamic_subcats
        )
    except Exception as e:
        import traceback
        app.logger.error(f"Admin page error: {str(e)}\n{traceback.format_exc()}")
        return f"<h1>Admin Panel Error</h1><pre>{str(e)}</pre><pre>{traceback.format_exc()}</pre>", 500

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
# REVIEW API ROUTES (ratings & comments)
# =========================================

@app.route('/api/reviews/<int:recommendation_id>', methods=['GET'])
def api_get_reviews(recommendation_id):
    """Get all reviews for a recommendation + average rating"""
    reviews = Review.query.filter_by(recommendation_id=recommendation_id).order_by(Review.created_at.desc()).all()
    avg = db.session.query(db.func.avg(Review.rating)).filter_by(recommendation_id=recommendation_id).scalar()
    return jsonify({
        'reviews': [
            {
                'id': r.id,
                'rating': r.rating,
                'comment': r.comment,
                'author': r.author.username if r.author else 'Unknown',
                'user_id': r.user_id,
                'created_at': r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews
        ],
        'average_rating': round(float(avg), 1) if avg else None,
        'total_reviews': len(reviews)
    })

@app.route('/api/reviews', methods=['POST'])
@jwt_required()
def api_add_review():
    """Submit a new review (1 review per user per recommendation)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()

    recommendation_id = data.get('recommendation_id')
    rating = data.get('rating')
    comment = data.get('comment', '').strip()

    if not recommendation_id or not rating:
        return jsonify({'error': 'Recommendation ID and rating are required'}), 400

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    except ValueError:
        return jsonify({'error': 'Rating must be a number'}), 400

    # Check if user already reviewed this recommendation
    existing = Review.query.filter_by(recommendation_id=recommendation_id, user_id=user_id).first()
    if existing:
        return jsonify({'error': 'You have already reviewed this place'}), 400

    review = Review(
        recommendation_id=recommendation_id,
        user_id=user_id,
        rating=rating,
        comment=comment if comment else None
    )
    db.session.add(review)
    db.session.commit()

    # Update the recommendation's avg_rating
    avg = db.session.query(db.func.avg(Review.rating)).filter_by(recommendation_id=recommendation_id).scalar()
    rec = Recommendation.query.get(recommendation_id)
    if rec and avg:
        rec.avg_rating = round(float(avg), 1)
        db.session.commit()

    # FIXED: Notify the recommendation owner
    if rec and rec.user_id and rec.user_id != user_id:
        create_notification(
            rec.user_id,
            f"{User.query.get(int(user_id)).username if User.query.get(int(user_id)) else 'Someone'} reviewed your place '{rec.title}'",
            type='review',
            link=f"/store/{rec.id}"
        )

    return jsonify({
        'message': 'Review submitted successfully',
        'review_id': review.id,
        'average_rating': rec.avg_rating if rec else None
    })

@app.route('/api/reviews/<int:review_id>', methods=['PUT'])
@jwt_required()
def api_update_review(review_id):
    """Edit your own review"""
    user_id = int(get_jwt_identity())
    review = Review.query.get_or_404(review_id)

    if review.user_id != user_id:
        return jsonify({'error': 'Not authorized to edit this review'}), 403

    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment', '').strip()

    if rating:
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return jsonify({'error': 'Rating must be between 1 and 5'}), 400
            review.rating = rating
        except ValueError:
            return jsonify({'error': 'Rating must be a number'}), 400

    if comment:
        review.comment = comment

    db.session.commit()

    # Update average
    avg = db.session.query(db.func.avg(Review.rating)).filter_by(recommendation_id=review.recommendation_id).scalar()
    rec = Recommendation.query.get(review.recommendation_id)
    if rec and avg:
        rec.avg_rating = round(float(avg), 1)
        db.session.commit()

    return jsonify({
        'message': 'Review updated',
        'average_rating': rec.avg_rating if rec else None
    })

@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@jwt_required()
def api_delete_review(review_id):
    """Delete your own review (or admin can delete any)"""
    user_id = int(get_jwt_identity())
    user = User.query.get(int(user_id))
    review = Review.query.get_or_404(review_id)

    if review.user_id != user_id and user.role != 'admin':
        return jsonify({'error': 'Not authorized to delete this review'}), 403

    rec_id = review.recommendation_id
    db.session.delete(review)
    db.session.commit()

    # Update average
    avg = db.session.query(db.func.avg(Review.rating)).filter_by(recommendation_id=rec_id).scalar()
    rec = Recommendation.query.get(rec_id)
    if rec:
        rec.avg_rating = round(float(avg), 1) if avg else 5
        db.session.commit()

    return jsonify({
        'message': 'Review deleted',
        'average_rating': rec.avg_rating if rec else None
    })


# =========================================
# FAVORITES API ROUTES
# =========================================

@app.route('/api/favorites', methods=['GET'])
@jwt_required()
def api_get_favorites():
    """Get current user's favorited recommendations"""
    user_id = int(get_jwt_identity())
    favorites = Favorite.query.filter_by(user_id=user_id).all()
    recs = [f.recommendation for f in favorites if f.recommendation]
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
        }
        for r in recs
    ])

@app.route('/api/favorites/check/<int:rec_id>', methods=['GET'])
@jwt_required()
def api_check_favorite(rec_id):
    """Check if current user has favorited a recommendation"""
    user_id = int(get_jwt_identity())
    fav = Favorite.query.filter_by(user_id=user_id, recommendation_id=rec_id).first()
    return jsonify({'is_favorite': fav is not None})

@app.route('/api/favorites', methods=['POST'])
@jwt_required()
def api_add_favorite():
    """Add a recommendation to favorites"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    rec_id = data.get('recommendation_id')

    if not rec_id:
        return jsonify({'error': 'recommendation_id required'}), 400

    existing = Favorite.query.filter_by(user_id=user_id, recommendation_id=rec_id).first()
    if existing:
        return jsonify({'error': 'Already in favorites'}), 400

    fav = Favorite(user_id=user_id, recommendation_id=rec_id)
    db.session.add(fav)
    db.session.commit()
    return jsonify({'message': 'Added to favorites'})

@app.route('/api/favorites/<int:rec_id>', methods=['DELETE'])
@jwt_required()
def api_remove_favorite(rec_id):
    """Remove a recommendation from favorites"""
    user_id = int(get_jwt_identity())
    fav = Favorite.query.filter_by(user_id=user_id, recommendation_id=rec_id).first()
    if not fav:
        return jsonify({'error': 'Not in favorites'}), 404

    db.session.delete(fav)
    db.session.commit()
    return jsonify({'message': 'Removed from favorites'})

# =========================================
# USER PROFILE API ROUTES
# =========================================

@app.route('/api/users/<int:id>/profile', methods=['GET'])
def api_get_user_profile(id):
    """Get public profile for any user"""
    user = User.query.get_or_404(id)
    recommendations = Recommendation.query.filter_by(user_id=id).all()
    reviews = Review.query.filter_by(user_id=id).order_by(Review.created_at.desc()).all()
    favorites_count = Favorite.query.filter_by(user_id=id).count()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'name': user.name or user.username,
        'role': user.role,
        'bio': user.bio,
        'avatar_url': user.avatar_url,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'recommendations_count': len(recommendations),
        'reviews_count': len(reviews),
        'favorites_count': favorites_count,
        'recommendations': [
            {
                'id': r.id,
                'name': r.title,
                'title': r.title,
                'category': r.category,
                'location': r.location,
                'image_url': r.image_url,
                'avg_rating': r.avg_rating,
            }
            for r in recommendations
        ],
        'reviews': [
            {
                'id': rev.id,
                'rating': rev.rating,
                'comment': rev.comment,
                'recommendation_title': rev.recommendation.title if rev.recommendation else 'Unknown',
                'recommendation_id': rev.recommendation_id,
                'created_at': rev.created_at.isoformat() if rev.created_at else None,
            }
            for rev in reviews
        ]
    })

@app.route('/api/users/me', methods=['GET'])
@jwt_required()
def api_get_my_profile():
    """Get current user's own profile"""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    recommendations_count = Recommendation.query.filter_by(user_id=user.id).count()
    reviews_count = Review.query.filter_by(user_id=user.id).count()
    favorites_count = Favorite.query.filter_by(user_id=user.id).count()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'name': user.name or user.username,
        'role': user.role,
        'bio': user.bio,
        'avatar_url': user.avatar_url,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'recommendations_count': recommendations_count,
        'reviews_count': reviews_count,
        'favorites_count': favorites_count,
    })

@app.route('/api/users/me', methods=['PUT'])
@jwt_required()
def api_update_my_profile():
    """Update current user's profile (bio, avatar) - supports both JSON and FormData"""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)

    # FIXED: Handle both JSON and multipart form data (for avatar upload)
    if request.content_type and 'multipart/form-data' in request.content_type:
        # FormData upload
        bio = request.form.get('bio', '')
        if bio:
            user.bio = bio[:500] if bio else None

        avatar_file = request.files.get('avatar')
        if avatar_file and allowed_file(avatar_file.filename):
            file_data = avatar_file.read()
            base64_string = base64.b64encode(file_data).decode('utf-8')
            ext = avatar_file.filename.rsplit('.', 1)[1].lower()
            mime_types = {
                'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'gif': 'image/gif', 'webp': 'image/webp'
            }
            mime = mime_types.get(ext, 'image/jpeg')
            user.avatar_url = f"data:{mime};base64,{base64_string}"
    else:
        # JSON upload
        data = request.get_json() or {}
        if 'bio' in data:
            user.bio = data['bio'][:500] if data['bio'] else None
        if 'avatar_url' in data:
            user.avatar_url = data['avatar_url'] if data['avatar_url'] else None

    db.session.commit()
    return jsonify({
        'message': 'Profile updated',
        'bio': user.bio,
        'avatar_url': user.avatar_url,
        'name': user.name or user.username,
    })

# =========================================
# NOTIFICATION API ROUTES
# =========================================

@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def api_get_notifications():
    """Get current user's notifications"""
    user_id = int(get_jwt_identity())
    notifs = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    return jsonify([
        {
            'id': n.id,
            'message': n.message,
            'type': n.type,
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat() if n.created_at else None,
            'recommendation_id': n.link.split('/')[-1] if n.link and '/store/' in n.link else None,
            'recommendation_name': None,  # Can be enriched if needed
        }
        for n in notifs
    ])

@app.route('/api/notifications/unread-count', methods=['GET'])
@jwt_required()
def api_get_unread_count():
    """Get count of unread notifications"""
    user_id = int(get_jwt_identity())
    count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/notifications/<int:id>/read', methods=['POST'])
@jwt_required()
def api_mark_notification_read(id):
    """Mark a notification as read"""
    user_id = int(get_jwt_identity())
    notif = Notification.query.get_or_404(id)

    if notif.user_id != user_id:
        return jsonify({'error': 'Not authorized'}), 403

    notif.is_read = True
    db.session.commit()
    return jsonify({'message': 'Marked as read'})

@app.route('/api/notifications/read-all', methods=['POST'])
@jwt_required()
def api_mark_all_read():
    """Mark all notifications as read"""
    user_id = int(get_jwt_identity())
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'message': 'All marked as read'})



# =========================================
# JINJA2 ADMIN FORM ROUTES (for admin.html)
# =========================================

@app.route('/admin/dismiss-report/<int:report_id>', methods=['POST'])
@login_required
@admin_required
def admin_dismiss_report(report_id):
    report = Report.query.get_or_404(report_id)
    report.status = 'dismissed'
    db.session.commit()

    if report.reporter_id:
        create_notification(
            report.reporter_id,
            f"Your report on '{report.reported_rec.title if report.reported_rec else 'a store'}' was dismissed.",
            type='report',
            link=f"/store/{report.store_id}"
        )

    flash('Report dismissed.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete-rec/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_rec(id):
    rec = Recommendation.query.get_or_404(id)
    title = rec.title
    db.session.delete(rec)
    db.session.commit()
    flash(f'Store "{title}" deleted.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/promote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_promote(user_id):
    user = User.query.get_or_404(user_id)
    user.role = 'admin'
    db.session.commit()

    create_notification(
        user.id,
        "You have been promoted to Admin!",
        type='admin'
    )

    flash(f'User {user.username} promoted to admin.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/demote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_demote(user_id):
    user = User.query.get_or_404(user_id)
    user.role = 'user'
    db.session.commit()
    flash(f'User {user.username} demoted to user.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot delete yourself!', 'error')
        return redirect(url_for('admin'))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'User {username} deleted.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete-subcat/<int:subcat_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_subcat(subcat_id):
    sub = SubCategory.query.get_or_404(subcat_id)
    name = sub.name
    db.session.delete(sub)
    db.session.commit()
    flash(f'Sub-category "{name}" deleted.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/add-subcat', methods=['POST'])
@login_required
@admin_required
def admin_add_subcat():
    icon = request.form.get('icon', '📌')
    name = request.form.get('name')

    if not name:
        flash('Name is required.', 'error')
        return redirect(url_for('admin'))

    sub = SubCategory(name=name, icon=icon, category='other')
    db.session.add(sub)
    db.session.commit()
    flash(f'Sub-category "{name}" added.', 'success')
    return redirect(url_for('admin'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_rec(id):
    rec = Recommendation.query.get_or_404(id)

    # Check authorization
    if rec.user_id != current_user.id and current_user.role != 'admin':
        flash('Not authorized.', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        rec.title = request.form.get('name', rec.title)
        rec.location = request.form.get('location', rec.location)
        rec.category = request.form.get('category', rec.category)
        rec.description = request.form.get('description', rec.description)
        rec.hours = request.form.get('hours', rec.hours)
        rec.reason = request.form.get('reason', rec.reason)
        rec.contact = request.form.get('contact', rec.contact)

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
        flash('Recommendation updated.', 'success')
        return redirect(url_for('admin'))

    # Redirect to Vue app with store ID in query param so Vue can open the edit modal
    return redirect(url_for('home') + f'?edit={id}')

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
