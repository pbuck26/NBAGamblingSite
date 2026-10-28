from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class SignupForm(FlaskForm):
    name = StringField(
        label=('Name'),
        validators=[DataRequired(), Length(max=100)]
    )
    email = EmailField(
        label=('Email'),
        validators=[
            DataRequired(),
            Email(message='Enter a valid email address.'),
            Length(max=200)
        ]
    )
    password = PasswordField(
        label=('Password'),
        validators=[
            DataRequired(),
            Length(min=8, message='Use at least 8 characters.')
        ]
    )
    confirm = PasswordField(
        label=('Confirm your password'),
        validators=[
            DataRequired(),
            EqualTo('password', message='Passwords must match.')
        ]
    )
    submit = SubmitField(label=('Sign up'))


class LoginForm(FlaskForm):
    email = EmailField(
        label=('Email'),
        validators=[
            DataRequired()
        ]
    )
    password = PasswordField(label=('Password'), validators=[DataRequired()])
    submit = SubmitField(label=('Log in'))

class ContactForm(FlaskForm):
    subject = StringField("Subject",  validators=[DataRequired(), Length(max=200)])
    message = TextAreaField("Message",  validators=[DataRequired(), Length(max=5000)])
    submit = SubmitField("Send")
