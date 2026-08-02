from flask import render_template, flash, redirect, url_for, request, abort
from urllib.parse import urlsplit
from app import app
from app.forms import LoginForm, RegistrationForm, AdminGameSubmission, EditUsernameForm, PredictionForm, AdminResultForm, AdminRecalculatePoints, AdminTeamSubmission, EditPicForm, AdminEditGameForm, EditDisplayNameForm, EditUserColourForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from app import db
from app.models import User, Game, Prediction, Team
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from zoneinfo import ZoneInfo
from uuid import uuid4
from pathlib import Path
from PIL import Image, ImageOps
import json
from app.helpers import getMatchday, getNowTime, getGamesForMatchday, getUsersByPointsDesc, getUsers, getGameFromID, getUserbyUsername
from collections import defaultdict
from math import floor

# TODO: make nowtime, matchday, matchday games, etc a seperate python file, as i keep writing the same fecking code

@app.route('/')
@app.route('/index')
@app.route("/index/matchday-<int:matchday>")
@login_required
def index(matchday=None):
    # REQUIREMENTS FOR NEW INDEX PAGE
    # 1. Stats by matchday
    #       Points Earned
    #       Positions Gained
    # 2. Rank History by Matchday
    # 3. Games by matchday

    # GET current matchday
    matchday = getMatchday(matchday)
    lastMatchday = db.session.scalar(sa.select(sa.func.max(Game.matchday))) # maybe make this a helper too?

    # get games on the matchday indicated
    matchdayGames = getGamesForMatchday(matchday)

    # calculate prediction stats for this matchdays games, i.e. percent that predict each result
    matchdayPredictions = []

    # matchday game stats
    for game in matchdayGames:
        home = 0
        away = 0
        draw = 0

        for prediction in game.predictions:
            if(prediction.home_score_predicted > prediction.away_score_predicted):
                home += 1
            elif (prediction.home_score_predicted < prediction.away_score_predicted):
                away += 1
            else:
                draw +=1

        total = (home + away + draw) if (home + away + draw) != 0 else 1

        home_percent = round((home / total) * 100,1)
        away_percent = round((away / total) * 100,1)
        draw_percent = round((draw / total) * 100,1)

        matchdayPredictions.append([home_percent,away_percent,draw_percent])

    # matchday users stats, maybe divide by game?

    # matchday points, who got the most points on x day!, This is kinda bad as it's an N+1 Query Problem, but whatever it works and we only have 10 users anyway
    users = getUsers()

    matchdayPointsEarned = []

    for user in users:
        matchdayPointsEarned.append([user.display_name, user.getMatchdayPoints(matchday), user.colour])

    matchdayPointsEarned.sort(key=lambda x: x[1], reverse=True)



    # create an average table based on our predictions
    # create a cumulative table based on our predictions
    # both is more fun!

    teams = db.session.scalars(sa.select(Team)).all()
  
    averagePredictionTableData = {}
    cumulativePredictionTableData = {}

    for team in teams:
        averagePredictionTableData[team.id] = {
        "pts": 0,
        "gf": 0,
        "ga": 0,
        "gd": 0,
        "w": 0,
        "l": 0,
        "d": 0,
        }

        cumulativePredictionTableData[team.id] = {
        "pts": 0,
        "gf": 0,
        "ga": 0,
        "gd": 0,
        "w": 0,
        "l": 0,
        "d": 0,
        }


    predictions = db.session.scalars(sa.select(Prediction)).all()

    # Group predictions by match for the average table
    predictionsByMatch = defaultdict(list)

    for prediction in predictions:
        predictionsByMatch[prediction.game_id].append(prediction)

        home_id = prediction.match.home_team_id 
        away_id = prediction.match.away_team_id

        home = prediction.home_score_predicted
        away = prediction.away_score_predicted

        cumulativePredictionTableData[home_id]["gf"] += home
        cumulativePredictionTableData[away_id]["gf"] += away

        cumulativePredictionTableData[home_id]["ga"] += away
        cumulativePredictionTableData[away_id]["ga"] += home

        if(home > away):
            cumulativePredictionTableData[home_id]["pts"] +=3
            cumulativePredictionTableData[home_id]["w"] +=1
            cumulativePredictionTableData[away_id]["l"] +=1
        elif(away >home):
            cumulativePredictionTableData[away_id]["pts"] +=3
            cumulativePredictionTableData[away_id]["w"] +=1
            cumulativePredictionTableData[home_id]["l"] +=1
        else:
            cumulativePredictionTableData[home_id]["pts"] +=1
            cumulativePredictionTableData[away_id]["pts"] +=1
            cumulativePredictionTableData[home_id]["d"] +=1
            cumulativePredictionTableData[away_id]["d"] +=1


    for matchPredictions in predictionsByMatch.values():
        match = matchPredictions[0].match

        home_id = match.home_team_id
        away_id = match.away_team_id

        avg_home = floor(sum(
            p.home_score_predicted for p in matchPredictions
        ) / len(matchPredictions))

        avg_away = floor(sum(
            p.away_score_predicted for p in matchPredictions
        ) / len(matchPredictions))

        averagePredictionTableData[home_id]["gf"] += avg_home
        averagePredictionTableData[away_id]["gf"] += avg_away

        averagePredictionTableData[home_id]["ga"] += avg_away
        averagePredictionTableData[away_id]["ga"] += avg_home

        if avg_home > avg_away:
            averagePredictionTableData[home_id]["pts"] += 3
            averagePredictionTableData[home_id]["w"] +=1
            averagePredictionTableData[away_id]["l"] +=1
        elif avg_away > avg_home:
            averagePredictionTableData[away_id]["pts"] += 3
            averagePredictionTableData[away_id]["w"] +=1
            averagePredictionTableData[home_id]["l"] +=1
        else:
            averagePredictionTableData[home_id]["pts"] += 1
            averagePredictionTableData[away_id]["pts"] += 1
            averagePredictionTableData[home_id]["d"] +=1
            averagePredictionTableData[away_id]["d"] +=1



    # TODO: Account for top 6 split .... somehow
    cumulativePredictedTableList = []

    for team in teams:
        cumulativePredictionTableData[team.id]["gd"] =  cumulativePredictionTableData[team.id]["gf"] -  cumulativePredictionTableData[team.id]["ga"]
        cumulativePredictedTableList.append([team, cumulativePredictionTableData[team.id]])

    cumulativePredictedTableList.sort(key=lambda x: (x[1]["pts"],x[1]["gd"],x[1]["gf"],), reverse=True)


    averagePredictedTableList = []

    for team in teams:
        averagePredictionTableData[team.id]["gd"] = (averagePredictionTableData[team.id]["gf"]- averagePredictionTableData[team.id]["ga"])
        averagePredictedTableList.append([team, averagePredictionTableData[team.id]])

    averagePredictedTableList.sort(key=lambda x: (x[1]["pts"],x[1]["gd"],x[1]["gf"],),reverse=True,)


    context = {
        "title": "Home",
        "matchday": matchday,
        "maxMatchday": lastMatchday,
        "matchdayGames": matchdayGames,
        "matchdayPredictions": matchdayPredictions,
        "matchdayPointsEarned": matchdayPointsEarned,
        "nowTime": getNowTime(),
        "cumulativeTable": cumulativePredictedTableList,
        "averageTable": averagePredictedTableList
    }

    return render_template('index.html', **context)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        logging_in_user = db.session.scalar(sa.select(User).where(User.username == form.username.data))
        if logging_in_user is None or not logging_in_user.check_password(form.password.data):
            flash('Invalid username and/or password!')
            return redirect(url_for('login'))
        #login_user(logging_in_user, remember=form.remember_me.data)
        login_user(logging_in_user, remember=False) # removed rememebr me for now
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET','POST'])
def register():
    print(
        "REGISTER",
        current_user.is_authenticated,
        getattr(current_user, "id", None),
        getattr(current_user, "username", None)
    )


    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(username=form.username.data, display_name=form.display_name.data)

        print("NEW USER OBJECT")
        print("id:", new_user.id)
        print("username:", new_user.username)
        print("displayName:", new_user.display_name)

        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@app.route('/user/<username>/matchday-<int:matchday>')
@login_required
def user(username, matchday=None):
    user = db.first_or_404(sa.select(User).where(User.username == username))

    matchday = getMatchday(matchday)

    # get total prediction count
    # get number of predicitons awarded 5 points - correct score
    # get number of predicitons awarded 2/3 points - correct result
    # get number of predicitons awarded 3 points - received bonus

    stats = db.session.execute(
        sa.select(
            sa.func.count(Prediction.id).label("total"),
            sa.func.sum(sa.case((Prediction.score_points,1), else_=0)).label("scores"),
            sa.func.sum(sa.case((Prediction.result_points,1), else_=0)).label("results"),
            sa.func.sum(sa.case((Prediction.bonus_points,1), else_=0)).label("bonus"),
        ).where(Prediction.user_id == user.id)).one()

    games_total = stats.total
    scores_total = stats.scores
    results_total = stats.results
    bonus_total = stats.bonus

    # super unsafe method of getting the machdays user has predicted, as ignores that user might've missed a matchday ...somehow also ignores that user might not have any predictions
    largestPredictedMatchday = user.predictions[-1].match.matchday + 1 or 0


    # this is so stupid
    query = sa.select(User)
    users = db.session.scalars(query).all()
    user_count = len(users)

    now_time = (datetime.now(ZoneInfo("Europe/London"))).replace(tzinfo=None)  # go a day into the future so that you can see todays games
    today = now_time

    # get all teams
    # get all user predictions
    
    # for each prediction check result expected then assign points GD GF GA for each team, then sort!

    teams = db.session.scalars(sa.select(Team)).all()
  
    data = {}

    for team in teams:
        data[team.id] = {
        "pts": 0,
        "gf": 0,
        "ga": 0,
        "gd": 0,
        "w": 0,
        "l": 0,
        "d": 0,
    }


    for prediction in user.predictions:
        if(prediction.match.kickoff > getNowTime() and current_user.id != user.id):
            continue

        home_id = prediction.match.home_team_id 
        away_id = prediction.match.away_team_id

        home = prediction.home_score_predicted
        away = prediction.away_score_predicted

        data[home_id]["gf"] += home
        data[away_id]["gf"] += away

        data[home_id]["ga"] += away
        data[away_id]["ga"] += home

        if(home > away):
            data[home_id]["pts"] +=3
            data[home_id]["w"] +=1
            data[away_id]["l"] +=1
        elif(away >home):
            data[away_id]["pts"] +=3
            data[away_id]["w"] +=1
            data[home_id]["l"] +=1
        else:
            data[home_id]["pts"] +=1
            data[away_id]["pts"] +=1
            data[home_id]["d"] +=1
            data[away_id]["d"] +=1


    # TODO: Account for top 6 split .... somehow
    predictedTableData = []

    for team in teams:
        data[team.id]["gd"] =  data[team.id]["gf"] -  data[team.id]["ga"]
        predictedTableData.append([team, data[team.id]])

    predictedTableData.sort(key=lambda x: (x[1]["pts"],x[1]["gd"],x[1]["gf"],), reverse=True)
  
    return render_template('user.html', user=user, games_total=games_total, scores_total=scores_total, results_total=results_total, bonus_total=bonus_total, today=today, predictedMatchdays=range(1,largestPredictedMatchday), predictedTableData=predictedTableData)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    username_form = EditUsernameForm(current_user.username)
    profile_form = EditPicForm()

    displayNameForm = EditDisplayNameForm(current_user.display_name)
    userColourForm = EditUserColourForm(current_user.colour)

    if request.method == 'GET':
        username_form.username.data = current_user.username
        displayNameForm.displayName.data = current_user.display_name
        userColourForm.userColour.data = current_user.colour

    if request.method == 'POST':
        if username_form.submitUsername.data and username_form.validate_on_submit():
            current_user.username = username_form.username.data
            print(
                "UPDATING USER username",
                current_user.id,
                current_user.username
            )

            db.session.commit()
            flash('Your changes have been saved.')
            return redirect( url_for('user', username=current_user.username))


        if profile_form.submitProfilePic.data and profile_form.validate_on_submit():
            picture = profile_form.profile.data

            if picture:
                try:
                    img = Image.open(picture)
                    img.verify()
                except Exception:
                    flash("Invalid image file")
                    return redirect( url_for('user', username=current_user.username))

                picture.seek(0)   
                img = Image.open(picture)
                img = ImageOps.exif_transpose(img)
                img.thumbnail((512, 512))

                #delete old pic if it exists

                if current_user.profile_pic_file != "none":
                    old_path = Path(app.root_path) / "static" / "profile_pics" / current_user.profile_pic_file

                    if old_path.exists():
                        old_path.unlink()

                ext = Path(picture.filename).suffix.lower()
                filename = f"{uuid4().hex}{ext}"

                flash(filename)
                img.save(Path(app.root_path) / "static" / "profile_pics" / filename)
                current_user.profile_pic_file = filename

                print(
                    "UPDATING USER profile pic",
                    current_user.id,
                    current_user.username
                )

                db.session.commit()
                flash('Your changes have been saved.')
            else:
                flash(' Didnt Got Data')
            
            return redirect(url_for('edit_profile'))


        if displayNameForm.submitDisplayName.data and displayNameForm.validate_on_submit():
            current_user.display_name = displayNameForm.displayName.data
            db.session.commit()
            flash('Your changes have been saved.')
            return redirect( url_for('user', username=current_user.username))


        if userColourForm.submitUserColour.data and userColourForm.validate_on_submit():
            current_user.colour = userColourForm.userColour.data
            db.session.commit()
            flash('Your changes have been saved.')
            return redirect( url_for('user', username=current_user.username))


    return render_template('edit_profile.html', title='Edit Profile', username_form=username_form, profile_form = profile_form, displayNameForm=displayNameForm,userColourForm=userColourForm)

@app.route('/matches', methods=['GET','POST'])
@app.route('/matches/matchday-<int:matchday>', methods=['GET','POST'])
@login_required
def matches(matchday=None):
    nowTime = getNowTime()
    matchday = getMatchday(matchday)
    lastMatchday = db.session.scalar(sa.select(sa.func.max(Game.matchday))) # maybe make this a helper too?
    
    games = getGamesForMatchday(matchday) # Need to remove all entries that are postponed from this, as otherwise get double filed when missed games are added

    postponed = False

    for game in games:
        if game.status == "postponed":
            postponed = True
            games.remove(game)

    predictions =  db.session.scalars(sa.select(Prediction).where(Prediction.user_id == current_user.id)).all()

    prediction_map = {
        p.game_id: p
        for p in predictions
    }

    form = PredictionForm()

    # get games that were postponed in the past, or were missed for some reason, i.e. rescheduled due to cup games, could also just consider them postponed? might be easier

    missedGames= db.session.scalars(sa.select(Game).where(Game.status == "postponed")).all()

    if (missedGames == ''):
        postponed = True


    if request.method == 'GET':
        for game in games +  missedGames: # prepopulate all the games
            entry = form.predictions.append_entry()

            entry.game_id.data = game.id
            entry.kickoff_time = game.kickoff
            entry.home_team = game.home_team
            entry.away_team = game.away_team
            entry.status = game.status
            entry.matchday = game.matchday


            existing_prediction = prediction_map.get(game.id)

            if existing_prediction:
                entry.home_score.data = existing_prediction.home_score_predicted
                entry.away_score.data = existing_prediction.away_score_predicted
               
    if request.method == 'POST' and form.validate_on_submit():

        predictions = json.loads(
            request.form.get("all_predictions", "{}")
        )

        for game_id, prediction in predictions.items():

            if(getGameFromID(game_id).kickoff < getNowTime()):
                flash("Cannot change games that have already started!")
                continue

            home_score = int(prediction["home"])
            away_score = int(prediction["away"])

            if home_score is None and away_score is None:
                continue

            if home_score is None:
                home_score = 0

            if away_score is None:
                away_score = 0

            existing_prediction = prediction_map.get(int(game_id))
            
            if existing_prediction:
                existing_prediction.home_score_predicted = home_score
                existing_prediction.away_score_predicted = away_score
            else:
                prediction = Prediction(user_id=current_user.id ,game_id=game_id, home_score_predicted=home_score, away_score_predicted=away_score)
                prediction_map[prediction.game_id] = prediction # add it to the map so that we deal with low latency and duplicates aren't possible
                db.session.add(prediction)


        print(
            "UPDATING USER predictions",
            current_user.id,
            current_user.username
        )

        try:   
            db.session.commit()
        except:
            db.session.rollback()
            flash("Error Saving Predictions! Try again later!")
            return redirect(url_for('matches'))

        flash('Your predictions have been saved!')
        return redirect(url_for('matches', saved=1))
    else:
        print(form.errors)

    return render_template('matches.html', title='Upcoming Games', form = form, today=date.today(), matchday=matchday, postponed=postponed, lastMatchday = lastMatchday)

@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    query = (
        sa.select(User)
        .order_by(User.points.desc(), User.number_of_scores.desc(), User.number_of_results.desc())
        .options(
            selectinload(User.predictions)
            .selectinload(Prediction.match)
            .selectinload(Game.home_team),

            selectinload(User.predictions)
            .selectinload(Prediction.match)
            .selectinload(Game.away_team)
        )
    )

    users = db.session.scalars(query).all()


    now_time = (datetime.now(ZoneInfo("Europe/London"))).replace(tzinfo=None)  # go a day into the future so that you can see todays games
    cutoff = now_time - timedelta(days=1)
    for user in users:
        user.upcoming_predictions = [
            p for p in user.predictions
            if p.match.kickoff >= cutoff
        ]


    today = now_time

    return render_template('leaderboard.html', title='Leaderboard', users=users, today=today)

@app.route('/faq')
def faq():
    return render_template('faq.html', title='FAQ')

@app.route('/admin_panel', methods=['GET','POST'])
@login_required
def admin_panel():
    if not current_user.is_admin:
        abort(403)

    return render_template('admin_panel.html', title='Admin Panel')

@app.route('/admin_panel/matches', methods=['GET','POST'])
@login_required
def adminMatches():
    if not current_user.is_admin:
            abort(403)

    # IGNORE THIS ONE, IM GOING TO USE IT FOR DISPLAYING ALL MATCHES IN A TABLE

    return render_template('admin/admin_matches.html', title='Admin Matches')

@app.route('/admin_panel/matches/add', methods=['GET','POST'])
@login_required
def adminMatchesAdd():
    if not current_user.is_admin:
            abort(403)

    # adding games
    addGameForm = AdminGameSubmission()
    teams = db.session.scalars(sa.select(Team).order_by(Team.name)).all()

    # populate dropdown choices
    addGameForm.home_team.choices = [(t.id, t.name) for t in teams]
    addGameForm.away_team.choices = [(t.id, t.name) for t in teams]

    if request.method == 'POST':


        if addGameForm.submit_game.data and addGameForm.validate():
            game = Game(home_team_id=addGameForm.home_team.data, away_team_id=addGameForm.away_team.data, kickoff=addGameForm.kickoff.data, matchday=addGameForm.matchday.data)
            db.session.add(game)
            db.session.commit()
            return redirect(url_for('adminMatchesAdd'))
        else:
            print(addGameForm.errors)


    return render_template('admin/add_match.html', title='Add Matches', addGameForm=addGameForm)

@app.route('/admin_panel/matches/edit', methods=['GET','POST'])
@login_required
def adminMatchesEdit():
    if not current_user.is_admin:
            abort(403)
   # edit games form
    editGameForm = AdminEditGameForm()

    allGames = db.session.scalars(sa.select(Game)).all()

    # making it so that it is obvious which game i'm trying to change
    editGameForm.game_id.choices = [ (0, "Select a game")] + [ (g.id, f"{g.id} - {g.home_team.name} vs {g.away_team.name} - {g.kickoff.date()}") for g in allGames]

    if request.method == 'POST' and editGameForm.submitGameEdit.data and editGameForm.validate():
        gameToEdit = db.session.get(Game, editGameForm.game_id.data)
        flash("Before Edit:")
        flash(str(gameToEdit))

        if(editGameForm.home_score.data is not None):
            gameToEdit.home_score = editGameForm.home_score.data

        if(editGameForm.away_score.data is not None):
            gameToEdit.away_score = editGameForm.away_score.data

        if(editGameForm.kickoff.data is not None):
            gameToEdit.kickoff = editGameForm.kickoff.data

        if (editGameForm.status.data != "none"):
            gameToEdit.status = editGameForm.status.data
           
        db.session.commit()

        flash("After Edit:")
        flash(str(gameToEdit))
        return redirect(url_for('adminMatchesEdit'))
    else:
        print(editGameForm.errors)

    return render_template('admin/edit_match.html', title='Edit Matches', editGameForm=editGameForm)

@app.route('/admin_panel/matches/results', methods=['GET','POST'])
@login_required
def adminResults():
    if not current_user.is_admin:
            abort(403)

    # adding results to games
    addResultsForm = AdminResultForm() 

    query = sa.select(Game).filter(Game.home_score == None)
    games_query = db.session.scalars(query).all()

    if request.method == 'GET':
        for game in games_query:
            print(game)
            entry = addResultsForm.results.append_entry()
            entry.game_id.data = game.id
            entry.home_team = game.home_team.name
            entry.away_team = game.away_team.name


    if request.method == 'POST':
        if addResultsForm.submit_results.data and addResultsForm.validate():
            print('adding games')
            flash('registering')

            for field in addResultsForm.results:
                g = db.session.get(Game, field.game_id.data)

                if field.home_score is None and field.away_score is None:
                    continue

                g.home_score = field.home_score.data
                g.away_score = field.away_score.data
                flash('registered result')

            db.session.commit()
            return redirect(url_for('adminResults'))
        else:
            print(addResultsForm.errors)

    
    return render_template('admin/add_results.html', title='Add Results', addResultsForm=addResultsForm)

@app.route('/admin_panel/teams', methods=['GET','POST'])
@login_required
def adminTeams():
    if not current_user.is_admin:
            abort(403)

    # IGNORE THIS ONE, IM GOING TO USE IT FOR DISPLAYING ALL TEAMS IN A TABLE

    return render_template('admin/admin_teams.html', title='Admin Teams')

@app.route('/admin_panel/teams/register', methods=['GET','POST'])
@login_required
def adminTeamsRegister():
    if not current_user.is_admin:
            abort(403)

        # adding teams
    addTeamForm = AdminTeamSubmission()

    if request.method == 'POST':

        if addTeamForm.submit.data and addTeamForm.validate():
            team = Team(name=addTeamForm.team.data, short_name=addTeamForm.short_name.data)
            db.session.add(team)
            db.session.commit()
            flash('Registered Team')
            return redirect(url_for('adminTeamsRegister'))
        else:
            print(addTeamForm.errors)

    return render_template('admin/register_team.html', title='Teams', addTeamForm=addTeamForm)

@app.route('/admin_panel/users', methods=['GET','POST'])
@login_required
def adminUsers():
    if not current_user.is_admin:
            abort(403)

    # recalculating points    
    recalculate_points = AdminRecalculatePoints()

    if request.method == 'POST':
        if recalculate_points.recalculate_points.data and recalculate_points.validate():
            
            #get users and update scores
            query = sa.select(User)
            flash('got query')
            flash('attempting to getusers')
            users = db.session.scalars(query).all()
            flash('got users')

            now = datetime.now(ZoneInfo("Europe/London"))

            for index, user in enumerate(users):
                string = 'attempting to update' + user.username
                flash(string)
                old_points = user.points
                user.calculate_points()
                new_points = user.points
                flash('updated scores for user')

                points_history = user.points_history or []

                flash("updating points record")

                points_history.append({"old": old_points, "new": new_points, "datetime": now.isoformat()})
                user.points_history = points_history
            
            db.session.commit()
            #have to redo the query as scores now updated

            query = sa.select(User).order_by(User.points.desc(), User.number_of_scores.desc(), User.number_of_results.desc())
            flash('got query')
            flash('attempting to getusers')
            users = db.session.scalars(query).all()
            flash('got users')

            #sort users TODO: FIX to only do by matchday
            for index, user in enumerate(users):
                rank_history = user.ranking_history or []

                current_rank = (index + 1)

                user.previous_ranking = current_rank # make current ranking the old ranking

                new_rank = index+1 # +1 to account for 0

                rank_history = user.ranking_history or []
    
                rank_history.append({"old": current_rank, "new": new_rank, "datetime": now.isoformat()})

                user.ranking_history = rank_history

            db.session.commit()
            return redirect(url_for('adminUsers'))


    return render_template('admin/admin_users.html', title='Admin Users', recalculate_points=recalculate_points)