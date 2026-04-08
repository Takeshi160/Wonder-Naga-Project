from flask import render_template, flash, redirect, url_for, session, request
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, EmptyForm, PostForm, RecommendationForm
from werkzeug.security import check_password_hash
from app.models import User, Post, Recommendation
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from urllib.parse import urlsplit


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            return render_template('auth.html',title='Sign In',form=form,mode='login',error='Invalid username or password')
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('auth.html', title='Sign In', form=form, mode='login', error=None)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)

        

@app.route('/', methods=['GET','POST'])
@app.route('/index', methods=['GET','POST'])
@login_required
def index():
    form = PostForm()

    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    posts = db.paginate(
        current_user.following_posts(),
        page=page,
        per_page=app.config['POSTS_PER_PAGE'],
        error_out=False
    )

    recommendations = Recommendation.query.order_by(Recommendation.id.desc()).all()

    return render_template(
        'index.html',
        title='Home',
        form=form,
        posts=posts.items,
        recommendations=recommendations
    )

@app.route('/edit_rec/<int:id>', methods=['GET','POST'])
@login_required
def edit_rec(id):
    rec = db.get_or_404(Recommendation, id)

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
        flash("Recommendation updated!")
        return redirect(url_for('index'))

    elif request.method == 'GET':
        form.title.data = rec.title
        form.category.data = rec.category
        form.description.data = rec.description
        form.location.data = rec.location
        form.reason.data = rec.reason
        form.hours.data = rec.hours
        form.contact.data = rec.contact

    return render_template('add.html', form=form)

@app.route('/delete_rec/<int:id>', methods=['POST'])
@login_required
def delete_rec(id):
    rec = db.get_or_404(Recommendation, id)

    db.session.delete(rec)
    db.session.commit()

    flash("Recommendation deleted.")
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('auth.html', title='Register', form=form, mode='register', error=None)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f'You are following {username}!')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f'You are not following {username}.')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))
    
@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    form = PostForm()
    return render_template("index.html", title='Explore',
                       posts=posts.items,
                       next_url=next_url,
                       prev_url=prev_url,
                       form=form)

@app.route('/edit_post/<int:id>', methods=['GET','POST'])
@login_required
def edit_post(id):
    post = db.get_or_404(Post, id)

    if post.author != current_user:
        flash("You cannot edit this post.")
        return redirect(url_for('index'))

    form = PostForm()

    if form.validate_on_submit():
        post.body = form.post.data
        db.session.commit()
        flash("Post updated!")
        return redirect(url_for('index'))

    elif request.method == 'GET':
        form.post.data = post.body

    return render_template('edit_post.html', title='Edit Post', form=form)

@app.route('/delete_post/<int:id>', methods=['POST'])
@login_required
def delete_post(id):
    post = db.get_or_404(Post, id)

    if post.author != current_user:
        flash("You cannot delete this post.")
        return redirect(url_for('index'))

    db.session.delete(post)
    db.session.commit()

    flash("Post deleted.")
    return redirect(url_for('index'))

@app.route('/post/<int:id>')
@login_required
def post_detail(id):
    post = db.get_or_404(Post, id)
    return render_template('store_detail.html', store=post)

@app.route('/restaurants')
def restaurants():
    return "Restaurants page coming soon"

@app.route('/cafes')
def cafes():
    return "Cafes page coming soon"

@app.route('/attractions')
def attractions():
    return "Attractions page coming soon"

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = RecommendationForm()

    # IMPORTANT: category choices must be set here
    form.category.choices = [
        ('restaurant', 'Restaurant'),
        ('cafe', 'Cafe'),
        ('store', 'Store'),
        ('attraction', 'Attraction')
    ]

    if form.validate_on_submit():
        print("VALID FORM")
        print(request.form)

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

        flash("Recommendation added successfully!", "success")
        return redirect(url_for('index'))
    else:
        print("INVALID FORM")
        print(form.errors)

    return render_template('add.html', form=form)

