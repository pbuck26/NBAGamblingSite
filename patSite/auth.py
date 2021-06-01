from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_login import current_user, login_user
from patSite.forms import SignupForm, LoginForm
from patSite.Models import Users, db
from . import login_manager
from flask import current_app as app

auth_bp = Blueprint('auth_bp', __name__,
template_folder='templates',
static_folder ='static')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    app.logger.info("Rendering login page")
    form = LoginForm()
    if current_user.is_authenticated:
        print("current_user.is_authenticated: {}".format(current_user.is_authenticated))
        return redirect(url_for('routes_blueprint.renderHomepage'))
    if form.validate_on_submit():
        app.logger.info("Valid Form response")
        user = Users.query.filter_by(email=form.email.data).first()
        if user and user.check_password(password=form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('Successfully Logged In!')
            return redirect(next_page or url_for('routes_blueprint.renderHomepage'))
        flash('Invalid username/password combination')
        return redirect(url_for('auth_bp.login'))
    return render_template('login.jinja2', 
    title='Log In',
    form=form,
    template='login-page',
    body ="Log in with your user account")

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    print("poopy")
    app.logger.info("Rendering signup page")
    form = SignupForm()
    if form.validate_on_submit():
        existing_user = Users.query.filter_by(email=form.email.data).first()
        if existing_user is None:
            new_user = Users(form.email.data,form.password.data, form.name.data)
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Successfully Logged In!')
            return redirect(url_for('routes_blueprint.renderHomepage'))
        flash('A user with already exists with that email address')
    return render_template('signup.jinja2', 
    title='Create an account.',
    form=form,
    template='signup-page',
    body ="Sign up for a user account")


@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in on every page load."""
    if user_id is not None:
        return Users.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash('You must be logged in to view that page.')
    return redirect(url_for('auth_bp.login'))