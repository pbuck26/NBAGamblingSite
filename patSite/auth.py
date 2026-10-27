from datetime import datetime as dt
from urllib.parse import urlsplit
from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_login import current_user, login_user
from sqlalchemy import func
from patSite.forms import SignupForm, LoginForm
from patSite.Models import Users, db
from . import login_manager
from flask import current_app as app

auth_bp = Blueprint('auth_bp', __name__,
template_folder='templates',
static_folder ='static')

def is_safe_redirect(target):
    """Only allow redirects to a path on this site, never to another host."""
    if not target or not target.startswith('/') or target.startswith('//') or '\\' in target:
        return False
    parts = urlsplit(target)
    return not parts.scheme and not parts.netloc

def find_user_by_email(email):
    return Users.query.filter(func.lower(Users.email) == email.strip().lower()).first()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    app.logger.info("Rendering login page")
    if current_user.is_authenticated:
        return redirect(url_for('routes_blueprint.renderHomepage'))
    form = LoginForm()
    next_page = request.args.get('next')
    if form.validate_on_submit():
        app.logger.info("Valid Form response")
        user = find_user_by_email(form.email.data)
        if user and user.check_password(password=form.password.data):
            user.last_login = dt.now()
            db.session.commit()  # also saves the upgraded hash if check_password rehashed it
            login_user(user)
            flash('Successfully logged in!')
            if not is_safe_redirect(next_page):
                next_page = url_for('routes_blueprint.renderHomepage')
            return redirect(next_page)
        flash('Invalid email/password combination')
        return redirect(url_for('auth_bp.login', next=next_page))
    return render_template('login.jinja2',
    title='Log In',
    form=form,
    next_page=next_page)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    app.logger.info("Rendering signup page")
    form = SignupForm()
    if form.validate_on_submit():
        if find_user_by_email(form.email.data) is None:
            new_user = Users(form.email.data.strip().lower(), form.password.data, form.name.data)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash(f"Welcome, {new_user.name}!")
            return redirect(url_for('routes_blueprint.renderHomepage'))
        flash('An account already exists with that email address')
    return render_template('signup.jinja2',
    title='Create an account',
    form=form)


@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in on every page load."""
    if user_id is not None:
        return db.session.get(Users, int(user_id))
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash('You must be logged in to view that page.')
    return redirect(url_for('auth_bp.login', next=request.path))
