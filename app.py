from flask import Flask, request, render_template, jsonify
from service import NewUserService
from model import Schema, UserModel
import json

app = Flask(__name__)

@app.after_request
def add_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] =  "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With"
    response.headers['Access-Control-Allow-Methods']=  "POST, GET, PUT, DELETE, OPTIONS"
    return response

#define route
@app.route("/")
def hello():
    return render_template('index.html', name = 'Pat')

@app.route("/newuser", methods=["POST"])
def new_user():
    try:
        return NewUserService().createNewUser(request.get_json())
    except:
        print(NewUserService().createNewUser(request.get_json()))
if __name__ == "__main__":
    Schema()
    app.run(debug = True)
