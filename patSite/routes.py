from flask import current_app as app
from flask import render_template, Blueprint, redirect, url_for, flash
from patSite.Models import Game, Prediction, ModelRun, ContactMessages, db
from flask_login import current_user, logout_user, login_required
from sqlalchemy import func
from patSite.clock import to_et, today_et
from patSite.forms import ContactForm
from patSite.stats import FEATURE_LABELS, track_record


routes_blueprint = Blueprint('routes_blueprint', __name__,
template_folder='templates',
static_folder ='static')

@routes_blueprint.app_template_filter('american')
def american_odds(odds):
    if odds is None:
        return '–'
    return f'+{odds}' if odds > 0 else str(odds)

@routes_blueprint.app_template_filter('pct')
def percent(value, digits=0):
    return '–' if value is None else f'{value * 100:.{digits}f}%'

@routes_blueprint.app_template_filter('units')
def units(value):
    return '–' if value is None else f'{value:+.2f}u'

@routes_blueprint.app_template_filter('et_time')
def et_time(naive_utc):
    t = to_et(naive_utc)
    return f"{t.hour % 12 or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"

@routes_blueprint.app_template_filter('et_stamp')
def et_stamp(naive_utc):
    t = to_et(naive_utc)
    return f'{t:%b} {t.day}, {t.year} at {et_time(naive_utc)} ET'

@routes_blueprint.app_template_filter('long_date')
def long_date(day):
    return f'{day:%A}, {day:%B} {day.day}, {day.year}'

@routes_blueprint.route("/")
def renderHomepage():
    app.logger.info("Rendering homepage...")
    today = today_et()
    # Today's slate, or the next day with picks if there are no games today.
    slate_date = (db.session.query(func.min(Game.game_date)).join(Prediction)
                  .filter(Game.game_date >= today).scalar())
    games = []
    if slate_date:
        games = (Game.query.join(Prediction).filter(Game.game_date == slate_date)
                 .order_by(Game.start_time).all())
    return render_template('games.jinja2', games=games, slate_date=slate_date, today=today)

@routes_blueprint.route("/performance")
def performance():
    graded = (Prediction.query.join(Game).filter(Prediction.graded.is_(True))
              .order_by(Game.start_time.desc()).all())
    run = ModelRun.query.order_by(ModelRun.created_at.desc()).first()
    return render_template('performance.jinja2',
    title='Model performance',
    record=track_record(graded),
    recent=graded[:50],
    run=run,
    feature_labels=FEATURE_LABELS)

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
