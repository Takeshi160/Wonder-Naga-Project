import os
import uuid
import sqlalchemy as sa
from werkzeug.utils import secure_filename
from flask import (
render_template,
redirect,
url_for,
flash,
request,
jsonify
)
from flask_login import (
current_user,
login_user,
logout_user,
login_required
)
from app import app, db
from app.models import User, Recommendation
from app.forms import LoginForm, RegistrationForm
UPLOAD_FOLDER = 'app/static/uploads'
ALLOWED_EXTENSIONS = {
'png',
'jpg',
'jpeg',
'gif',
5
'webp'
}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# =====================================================
# HELPER FUNCTIONS
# =====================================================
def allowed_file(filename):
return '.' in filename and
filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# =====================================================
# HOME
# =====================================================
@app.route('/')
def home():
return render_template('index.html')
# =====================================================
# AUTH API
# =====================================================
@app.route('/api/auth/register', methods=['POST'])
def api_register():
data = request.get_json()
username = data.get('username')
password = data.get('password')
existing = db.session.scalar(
sa.select(User).where(User.username == username)
)
if existing:
return jsonify({'message': 'Username already exists'}), 400
user = User(
username=username,
6
email=f'{username}@thatsmynaga.com'
)
user.set_password(password)
db.session.add(user)
db.session.commit()
login_user(user)
return jsonify({
'message': 'Registered successfully',
'token': str(user.id)
})
@app.route('/api/auth/login', methods=['POST'])
def api_login():
data = request.get_json()
username = data.get('username')
password = data.get('password')
user = db.session.scalar(
sa.select(User).where(User.username == username)
)
if user is None or not user.check_password(password):
return jsonify({'message': 'Invalid username or password'}), 401
login_user(user)
return jsonify({
'message': 'Login successful',
'token': str(user.id)
})
@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
logout_user()
return jsonify({'message': 'Logged out'})
# =====================================================
# STORE APIs
7
# =====================================================
@app.route('/api/stores/top')
def api_top_stores():
stores = db.session.scalars(
sa.select(Recommendation)
.order_by(Recommendation.rating.desc())
.limit(8)
).all()
return jsonify([
store.to_dict() for store in stores
])
@app.route('/api/stores/featured')
def api_featured_store():
featured = db.session.scalar(
sa.select(Recommendation)
.order_by(Recommendation.rating.desc())
)
if not featured:
return jsonify(None)
return jsonify(featured.to_dict())
@app.route('/api/stores')
def api_stores():
category = request.args.get('category')
search = request.args.get('search', '')
sort = request.args.get('sort', 'newest')
subcategory = request.args.get('subcategory')
query = sa.select(Recommendation)
if category:
query = query.where(Recommendation.category == category)
if subcategory:
query = query.where(Recommendation.subcategory == subcategory)
if search:
8
query = query.where(
Recommendation.title.ilike(f'%{search}%')
)
if sort == 'a-z':
query = query.order_by(Recommendation.title.asc())
elif sort == 'z-a':
query = query.order_by(Recommendation.title.desc())
elif sort == 'rating':
query = query.order_by(Recommendation.rating.desc())
else:
query = query.order_by(Recommendation.id.desc())
stores = db.session.scalars(query).all()
return jsonify([
store.to_dict() for store in stores
])
@app.route('/api/stores/<int:id>')
def api_store_detail(id):
store = db.session.get(Recommendation, id)
if store is None:
return jsonify({'message': 'Store not found'}), 404
return jsonify(store.to_dict())
# =====================================================
# ADD RECOMMENDATION API
# =====================================================
@app.route('/api/recommendations', methods=['POST'])
def api_add_recommendation():
title = request.form.get('name')
reason = request.form.get('reason')
location = request.form.get('location')
category = request.form.get('category')
subcategory = request.form.get('subcategory')
description = request.form.get('description')
9
hours = request.form.get('hours')
contact = request.form.get('contact')
image_url = None
if 'images' in request.files:
file = request.files['images']
if file and allowed_file(file.filename):
filename = secure_filename(file.filename)
unique_name = f'{uuid.uuid4()}_{filename}'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
filepath = os.path.join(
app.config['UPLOAD_FOLDER'],
unique_name
)
file.save(filepath)
image_url = f'/static/uploads/{unique_name}'
recommendation = Recommendation(
title=title,
reason=reason,
location=location,
category=category,
subcategory=subcategory,
description=description,
hours=hours,
contact=contact,
image_url=image_url,
rating=5.0
)
db.session.add(recommendation)
db.session.commit()
return jsonify({
'message': 'Recommendation added successfully'
})
# =====================================================
10
# ADMIN PAGE
# =====================================================
@app.route('/admin')
@login_required
def admin_panel():
if not current_user.is_admin:
flash('Admin access only')
return redirect(url_for('home'))
recommendations = db.session.scalars(
sa.select(Recommendation)
.order_by(Recommendation.id.desc())
).all()
users = db.session.scalars(
sa.select(User)
).all()
return render_template(
'admin.html',
recommendations=recommendations,
users=users
)
@app.route('/admin/delete/<int:id>')
@login_required
def admin_delete(id):
if not current_user.is_admin:
return redirect(url_for('home'))
recommendation = db.session.get(Recommendation, id)
if recommendation:
db.session.delete(recommendation)
db.session.commit()
flash('Recommendation deleted')
return redirect(url_for('admin_panel'))
