from flask import current_app as app
from flask import request, render_template, jsonify, Response
from .Models import Users, db

@app.route("/")
def renderHomepage():
    app.logger.info('homepage')
    # have to add a "pick" variable
    # verify that the path to static png file works
    # arrange picks into one variable
    # move website html to index file
    return render_template('websitetake2.html', games = games, user_verified = False)

@app.route("/", methods=['POST', 'GET'])
def get_email():
    app.logger.info('Email request endpoint')
    if "email" in request.form:
        email = request.form['email']
        password = request.form['pwd']
        data = Users(email, password)
        db.session.add(data)
        db.session.commit()
        return render_template('websitetake2.html', games = games, user_verified = True)
    else:
        app.logger.error('poopoo')