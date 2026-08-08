import sqlalchemy as sa
from app import app, db
from app.models import User, Game
from sqlalchemy import func
from datetime import datetime
from zoneinfo import ZoneInfo
from app.helpers import sendPushToUser

with app.app_context():
    now_time=datetime.now(ZoneInfo("Europe/London")).replace(tzinfo=None)
    game_today = db.session.scalar(
        sa.select(Game.id)
        .where(func.date(Game.kickoff) == now_time.date())
        .limit(1)
    ) is not None
    users = db.session.scalars(sa.select(User)).all()

    if game_today:
        for user in users:
            sendPushToUser(user.id, "SPFL Predictions 26/27", "Games are on today! Don't forget to predict!")
