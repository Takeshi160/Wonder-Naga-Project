from flask import render_template, request, jsonify
from app import app, db
from app.models import Place
from werkzeug.utils import secure_filename
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

# Create upload folder if missing
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

    return render_template('index.html')


@app.route('/admin')
def admin():

    return render_template('admin.html')

# =========================================
# API ROUTES
# =========================================

@app.route('/api/stores', methods=['GET'])
def get_stores():

    places = Place.query.all()

    data = []

    for p in places:

        data.append({
            'id': p.id,
            'name': p.name,
            'location': p.location,
            'category': p.category,
            'description': p.description,
            'hours': p.hours,
            'image_url': p.image_url,
            'avg_rating': p.avg_rating
        })

    return jsonify(data)

# =========================================
# ADD RECOMMENDATION
# =========================================

@app.route('/api/recommendations', methods=['POST'])
def add_recommendation():

    name = request.form.get('name')
    location = request.form.get('location')
    category = request.form.get('category')
    description = request.form.get('description')
    hours = request.form.get('hours')

    image_url = None

    files = request.files.getlist('images')

    # Upload FIRST image
    if files and files[0]:

        file = files[0]

        if file and allowed_file(file.filename):

            filename = secure_filename(file.filename)

            unique_name = f"{uuid.uuid4()}_{filename}"

            save_path = os.path.join(
                app.config['UPLOAD_FOLDER'],
                unique_name
            )

            file.save(save_path)

            image_url = f"/static/uploads/{unique_name}"

    place = Place(
        name=name,
        location=location,
        category=category,
        description=description,
        hours=hours,
        image_url=image_url,
        avg_rating=5
    )

    db.session.add(place)
    db.session.commit()

    return jsonify({
        'message': 'Recommendation added successfully'
    })

# =========================================
# DELETE PLACE (ADMIN)
# =========================================

@app.route('/api/delete/<int:id>', methods=['DELETE'])
def delete_place(id):

    place = Place.query.get_or_404(id)

    db.session.delete(place)
    db.session.commit()

    return jsonify({
        'message': 'Place deleted'
    })

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
# SEARCH FILTERS
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

    places = query.all()

    results = []

    for p in places:

        results.append({
            'id': p.id,
            'name': p.name,
            'location': p.location,
            'category': p.category,
            'description': p.description,
            'hours': p.hours,
            'image_url': p.image_url,
            'avg_rating': p.avg_rating
        })

    return jsonify(results)
