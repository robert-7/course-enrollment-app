from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms import PasswordField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import DataRequired
from wtforms.validators import Email
from wtforms.validators import EqualTo
from wtforms.validators import Length
from wtforms.validators import ValidationError

from application.models import User


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=6, max=15)]
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Login")


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=6, max=15)]
    )
    password_confirm = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), Length(min=6, max=15), EqualTo("password")],
    )
    first_name = StringField(
        "First Name", validators=[DataRequired(), Length(min=2, max=55)]
    )
    last_name = StringField(
        "Last Name", validators=[DataRequired(), Length(min=2, max=55)]
    )
    submit = SubmitField("Register Now")

    def validate_email(self, email):
        # this throws an error for some reason
        user = User.objects(email=email.data)
        user = user.first()
        if user:
            raise ValidationError("Email is already in user. Pick another one.")
