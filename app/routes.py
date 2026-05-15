from flask import render_template, request, jsonify, redirect, url_for
from app import app, db
from app.models import Place, Recommendation
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


@app.route('/admin')
def admin():
    return render_template('admin.html')

# =========================================
# API ROUTES
# =========================================


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
    if form.validate_on_submit():
        # Handle image upload
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
        
        # Create Recommendation (not Place!)
        rec = Recommendation(
            title=form.name.data,  # form has 'name', model has 'title'
            reason=form.reason.data,
            location=form.location.data,
            category=form.category.data,
            description=form.description.data,
            hours=form.hours.data,
            contact=form.contact.data,
            image_url=image_url,
            avg_rating=5,
            user_id=current_user.id if current_user.is_authenticated else 1  # fallback to admin
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
