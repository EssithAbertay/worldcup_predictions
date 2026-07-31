from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeLocalField, FieldList, FormField, RadioField, IntegerField, Form, SelectField, ColorField
from wtforms.validators import ValidationError, DataRequired, EqualTo, NumberRange, Optional, InputRequired, Length
import sqlalchemy as sa
from app import db
from app.models import User
from flask_wtf.file import FileField, FileAllowed
import os
#from wtforms.validators import Email

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    #email = StringField('Email', validators=[DataRequired(), Email()])
    display_name = StringField('Display Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(max=32)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match'), Length(max=32)])
    pin = StringField('Pin', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(User.username == username.data))
        if user is not None:
            raise ValidationError('Already in use! Please use a different username.')
        
    def validate_pin(self, pin):
        valid = os.environ.get('PIN') == pin.data
        if not valid:
            raise ValidationError('Incorrect Pin')
    

    #def validate_email(self, email):
    #   user = db.session.scalar(sa.select(User).where(User.email == email.data))
    #    if user is not None:
    #        raise ValidationError('Already in use! Please use a different email.')
        
class EditUsernameForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    submitUsername = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == username.data))
            if user is not None:
                raise ValidationError('Already in use! Please use a different username.')

class EditDisplayNameForm(FlaskForm):
    displayName = StringField('Display Name', validators=[DataRequired()])
    submitDisplayName = SubmitField('Submit')

    def __init__(self, original_displayName, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_displayName = original_displayName

class EditUserColourForm(FlaskForm):
    userColour = ColorField('Colour', validators=[DataRequired()])
    submitUserColour = SubmitField('Submit')

    def __init__(self, original_userColour, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_displayName = original_userColour

class EditPicForm(FlaskForm):
    profile = FileField('Select Profile Picture', validators=[FileAllowed(['jpg', 'jpeg', 'png'])])
    submitProfilePic = SubmitField('Submit')
     
class SinglePredictionForm(Form):
    game_id = IntegerField(validators=[DataRequired()])
    home_score = IntegerField('Home Score', validators=[Optional(), NumberRange(min=0, max=99)])
    away_score = IntegerField('Away Score', validators=[Optional(), NumberRange(min=0, max=99)])

class PredictionForm(FlaskForm):
    predictions = FieldList(FormField(SinglePredictionForm), min_entries=0)
    submit = SubmitField('Save Predictions')

class AdminTeamSubmission(FlaskForm):
    team = StringField('Team', validators=[DataRequired()])
    short_name = StringField('Short Name', validators=[DataRequired()])
    submit = SubmitField('Add Team')

class AdminGameSubmission(FlaskForm):
    home_team = SelectField('Home Team', validators=[DataRequired()], coerce=int)
    away_team = SelectField('Away Team', validators=[DataRequired()], coerce=int)

    matchday  = IntegerField('Matchday', validators=[DataRequired()])
    kickoff = DateTimeLocalField('Kickoff DateTime',  format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    submit_game = SubmitField('Add Game')

class AdminSingleResult(Form):
    game_id = IntegerField(validators=[DataRequired()])
    home_score = IntegerField('Home Team', validators=[Optional(), NumberRange(min=0, max=99)])
    away_score = IntegerField('Away Team', validators=[Optional(), NumberRange(min=0, max=99)])

class AdminEditGameForm(FlaskForm):
    game_id = SelectField("Game",coerce=int)
    home_score = IntegerField('New Home Score', validators=[Optional(), NumberRange(min=0, max=99)])
    away_score = IntegerField('New Away Score', validators=[Optional(), NumberRange(min=0, max=99)])
    kickoff = DateTimeLocalField('New Kickoff DateTime',  format='%Y-%m-%dT%H:%M', validators=[Optional()])
    status = SelectField('New Status', choices=[("none","None"),("scheduled","Scheduled"),("postponed","Postponed"),("completed","Completed")], validators=[Optional()])
    submitGameEdit = SubmitField('Edit Game')

class AdminResultForm(FlaskForm):
    results = FieldList(FormField(AdminSingleResult), min_entries=0)
    submit_results = SubmitField('Submit Results')

class AdminRecalculatePoints(FlaskForm):
    recalculate_points = SubmitField('Recalculate Points')
    





    
