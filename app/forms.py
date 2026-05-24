from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateTimeLocalField, FieldList, FormField, RadioField, IntegerField, Form
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, NumberRange, Optional, InputRequired
import sqlalchemy as sa
from app import db
from app.models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(User.username == username.data))
        if user is not None:
            raise ValidationError('Already in use! Please use a different username.')
        
    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(User.email == email.data))
        if user is not None:
            raise ValidationError('Already in use! Please use a different email.')
        
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
                raise ValidationError('Please use a different username.')
      
class SinglePredictionForm(Form):
    penalties_required = False

    game_id = IntegerField(validators=[DataRequired()])
    home_score = IntegerField('Home Score', validators=[Optional(), NumberRange(min=0, max=99)])
    away_score = IntegerField('Away Score', validators=[Optional(), NumberRange(min=0, max=99)])
    penalty_winner = RadioField('Penalty Winner', choices=[('home','Home Team'),('away','Away Team')], default='home')

class PredictionForm(FlaskForm):
    predictions = FieldList(FormField(SinglePredictionForm), min_entries=0)
    submit = SubmitField('Submit Predictions')

class AdminGameSubmission(FlaskForm):
    home_team = StringField('Home Team', validators=[DataRequired()])
    away_team = StringField('Away Team', validators=[DataRequired()])
    kickoff = DateTimeLocalField('Kickoff DateTime',  format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    is_penalty_game = BooleanField('Can go to penalties?')
    submit_game = SubmitField('Add Game')

class AdminSingleResult(Form):

    game_id = IntegerField(validators=[DataRequired()])
    home_score = IntegerField('Home Team', validators=[InputRequired(), NumberRange(min=0, max=99)])
    away_score = IntegerField('Away Team', validators=[InputRequired(), NumberRange(min=0, max=99)])
    penalty_winner = RadioField('Penalty Winner', choices=[('home','Home Team'),('away','Away Team'),('na','N/A')], default='na')

class AdminResultForm(FlaskForm):
    results = FieldList(FormField(AdminSingleResult), min_entries=0)
    submit_results = SubmitField('Submit Results')

class AdminRecalculatePoints(FlaskForm):
    recalculate_points = SubmitField('Recalculate Points')
    





    
