from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5
from flask import url_for
from sqlalchemy import func, JSON
from sqlalchemy.ext.mutable import MutableList

class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    #email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    points: so.Mapped[int] = so.mapped_column(default=0)
    ranking: so.Mapped[int] = so.mapped_column(nullable=True)
    previous_ranking: so.Mapped[int] = so.mapped_column(nullable=True, default=0)
    ranking_history: so.Mapped[list[dict]] = so.mapped_column(MutableList.as_mutable(JSON))
    points_history: so.Mapped[list[dict]] = so.mapped_column(MutableList.as_mutable(JSON))
    is_admin: so.Mapped[bool] = so.mapped_column(default=False)
    profile_pic_file: so.Mapped[str] = so.mapped_column(sa.String(64), default='none')

    number_of_scores: so.Mapped[int] = so.mapped_column(nullable=True, default=0)
    number_of_results: so.Mapped[int] = so.mapped_column(nullable=True, default=0)

    predictions: so.Mapped[list['Prediction']] = so.relationship(back_populates='author')
    
    def __repr__(self):
        return '<User {}>'.format(
            self.username
        )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)    
    
    def avatar(self, size):
        if(self.profile_pic_file == 'none'):
            digest = md5(self.username.lower().encode('utf-8')).hexdigest()
            return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
        else:
          return url_for('static',filename=f'profile_pics/{self.profile_pic_file}')

    def get_ranking_text(self):
        base_string = str(self.ranking)
        last_digit = int(base_string[-1])
        
        if self.ranking == 1:
            return "1st 🥇"
        elif self.ranking == 2:
            return "2nd 🥈"
        elif self.ranking == 3:
            return "3rd 🥉"
        elif self.ranking > 3 and self.ranking < 20:
            return base_string + "th"
        elif last_digit == 1:
            return base_string + "st"
        elif last_digit == 2:
            return base_string + "nd"
        elif last_digit == 3:
            return base_string + "rd"
        else:
            return base_string + "th"

    def calculate_points(self):
        # for each prediction, check it against its game then assign points
        # for now its just working off of scores, will add penalties later
        # also have to make it skip games that have already been worked out
        # TODO: skip calculated games

        self.points = 0 # stopgap while recalcing all games
        self.number_of_results = 0
        self.number_of_scores = 0
       # predictions = db.session.execute(self.predictions.select().where(Prediction.points_awarded == None)).scalars() # this ver should only get games that havent been set yet
        predictions = self.predictions # gets all predictions

        for prediction in predictions:
            # all reset to 0
            prediction.points_awarded=0
            prediction.score_points = False
            prediction.result_points = False
            prediction.bonus_points = False

            #first skip games that haven't happened yet
            if prediction.match.home_score is None or prediction.match.away_score is None:
                continue 

            # check if scores are correct
            home_correct = bool(prediction.home_score_predicted == prediction.match.home_score)
            away_correct = bool(prediction.away_score_predicted == prediction.match.away_score)

            # if this is a penlty/knockout game, scoring changes
            if prediction.match.penalty_game: 

                # gather prediction

                actual_result = (
                    "home" if prediction.match.home_score > prediction.match.away_score
                    else "away" if  prediction.match.home_score < prediction.match.away_score
                    else prediction.match.penalty_winner
                )

                predicted_result = (
                    "home" if prediction.home_score_predicted > prediction.away_score_predicted
                    else "away" if  prediction.home_score_predicted < prediction.away_score_predicted
                    else prediction.penalty_winner_predicted
                )

                actual_draw = bool(prediction.match.home_score == prediction.match.away_score)

                to_award = 0

                # check exact scores predicted are correct
                if (home_correct and away_correct):
                    prediction.score_points = True
                    if(actual_result == predicted_result): # check if had the correct result as well, when result is incorrect that's a penalty blunder
                        to_award = 8
                    else:
                        to_award = 6

                    prediction.points_awarded = to_award
                    self.points += to_award
                    continue # don't add anything on top of this
 

                if(actual_draw): # if game was actually a draw 
                    if(prediction.home_score_predicted == prediction.away_score_predicted): # if user predicted a draw
                        prediction.result_points = True
                        to_award += 3
                        
                        if(actual_result == predicted_result): # if user additionally got the pens winner
                            to_award += 2

                    else:
                        if(actual_result == predicted_result): # if user got the winner right
                            prediction.result_points = True
                            to_award += 3   


                else: # if game wasn't a draw
                    if(prediction.home_score_predicted == prediction.away_score_predicted): # and user predicted a draw
                        if(actual_result == predicted_result): # if user got the winner right
                            prediction.result_points = True
                            to_award += 3   
                    else:
                         if(actual_result == predicted_result): # if user got the winner right
                            prediction.result_points = True
                            to_award += 5   

                if (home_correct or away_correct): # bonus point for getting either score correct
                    to_award += 1
                    prediction.bonus_points = True

                prediction.points_awarded = to_award
                self.points += to_award

            #
            #
            #
            #

            else: # when it's not a penalty game

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
                    prediction.points_awarded = 5
                    prediction.score_points = True
                    self.points += 5
                    self.number_of_scores += 1
                    continue # continue as max points is 5

                if(actual_result == predicted_result): # if predicted correct result
                    prediction.points_awarded = 2
                    prediction.result_points = True
                    self.number_of_results += 1
                    self.points += 2
                
                if(home_correct or away_correct): # bonus point for a correct score
                    prediction.points_awarded += 1
                    prediction.bonus_points = True
                    self.points += 1

class Team(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    name: so.Mapped[str] = so.mapped_column(sa.String(64))
    fifa_code: so.Mapped[str] = so.mapped_column(sa.String(10))
    flag_code: so.Mapped[str] = so.mapped_column(sa.String(10))
    group:  so.Mapped[str] = so.mapped_column(sa.String(1))

    def __repr__(self):
        return '<Team ID={} Name={} FIFA code={} Flag code={} Group={}>'.format(
            self.id,
            self.name,
            self.fifa_code,
            self.flag_code,
            self.group
    )

class Game(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    home_team_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Team.id))
    away_team_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Team.id))

    home_score: so.Mapped[Optional[int]] = so.mapped_column()
    away_score: so.Mapped[Optional[int]] = so.mapped_column()
    penalty_game: so.Mapped[bool] = so.mapped_column(default=False)
    penalty_winner: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64), default='none') # will be either home, away, or none
    kickoff: so.Mapped[datetime] = so.mapped_column(index=True)

    predictions: so.Mapped[list['Prediction']] = so.relationship(back_populates='match')

    home_team: so.Mapped["Team"] = so.relationship(
        foreign_keys=[home_team_id]
    )

    away_team: so.Mapped["Team"] = so.relationship(
        foreign_keys=[away_team_id]
    )

    def __repr__(self):
        return '<Game {} vs {} @ {} Penalties: {}>'.format(
            self.home_team,
            self.away_team,
            self.kickoff.isoformat(),
            self.penalty_game
    )

    def get_average_home_score(self):
        return (
        db.session.query(func.avg(Prediction.home_score_predicted))
        .filter(Prediction.game_id == self.id)
        .scalar()
        ) or 'N/A'

    def get_average_away_score(self):
        return (
        db.session.query(func.avg(Prediction.away_score_predicted))
        .filter(Prediction.game_id == self.id)
        .scalar()
        ) or 'N/A'

class Prediction(db.Model):
    __table_args__ = (
        sa.UniqueConstraint("user_id","game_id", name="uq_prediction_user_game"),
    )

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    home_score_predicted: so.Mapped[int] = so.mapped_column(default = 0)
    away_score_predicted: so.Mapped[int] = so.mapped_column(default = 0)
    penalty_winner_predicted: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))
    points_awarded: so.Mapped[int] = so.mapped_column(default=0)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    game_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Game.id), index=True)

    score_points: so.Mapped[bool] = so.mapped_column(default=False)
    result_points: so.Mapped[bool] = so.mapped_column(default=False)
    bonus_points: so.Mapped[bool] = so.mapped_column(default=False)

    author: so.Mapped[User] = so.relationship(back_populates='predictions')
    match: so.Mapped[Game] = so.relationship(back_populates='predictions')

    def __repr__(self):
        return '<Prediction user={} game={} {}-{}>'.format(
            self.user_id,
            self.game_id,
            self.home_score_predicted,
            self.away_score_predicted
    )

class League(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    #Join code
    #Array of users

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))