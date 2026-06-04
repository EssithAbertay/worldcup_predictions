from flask import render_template, flash, redirect, url_for, request, abort
from urllib.parse import urlsplit
from app import app
from app.forms import LoginForm, RegistrationForm, AdminGameSubmission, EditProfileForm, PredictionForm, AdminResultForm, AdminRecalculatePoints

from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from app import db
from app.models import User, Game, Prediction
from datetime import datetime, date
from sqlalchemy import func
from app.classes import TopUser


@app.route('/')
@app.route('/index')
@login_required
def index():
    games = db.session.scalars(sa.select(Game).where(func.date(Game.kickoff) == date.today())).all()
    users = db.session.scalars(sa.select(User).order_by(User.points.desc()).limit(5)).all()

    leaderboard = []

    for user in users:
        query = sa.select(Prediction).join(Prediction.match).where(Game.kickoff >= date.today()).limit(4)
        predictions = db.session.scalars(query).all()

        leaderboard.append(TopUser(user=user,predictions=predictions))

    return render_template('index.html', title='Home', games=games, leaderboard=leaderboard)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username and/or password!')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
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
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))

    query = user.predictions.select()
    predictions = db.session.scalars(query).all()

    return render_template('user.html', user=user, predictions=predictions)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    return render_template('edit_profile.html', title='Edit Profile', form=form)


@app.route('/upcoming_games', methods=['GET','POST'])
@login_required
def upcoming_games():
    right_now = datetime.now() # we all love a little fatboy slim ;)

    games = db.session.scalars(sa.select(Game).where(Game.kickoff > right_now)).all()
    predictions =  db.session.scalars(sa.select(Prediction).where(Prediction.user_id == current_user.id)).all()

    prediction_map = {
    p.game_id: p
    for p in predictions
    }

    form = PredictionForm()
    
    predicted_games = []
    unpredicted_games = []

    if request.method == 'GET':
        for id, game in enumerate(games):
            print(game)

            existing_prediction = prediction_map.get(game.id)

            entry = form.predictions.append_entry()
            entry.game_id.data = game.id

            entry.penalties_required = game.penalty_game

            entry.kickoff_time = game.kickoff
            entry.home_team = game.home_team
            entry.away_team = game.away_team     

            # prepopulating the fields 

            if existing_prediction:
                entry.home_score.data = existing_prediction.home_score_predicted
                entry.away_score.data = existing_prediction.away_score_predicted
                predicted_games.append(id)
            else:
                unpredicted_games.append(id)
               
    if form.validate_on_submit():
        for field in form.predictions:
            home_score = field.home_score.data
            away_score = field.away_score.data
            penalty_winner = field.penalty_winner.data

            if home_score is None and away_score is None:
                continue

            if home_score is None:
                home_score = 0

            if away_score is None:
                away_score = 0

            existing_prediction = prediction_map.get(field.game_id.data)

            if existing_prediction:
                flash('Prediction did exist, updating')
                existing_prediction.home_score_predicted = home_score
                existing_prediction.away_score_predicted = away_score
                existing_prediction.penalty_winner_predicted = penalty_winner
            else:
                flash('Prediction didn\'t exist, adding')
                prediction = Prediction(user_id=current_user.id ,game_id=field.game_id.data, home_score_predicted=home_score, away_score_predicted=away_score, penalty_winner_predicted=penalty_winner)
                db.session.add(prediction)

        db.session.commit()

        flash('Your predictions have been saved.')
        return redirect(url_for('upcoming_games'))
    else:
        print(form.errors)

    return render_template('upcoming_games.html', title='Upcoming Games', form = form, predicted_games = predicted_games, unpredicted_games = unpredicted_games)

@app.route('/admin_panel', methods=['GET','POST'])
@login_required
def admin_panel():
    if not current_user.is_admin:
        abort(403)

    # adding games
    add_game_form = AdminGameSubmission()

    # adding results to games

    add_result_form = AdminResultForm() 

    query = sa.select(Game).filter(Game.home_score == None)
    games_query = db.session.scalars(query).all()

    # recalculating points

    recalculate_points = AdminRecalculatePoints()

    if request.method == 'GET':
        for game in games_query:
            print(game)
            entry = add_result_form.results.append_entry()
            entry.game_id.data = game.id
            entry.home_team = game.home_team
            entry.away_team = game.away_team    
            entry.penalty_game = game.penalty_game

    if request.method == 'POST':
        if add_game_form.submit_game.data and add_game_form.validate():
            game = Game(home_team=add_game_form.home_team.data, away_team=add_game_form.away_team.data, kickoff=add_game_form.kickoff.data, penalty_game=add_game_form.is_penalty_game.data)
            db.session.add(game)
            db.session.commit()
            return redirect(url_for('admin_panel'))
        else:
            print(add_game_form.errors)

        if add_result_form.submit_results.data and add_result_form.validate():
            print('adding games')
            flash('registering')

            for field in add_result_form.results:
                g = db.session.get(Game, field.game_id.data)

                if field.home_score is None and field.away_score is None:
                    continue

                g.home_score = field.home_score.data
                g.away_score = field.away_score.data
                g.penalty_winner = field.penalty_winner.data
                flash('registered result')

            db.session.commit()
            return redirect(url_for('admin_panel'))
        else:
            print(add_result_form.errors)

        if recalculate_points.recalculate_points.data and recalculate_points.validate():
            query = sa.select(User).order_by(User.points.desc())
            flash('got query')
            flash('attempting to getusers')
            users = db.session.scalars(query).all()
            flash('got users')

            for user in users:
                flash('attempting to update user scores')
                user.calculate_points()
                flash('updated scores for user')

            db.session.commit()

            return redirect(url_for('admin_panel'))

    return render_template('admin_panel.html', title='Admin Panel', add_game_form=add_game_form, add_result_form=add_result_form, recalculate_points = recalculate_points)



@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    query = sa.select(User).order_by(User.points.desc())
    users = db.session.scalars(query).all()
    return render_template('leaderboard.html', title='Leaderboard', users=users)

@app.route('/faq')
def faq():
    return render_template('faq.html', title='FAQ')

