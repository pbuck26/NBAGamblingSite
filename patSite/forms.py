from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, email_validator

class SignupForm(FlaskForm):
    name = StringField(
        label=('Name'),
        validators=[DataRequired()]
    )
    email = StringField(
        label=('Email'),
        validators=[
            Length(min=6),
            DataRequired()
        ]
    )
    password = PasswordField(
        label=('Password'),
        validators=[
            DataRequired(),
            Length(min=6, message='Select a stronger password.')
        ]
    )
    confirm = PasswordField(
        label=('Confirm Your Password'),
        validators=[
            DataRequired(),
            EqualTo('password', message='Passwords must match.')
        ]
    )
    submit = SubmitField(label=('Register'))


class LoginForm(FlaskForm):
    email = StringField(
        label=('Email'),
        validators=[
            DataRequired()
        ]
    )
    password = PasswordField(label=('Password'), validators=[DataRequired()])
    submit = SubmitField(label=('Log In'))