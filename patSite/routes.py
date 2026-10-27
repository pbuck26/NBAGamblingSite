from flask import current_app as app
from flask import render_template, Blueprint, redirect, url_for, flash
from patSite.Models import Picks, ContactMessages, db
from flask_login import current_user, logout_user, login_required
import datetime
from sqlalchemy import cast, Date
from patSite.forms import ContactForm


routes_blueprint = Blueprint('routes_blueprint', __name__,
template_folder='templates',
static_folder ='static')

@routes_blueprint.route("/")
def renderHomepage():
    app.logger.info("Rendering homepage...")
    games = Picks.query.filter(cast(Picks.date, Date)==datetime.date.today()).all()
    return render_template('games.jinja2', games = games)

@routes_blueprint.route("/contact", methods=['GET', 'POST'])
@login_required
def contactPage():
    app.logger.info("Rendering contact page...")
    form = ContactForm()
    if form.validate_on_submit():
        contact_message = ContactMessages(form.subject.data, form.message.data, current_user.id)
        db.session.add(contact_message)
        db.session.commit()
        flash("Message successfully delivered")
        return redirect(url_for('routes_blueprint.renderHomepage'))

    return render_template('contact.jinja2',
    title='Contact',
    form=form)

@routes_blueprint.route("/logout")
@login_required
def logout():
    name = current_user.name
    logout_user()
    flash(f"Goodbye, {name}!")
    return redirect(url_for('routes_blueprint.renderHomepage'))
