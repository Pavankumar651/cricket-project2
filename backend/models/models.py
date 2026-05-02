"""
Database Models - SQLAlchemy ORM
"""
from backend.app import db
from flask_login import UserMixin
from datetime import datetime


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(20), default='All Rounder')
    is_active = db.Column(db.Boolean, default=True)
    jersey_number = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    career_stats = db.relationship('PlayerCareerStats', backref='player', uselist=False)


class PlayerCareerStats(db.Model):
    __tablename__ = 'player_career_stats'
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), primary_key=True)
    total_runs = db.Column(db.Integer, default=0)
    balls_faced = db.Column(db.Integer, default=0)
    matches_batted = db.Column(db.Integer, default=0)
    highest_score = db.Column(db.Integer, default=0)
    times_out = db.Column(db.Integer, default=0)
    fours = db.Column(db.Integer, default=0)
    sixes = db.Column(db.Integer, default=0)
    singles = db.Column(db.Integer, default=0)
    doubles = db.Column(db.Integer, default=0)
    triples = db.Column(db.Integer, default=0)
    overs_bowled = db.Column(db.Numeric(6, 1), default=0)
    balls_bowled = db.Column(db.Integer, default=0)
    runs_conceded = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)
    matches_bowled = db.Column(db.Integer, default=0)
    best_wickets = db.Column(db.Integer, default=0)
    best_runs = db.Column(db.Integer, default=999)
    matches_played = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    mvp_awards = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Day(db.Model):
    __tablename__ = 'days'
    id = db.Column(db.Integer, primary_key=True)
    day_date = db.Column(db.Date, unique=True, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(20), default='active')
    mvp_player_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    top_scorer_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    top_wicket_taker_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    teams = db.relationship('DailyTeam', backref='day', lazy='dynamic')
    matches = db.relationship('Match', backref='day', lazy='dynamic')


class DailyTeam(db.Model):
    __tablename__ = 'daily_teams'
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey('days.id'), nullable=False)
    team_label = db.Column(db.String(10), nullable=False)
    team_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    players = db.relationship('TeamPlayer', backref='team', lazy='dynamic')


class TeamPlayer(db.Model):
    __tablename__ = 'team_players'
    id = db.Column(db.Integer, primary_key=True)
    daily_team_id = db.Column(db.Integer, db.ForeignKey('daily_teams.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)


class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey('days.id'), nullable=False)
    match_number = db.Column(db.Integer, nullable=False)
    team_a_id = db.Column(db.Integer, db.ForeignKey('daily_teams.id'), nullable=False)
    team_b_id = db.Column(db.Integer, db.ForeignKey('daily_teams.id'), nullable=False)
    toss_winner = db.Column(db.String(10))
    batting_first = db.Column(db.String(10))
    total_overs = db.Column(db.Integer, default=10)
    status = db.Column(db.String(20), default='upcoming')
    winner = db.Column(db.String(10))
    win_margin = db.Column(db.Integer, default=0)
    win_type = db.Column(db.String(20))
    team_a_win_prob = db.Column(db.Numeric(5, 2), default=50.00)
    team_b_win_prob = db.Column(db.Numeric(5, 2), default=50.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    innings = db.relationship('Innings', backref='match', lazy='dynamic')


class Innings(db.Model):
    __tablename__ = 'innings'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    innings_number = db.Column(db.Integer, nullable=False)
    batting_team_id = db.Column(db.Integer, db.ForeignKey('daily_teams.id'), nullable=False)
    bowling_team_id = db.Column(db.Integer, db.ForeignKey('daily_teams.id'), nullable=False)
    total_runs = db.Column(db.Integer, default=0)
    total_wickets = db.Column(db.Integer, default=0)
    total_balls = db.Column(db.Integer, default=0)
    total_extras = db.Column(db.Integer, default=0)
    wides = db.Column(db.Integer, default=0)
    no_balls = db.Column(db.Integer, default=0)
    byes = db.Column(db.Integer, default=0)
    leg_byes = db.Column(db.Integer, default=0)
    current_striker_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    current_non_striker_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    current_bowler_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    status = db.Column(db.String(20), default='live')
    completed_at = db.Column(db.DateTime)
    balls = db.relationship('BallByBall', backref='innings_ref', lazy='dynamic')


class BallByBall(db.Model):
    __tablename__ = 'ball_by_ball'
    id = db.Column(db.Integer, primary_key=True)
    innings_id = db.Column(db.Integer, db.ForeignKey('innings.id'), nullable=False)
    over_number = db.Column(db.Integer, nullable=False)
    ball_number = db.Column(db.Integer, nullable=False)
    delivery_number = db.Column(db.Integer, nullable=False)
    striker_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    non_striker_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    bowler_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    runs_off_bat = db.Column(db.Integer, default=0)
    extra_runs = db.Column(db.Integer, default=0)
    extra_type = db.Column(db.String(20))
    total_runs = db.Column(db.Integer, default=0)
    is_wicket = db.Column(db.Boolean, default=False)
    wicket_type = db.Column(db.String(30))
    dismissed_player_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    fielder_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    strike_changed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BatsmanInnings(db.Model):
    __tablename__ = 'batsman_innings'
    id = db.Column(db.Integer, primary_key=True)
    innings_id = db.Column(db.Integer, db.ForeignKey('innings.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    batting_order = db.Column(db.Integer)
    runs = db.Column(db.Integer, default=0)
    balls = db.Column(db.Integer, default=0)
    fours = db.Column(db.Integer, default=0)
    sixes = db.Column(db.Integer, default=0)
    singles = db.Column(db.Integer, default=0)
    doubles = db.Column(db.Integer, default=0)
    triples = db.Column(db.Integer, default=0)
    is_out = db.Column(db.Boolean, default=False)
    dismissal_type = db.Column(db.String(30))
    bowler_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BowlerInnings(db.Model):
    __tablename__ = 'bowler_innings'
    id = db.Column(db.Integer, primary_key=True)
    innings_id = db.Column(db.Integer, db.ForeignKey('innings.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    overs_bowled = db.Column(db.Numeric(4, 1), default=0)
    balls_bowled = db.Column(db.Integer, default=0)
    runs_conceded = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)
    wides = db.Column(db.Integer, default=0)
    no_balls = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)