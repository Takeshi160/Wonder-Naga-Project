from flask import render_template, request, jsonify, redirect, url_for
from app import app, db
from app.models import Place, Recommendation, User, Report, SubCategory
from app.forms import RecommendationForm
from werkzeug.utils import secure_filename
from flask_login import login_required, login_user, logout_user, current_user
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
# MAIN PAGES
# =========================================

@app.route('/')
def home():
    # Get featured place (first one, or random)
    featured = Place.query.first()
    
    # Get top stores (all places for now, you can limit/sort later)
    top_stores = Place.query.all()
    
    # Get user recommendations
    recommendations = Recommendation.query.all()
    
    return render_template('index.html', 
                         featured=featured, 
                         top_stores=top_stores, 
                         recommendations=recommendations)


# =========================================
# API ROUTES
# =========================================


from app.forms import LoginForm, RegistrationForm

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not check_password_hash(user.password, form.password.data):
            return render_template('auth.html', mode='login', form=form, error='Invalid username or password')
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('home'))
    
    return render_template('auth.html', mode='login', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    
    return render_template('auth.html', mode='register', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

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

@app.route('/store/<int:id>')
def store_detail(id):
    place = Place.query.get_or_404(id)
    return render_template('store_detail.html', place=place)


# =========================================
# ADD RECOMMENDATION
# =========================================
@app.route('/add', methods=['GET', 'POST'])
def add():
    form = RecommendationForm()
    
    # Populate sub-category choices based on main category
    form.sub_category.choices = [(str(s.id), f"{s.icon} {s.name}") for s in SubCategory.query.all()]
    
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
            sub_category_id=int(form.sub_category.data) if form.sub_category.data else None,
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

@app.route('/api/recommendations', methods=['POST'])
def add_recommendation():
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
        user_id=current_user.id if current_user.is_authenticated else 1
    )

    db.session.add(rec)
    db.session.commit()

    return jsonify({'message': 'Recommendation added successfully'})


# =========================================
# DELETE PLACE
# =========================================

@app.route('/api/delete/<int:id>', methods=['DELETE'])
def delete_place(id):

    place = Place.query.get_or_404(id)

    db.session.delete(place)
    db.session.commit()

    return jsonify({'message': 'Place deleted'})

@app.route('/delete_rec/<int:id>', methods=['POST'])
@login_required
def delete_rec(id):
    rec = Recommendation.query.get_or_404(id)
    
    # Only allow owner or admin to delete
    if rec.user_id != current_user.id and current_user.role != 'admin':
        return redirect(url_for('home'))
    
    db.session.delete(rec)
    db.session.commit()
    
    return redirect(url_for('home'))

# =========================================
# FEATURED PLACE
# =========================================

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


# =========================================
# FILTER
# =========================================

@app.route('/api/filter')
def filter_places():

    query = Place.query

    category = request.args.get('category')
    location = request.args.get('location')
    sort = request.args.get('sort')

    if category:
        query = query.filter_by(category=category)

    if location:
        query = query.filter(
            Place.location.ilike(f"%{location}%")
        )

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
    
    # Search in title, description, location, and reason
    from sqlalchemy import or_
    
    query = Recommendation.query.filter(
        or_(
            Recommendation.title.ilike(f'%{q}%'),
            Recommendation.description.ilike(f'%{q}%'),
            Recommendation.location.ilike(f'%{q}%'),
            Recommendation.reason.ilike(f'%{q}%')
        )
    )
    
    # If category filter is applied (from category pages)
    if category:
        query = query.filter_by(category=category)
    
    items = query.all()
    
    return render_template('search.html', 
                         items=items, 
                         q=q, 
                         category=category,
                         category_name=category.capitalize() if category else 'All')

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    users = User.query.all()
    all_stores = Recommendation.query.all()
    total_users = User.query.count()
    total_stores = Recommendation.query.count()
    pending_reports = Report.query.all()
    dynamic_subcats = SubCategory.query.all()
    
    return render_template('admin.html', 
                         users=users, 
                         all_stores=all_stores,
                         total_users=total_users,
                         total_stores=total_stores,
                         pending_reports=pending_reports,
                         dynamic_subcats=dynamic_subcats)

@app.route('/admin/promote/<int:user_id>', methods=['POST'])
@login_required
def admin_promote(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    user.role = 'admin'
    db.session.commit()
    
    return redirect(url_for('admin'))


@app.route('/admin/demote/<int:user_id>', methods=['POST'])
@login_required
def admin_demote(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    user.role = 'user'
    db.session.commit()
    
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    # Don't let admin delete themselves
    if user_id == current_user.id:
        return redirect(url_for('admin'))
    
    user = User.query.get_or_404(user_id)
    
    # Delete all their recommendations first (or reassign them)
    Recommendation.query.filter_by(user_id=user.id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    return redirect(url_for('admin'))

@app.route('/edit_rec/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_rec(id):
    rec = Recommendation.query.get_or_404(id)
    
    # Only owner or admin can edit
    if rec.user_id != current_user.id and current_user.role != 'admin':
        return redirect(url_for('home'))
    
    form = RecommendationForm()
    
    if form.validate_on_submit():
        # Handle new image upload (optional)
        image_url = rec.image_url  # keep existing by default
        files = request.files.getlist('images')
        
        if files and files[0]:
            file = files[0]
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4()}_{filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(save_path)
                image_url = f"/static/uploads/{unique_name}"
        
        # Update fields
        rec.title = form.name.data
        rec.reason = form.reason.data
        rec.location = form.location.data
        rec.category = form.category.data
        rec.description = form.description.data
        rec.hours = form.hours.data
        rec.contact = form.contact.data
        rec.image_url = image_url
        
        db.session.commit()
        return redirect(url_for('home'))
    
    # Pre-fill form with existing data
    if request.method == 'GET':
        form.name.data = rec.title
        form.reason.data = rec.reason
        form.location.data = rec.location
        form.category.data = rec.category
        form.description.data = rec.description
        form.hours.data = rec.hours
        form.contact.data = rec.contact
    
    return render_template('edit_rec.html', form=form, rec=rec)

@app.route('/admin/delete_rec/<int:id>', methods=['POST'])
@login_required
def admin_delete_rec(id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    rec = Recommendation.query.get_or_404(id)
    db.session.delete(rec)
    db.session.commit()
    
    return redirect(url_for('admin'))

@app.route('/report/<int:store_id>', methods=['POST'])
@login_required
def report_store(store_id):
    reason = request.form.get('reason', 'No reason provided')
    
    report = Report(
        reporter_id=current_user.id,
        store_id=store_id,
        reason=reason
    )
    
    db.session.add(report)
    db.session.commit()
    
    return redirect(url_for('home'))


@app.route('/admin/dismiss_report/<int:report_id>', methods=['POST'])
@login_required
def admin_dismiss_report(report_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    
    return redirect(url_for('admin'))

@app.route('/admin/add_subcat', methods=['POST'])
@login_required
def admin_add_subcat():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    name = request.form.get('name')
    icon = request.form.get('icon', '📂')
    
    subcat = SubCategory(name=name, icon=icon)
    db.session.add(subcat)
    db.session.commit()
    
    return redirect(url_for('admin'))


@app.route('/admin/delete_subcat/<int:subcat_id>', methods=['POST'])
@login_required
def admin_delete_subcat(subcat_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    subcat = SubCategory.query.get_or_404(subcat_id)
    db.session.delete(subcat)
    db.session.commit()
    
    return redirect(url_for('admin'))