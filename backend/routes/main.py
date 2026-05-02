# backend/routes/main.py

from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/players')
def players_page():
    return render_template('players.html')

@main_bp.route('/player/<int:player_id>')
def player_profile(player_id):
    return render_template('player_profile.html', player_id=player_id)

@main_bp.route('/matches')
def matches_page():
    return render_template('matches.html')

@main_bp.route('/leaderboard')
def leaderboard_page():
    return render_template('leaderboard.html')