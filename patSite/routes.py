from flask import current_app as app
from flask import request, render_template, Blueprint, redirect, url_for
from flask.helpers import flash
from patSite.Models import Users, Picks, ContactMessages, db
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

@routes_blueprint("/contact", methods=['GET', 'POST'])
@login_required
def contactPage():
    app.logger.info("Rendering contact page...")
    form = ContactForm()
    if form.validate_on_submit():
        contact_message = ContactMessages(form.subject.data, form.message.data, current_user.id)
        db.session.add(contact_message)
        db.session.commit()
        flash("Message succesfully delivered")
        return redirect(url_for('routes_blueprint.renderHomepage'))

    return render_template('contact.jinja2', 
    title='Contact Page',
    form=form,
    template='contact-page',
    body ="Contact Me!")

