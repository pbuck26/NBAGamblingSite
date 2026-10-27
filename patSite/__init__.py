import secrets
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db=SQLAlchemy()
login_manager = LoginManager()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.logger.warning("SECRET_KEY is not set; using a random key, so logins reset on every restart")
        app.config["SECRET_KEY"] = secrets.token_hex(32)

    app.logger.info("Creating application")
    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from patSite.routes import routes_blueprint
        app.register_blueprint(routes_blueprint)
        from patSite import Models
        from patSite.auth import auth_bp
        from patSite.commands import commands_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(commands_bp)
        Models.db.create_all()

    return app
