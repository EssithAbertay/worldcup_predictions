from app import app
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from app import db
from app.models import Game, User, Prediction
import sqlalchemy as sa
from app import db
from sqlalchemy import func
from flask import request
from sqlalchemy.orm import selectinload

def getMatchday(matchday=None) -> int:
    # if matchday is provided from route then just return that
    if matchday is not None:
        return matchday

    firstGameToday = getFirstGameFromToday()

    # if the next game is none we've reached the end so return the final day
    if firstGameToday is None:
        return db.session.scalar(sa.select(sa.func.max(Game.matchday)))

    # return the current matchday
    return firstGameToday.matchday

# returns the first game that starts from midnight of today, can return a game from tomorrow if no games today or so on
def getFirstGameFromToday() -> Game | None:
     # use london timezone because I'm lazy and have not adjusted everything to UTC+0, maybe I will sometime
    now_time = getNowTime()

    # get next game, from beggining of today, as we want to see games from today
    return  db.session.scalar(sa.select(Game).where(func.date(Game.kickoff) >= now_time.date()).order_by(Game.kickoff))

# later use this to adjust for timezone, currently naive as i've been very lazy in the database
def getNowTime() -> datetime:
    return datetime.now(ZoneInfo("Europe/London")).replace(tzinfo=None)

# gets games on provided matchday, if no matchday is provided will fill with next available
def getGamesForMatchday(matchday=None) -> list[Game]:
    if matchday is None:
        matchday = getMatchday()

    return db.session.scalars(sa.select(Game).options(selectinload(Game.predictions), selectinload(Game.home_team),selectinload(Game.away_team)).where(Game.matchday == matchday).order_by(Game.kickoff.asc())).all()

def getUsers() -> list[User]:
    return db.session.scalars(sa.select(User)).all()

def getUsersByPointsDesc() -> list[User]:
    return db.session.scalars(sa.select(User).order_by(User.points.desc())).all()

def getUserByID(userID) -> User:
    return db.first_or_404(sa.select(User).where(User.id == userID))

def getUserbyUsername(username) -> User:
    return db.first_or_404(sa.select(User).where(User.username == username))


# might not work but until I use it we won't know 
def getUserPredictions(userID) -> list[Prediction]:
    return db.first_or_404(sa.select(User).where(User.id == userID)).predictions

def getGameFromID(gameID) -> Game:
    return db.first_or_404(sa.select(Game).where(Game.id == gameID))
