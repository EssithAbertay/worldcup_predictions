from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5

class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    #email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    points: so.Mapped[int] = so.mapped_column(default=0)
    ranking: so.Mapped[int] = so.mapped_column(nullable=True)
    is_admin: so.Mapped[bool] = so.mapped_column(default=False)

    predictions: so.WriteOnlyMapped['Prediction'] = so.relationship(back_populates='author')

    def __repr__(self):
        return '<User {}>'.format(
            self.username
        )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)    
    
    def avatar(self, size):
        digest = md5(self.username.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
    
    def calculate_points(self):
        # for each prediction, check it against its game then assign points
        # for now its just working off of scores, will add penalties later
        # also have to make it skip games that have already been worked out
        self.points = 0
       # predictions = db.session.execute(self.predictions.select().where(Prediction.points_awarded == None)).scalars() # this ver should only get games that havent been set yet
        predictions = db.session.execute(self.predictions.select()).scalars() # gets all games

        for prediction in predictions:


            #first skip games that haven't happened yet
            if prediction.match.home_score is None or prediction.match.away_score is None:
                continue 

            # if this is a penalty game then do this 
            if prediction.match.penalty_game: # not finished
                if prediction.match.penalty_winner != 'na': # check that the game required penalties
                    if prediction.penalty_winner_predicted == prediction.match.penalty_winner:
                        prediction.points_awarded = 3
                        self.points += 3
                    else:
                        prediction.points_awarded = 0
                        self.points += 0
            else: # when it's not a penalty game
                prediction.points_awarded = 0

                # check if scores are correct
                home_correct = bool(prediction.home_score_predicted == prediction.match.home_score)
                away_correct = bool(prediction.away_score_predicted == prediction.match.away_score)
                
                actual_result = (
                    "draw" if prediction.match.home_score == prediction.match.away_score
                    else "home" if prediction.match.home_score > prediction.match.away_score
                    else "away"
                )

                predicted_result = (
                    "draw" if prediction.home_score_predicted == prediction.away_score_predicted
                    else "home" if prediction.home_score_predicted > prediction.away_score_predicted
                    else "away"
                )


                # check if user has correct score
                if(home_correct and away_correct): # correct score + results
                    prediction.points_awarded += 5
                    self.points += 5
                    continue # continue as max points is 5

                if(actual_result == predicted_result): # if predicted correct result
                    prediction.points_awarded += 2
                    self.points += 2
                
                if(home_correct or away_correct): # bonus point for a correct score
                        prediction.points_awarded += 1
                        self.points += 1

                # nothing correct at all
                prediction.points_awarded = 0
                self.points += 0

class Game(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    home_team: so.Mapped[str] = so.mapped_column(sa.String(64), index=True)
    away_team: so.Mapped[str] = so.mapped_column(sa.String(64), index=True)
    home_score: so.Mapped[Optional[int]] = so.mapped_column()
    away_score: so.Mapped[Optional[int]] = so.mapped_column()
    penalty_game: so.Mapped[bool] = so.mapped_column(default=False)
    penalty_winner: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64), default='none') # will be either home, away, or none
    kickoff: so.Mapped[datetime] = so.mapped_column(index=True)

    predictions: so.WriteOnlyMapped['Prediction'] = so.relationship(back_populates='match')

    def __repr__(self):
        return '<Game {} vs {} @ {} Penalties: {}>'.format(
            self.home_team,
            self.away_team,
            self.kickoff.isoformat(),
            self.penalty_game
    )

class Prediction(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    home_score_predicted: so.Mapped[int] = so.mapped_column()
    away_score_predicted: so.Mapped[int] = so.mapped_column()
    penalty_winner_predicted: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))
    points_awarded: so.Mapped[int] = so.mapped_column(default=0)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    game_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Game.id), index=True)

    author: so.Mapped[User] = so.relationship(back_populates='predictions')
    match: so.Mapped[Game] = so.relationship(back_populates='predictions')

    def __repr__(self):
        return '<Prediction user={} game={} {}-{}>'.format(
            self.user_id,
            self.game_id,
            self.home_score_predicted,
            self.away_score_predicted
    )

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))