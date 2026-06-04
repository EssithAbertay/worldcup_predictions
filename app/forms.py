from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeLocalField, FieldList, FormField, RadioField, IntegerField, Form, SelectField
from wtforms.validators import ValidationError, DataRequired, EqualTo, NumberRange, Optional, InputRequired, Length
import sqlalchemy as sa
from app import db
from app.models import User
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
        
class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == username.data))
            if user is not None:
                raise ValidationError('Already in use! Please use a different username.')
      
class SinglePredictionForm(Form):
    penalties_required = False

    game_id = IntegerField(validators=[DataRequired()])
    home_score = IntegerField('Home Score', validators=[Optional(), NumberRange(min=0, max=99)])
    away_score = IntegerField('Away Score', validators=[Optional(), NumberRange(min=0, max=99)])
    penalty_winner = RadioField('Penalty Winner', choices=[('home','Home Team'),('away','Away Team')], default='home')

class PredictionForm(FlaskForm):
    predictions = FieldList(FormField(SinglePredictionForm), min_entries=0)
    submit = SubmitField('Submit Predictions')


class AdminTeamSubmission(FlaskForm):
    team = StringField('Team', validators=[DataRequired()])
    fifa_code = StringField('FIFA Code', validators=[DataRequired()])
    flag_code = StringField('Flag Code', validators=[DataRequired()])
    group = StringField('Group', validators=[DataRequired()])
    submit = SubmitField('Add Team')


class AdminGameSubmission(FlaskForm):
    home_team = SelectField('Home Team', validators=[DataRequired()], coerce=int)
    away_team = SelectField('Away Team', validators=[DataRequired()], coerce=int)

    kickoff = DateTimeLocalField('Kickoff DateTime',  format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    is_penalty_game = BooleanField('Can go to penalties?')
    submit_game = SubmitField('Add Game')

class AdminSingleResult(Form):

    game_id = IntegerField(validators=[DataRequired()])
    home_score = IntegerField('Home Team', validators=[Optional(), NumberRange(min=0, max=99)])
    away_score = IntegerField('Away Team', validators=[Optional(), NumberRange(min=0, max=99)])
    penalty_winner = RadioField('Penalty Winner', choices=[('home','Home Team'),('away','Away Team'),('na','N/A')], default='na')

class AdminResultForm(FlaskForm):
    results = FieldList(FormField(AdminSingleResult), min_entries=0)
    submit_results = SubmitField('Submit Results')

class AdminRecalculatePoints(FlaskForm):
    recalculate_points = SubmitField('Recalculate Points')
    





    
