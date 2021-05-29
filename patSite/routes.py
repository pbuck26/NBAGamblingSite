from flask import current_app as app
from flask import request, render_template, jsonify, Response, Blueprint, g
from patSite.Models import Users, db
from flask_login import current_user, logout_user, login_required

routes_blueprint = Blueprint('routes_blueprint', __name__)

@routes_blueprint.route("/")
def renderHomepage():
    app.logger.info('homepage')
    # have to add a "pick" variable
    # verify that the path to static png file works
    # arrange picks into one variable
    # move website html to index file
    return render_template('games.jinja2', games = g.games)
