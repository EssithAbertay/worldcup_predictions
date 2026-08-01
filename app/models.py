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
from pathlib import Path



# TODO: Readd email support
# TODO: Add display names
# TODO: Add leagues, use ranking history in user for global ranks, store local ranking history within custom league
class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    display_name: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
       
    #email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    points: so.Mapped[int] = so.mapped_column(default=0) # all scores awarded are multiplied by 2, to account for half points
    ranking_history: so.Mapped[list[dict]] = so.mapped_column(MutableList.as_mutable(JSON))
    points_history: so.Mapped[list[dict]] = so.mapped_column(MutableList.as_mutable(JSON))
    is_admin: so.Mapped[bool] = so.mapped_column(default=False)
    profile_pic_file: so.Mapped[str] = so.mapped_column(sa.String(64), default='none')

    number_of_scores: so.Mapped[int] = so.mapped_column(nullable=True, default=0)
    number_of_results: so.Mapped[int] = so.mapped_column(nullable=True, default=0)

    colour: so.Mapped[str] = so.mapped_column(sa.String(7),default="#e82a2a")

    predictions: so.Mapped[list['Prediction']] = so.relationship(back_populates='author')
    
    def __repr__(self):
        return '<User {}>'.format(
            self.username
        )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)    
    
    # TODO: Fix bug in avatar function that always returns the gravatar

    def avatar(self, size):
        # get the supposed path to a users profile picture
        path = Path(f'profile_pics/{self.profile_pic_file}')

        # if a file exists at the path, return it, otherwise return a gravatar
        if(path.is_file()):
            return url_for('static',filename=f'profile_pics/{self.profile_pic_file}')
        else:
            digest = md5(self.username.lower().encode('utf-8')).hexdigest()
            return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
       
    def getMatchdayPredictions(self, matchday: int):
        return [
            p for p in self.predictions
            if p.match.matchday == matchday
        ]

    @property
    def getCurrentRank(self):
        if self.ranking_history:
            return self.ranking_history[-1].get("new", 1)
        return "NC"

    # this is used whenever i get points that need displayed
    @property
    def actualPoints(self) -> float:
        return self.points / 2 

    #Accounts for point dividing
    def getMatchdayPoints(self, matchday) -> float:
        return (
            db.session.scalar(
                sa.select(func.coalesce(func.sum(Prediction.points_awarded), 0))
                .join(Prediction.match)
                .where(
                    Prediction.user_id == self.id,
                    Game.matchday == matchday,
                )
            ) / 2
            or 0
        )    
    
    def getGlobalRankingText(self):
        if not self.ranking_history:
            return "Global Rank: Unranked"

        current_rank = self.ranking_history[-1]["new"]


        base_string = "Global Rank: " + str(current_rank)
        last_digit = int(base_string[-1])
        
        if current_rank == 1:
            return "1st 🥇"
        elif current_rank == 2:
            return "2nd 🥈"
        elif current_rank == 3:
            return "3rd 🥉"
        elif current_rank > 3 and current_rank < 20:
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
                prediction.points_awarded = 10
                prediction.score_points = True
                self.points += 10
                self.number_of_scores += 1
                continue # continue as max points is 5

            if(actual_result == predicted_result): # if predicted correct result
                prediction.points_awarded = 4
                prediction.result_points = True
                self.number_of_results += 1
                self.points += 4
            # checking bonuses
            
            # correct score bonus
            if(home_correct or away_correct): # bonus point for a correct score
                prediction.points_awarded += 2
                prediction.bonus_points = True
                self.points += 2


            predictedHomeGoals = prediction.home_score_predicted
            predictedAwayGoals = prediction.away_score_predicted

            actualHomeGoals = prediction.match.home_score
            actualAwayGoals = prediction.match.away_score

            predictedGoalCount = predictedHomeGoals + predictedAwayGoals
            predictedGoalMargin = abs(predictedHomeGoals - predictedAwayGoals)

            actualGoalCount = actualHomeGoals +actualAwayGoals
            actualGoalMargin = abs(actualHomeGoals - actualAwayGoals)

            # correct winning margin bonus

            if(predictedGoalMargin == actualGoalMargin and actual_result == predicted_result):
                prediction.points_awarded += 2
                prediction.bonus_points = True
                self.points += 2

            # correct number of goals bonus

            if(predictedGoalCount == actualGoalCount):
                prediction.points_awarded += 1
                prediction.bonus_points = True
                self.points += 1

class Team(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    name: so.Mapped[str] = so.mapped_column(sa.String(64))
    short_name: so.Mapped[str] = so.mapped_column(sa.String(64))
    logo_file: so.Mapped[str] = so.mapped_column(sa.String(64), default='none')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.short_name and not self.logo_file:
            self.logo_file = f"{self.short_name.lower()}.svg"


    def __repr__(self):
        return '<Team ID={} Name={} Short Name={}>'.format(
            self.id,
            self.name,
            self.short_name,
    )

    def logo(self):
          return url_for('static',filename=f'logos/{self.logo_file}')

class Game(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    home_team_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Team.id))
    away_team_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Team.id))

    home_score: so.Mapped[Optional[int]] = so.mapped_column()
    away_score: so.Mapped[Optional[int]] = so.mapped_column()
    kickoff: so.Mapped[datetime] = so.mapped_column(index=True)
    matchday: so.Mapped[int] = so.mapped_column(index=True)

    status: so.Mapped[str] = so.mapped_column(default="scheduled")

    predictions: so.Mapped[list['Prediction']] = so.relationship(back_populates='match')

    home_team: so.Mapped["Team"] = so.relationship(
        foreign_keys=[home_team_id]
    )

    away_team: so.Mapped["Team"] = so.relationship(
        foreign_keys=[away_team_id]
    )

    def __repr__(self):
        return '<Game: {} vs {} Kickoff: {} Score: {}-{} Status: {}>'.format(
            self.home_team,
            self.away_team,
            self.kickoff.isoformat(),
            self.home_score,
            self.away_score,
            self.status
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
    points_awarded: so.Mapped[int] = so.mapped_column(default=0)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    game_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Game.id), index=True)

    score_points: so.Mapped[bool] = so.mapped_column(default=False)
    result_points: so.Mapped[bool] = so.mapped_column(default=False)
    bonus_points: so.Mapped[bool] = so.mapped_column(default=False)

    author: so.Mapped[User] = so.relationship(back_populates='predictions')
    match: so.Mapped[Game] = so.relationship(back_populates='predictions')

    def __repr__(self):
        return '<Prediction user={} game={} {}-{} {}>'.format(
            self.user_id,
            self.game_id,
            self.home_score_predicted,
            self.away_score_predicted,
            self.match.kickoff.isoformat()
    )

class League(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    #Join code
    #Array of users

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))