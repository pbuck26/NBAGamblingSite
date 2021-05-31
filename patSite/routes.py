from flask import current_app as app
from flask import request, render_template, jsonify, Response, Blueprint, g
from patSite.Models import Users, Picks, db
from flask_login import current_user, logout_user, login_required
import datetime
from datetime import timedelta
from sqlalchemy import cast, Date


routes_blueprint = Blueprint('routes_blueprint', __name__)

@routes_blueprint.route("/")
def renderHomepage():
    app.logger.info("Rendering homepage...")
    games = Picks.query.filter(cast(Picks.date, Date)==datetime.date.today()).all()
    return render_template('games.jinja2', games = games)
