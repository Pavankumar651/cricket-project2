"""
Fixed Players Routes - Correct stats, Orange Cap, Purple Cap separate
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from backend.app import db
from backend.models.models import (
    Player, PlayerCareerStats, BatsmanInnings, BowlerInnings, Innings, Match
)

players_bp = Blueprint('players', __name__)


@players_bp.route('/', methods=['GET'])
def get_all_players():
    players = Player.query.filter_by(is_active=True).order_by(Player.id).all()
    result = []
    for p in players:
        cs = p.career_stats
        avg = 0
        if cs and cs.times_out > 0:
            avg = round(cs.total_runs / cs.times_out, 1)
        elif cs:
            avg = cs.total_runs
        result.append({
            'id'  : p.id,
            'name': p.name,
            'role': p.role,
            'career': {
                'matches' : cs.matches_played  if cs else 0,
                'runs'    : cs.total_runs       if cs else 0,
                'wickets' : cs.wickets          if cs else 0,
                'highest' : cs.highest_score   if cs else 0,
                'avg'     : avg,
                'sr'      : round(cs.total_runs / cs.balls_faced * 100, 1) if cs and cs.balls_faced > 0 else 0,
            }
        })
    return jsonify(result)


@players_bp.route('/<int:player_id>', methods=['GET'])
def get_player_profile(player_id):
    player = Player.query.get_or_404(player_id)
    cs = player.career_stats

    # Batting average
    bat_avg = 0
    if cs and cs.times_out > 0:
        bat_avg = round(cs.total_runs / cs.times_out, 2)
    elif cs:
        bat_avg = cs.total_runs

    # Bowling average
    bowl_avg = None
    if cs and cs.wickets > 0:
        bowl_avg = round(cs.runs_conceded / cs.wickets, 2)

    # Strike rate
    sr = round(cs.total_runs / cs.balls_faced * 100, 2) if cs and cs.balls_faced > 0 else 0

    # Economy
    econ = round(cs.runs_conceded / (cs.balls_bowled / 6), 2) if cs and cs.balls_bowled > 0 else 0

    # Overs bowled display
    overs_display = f"{cs.balls_bowled // 6}.{cs.balls_bowled % 6}" if cs else "0.0"

    # Last 5 innings scores
    recent = BatsmanInnings.query.join(
        Innings, BatsmanInnings.innings_id == Innings.id
    ).join(Match, Innings.match_id == Match.id).filter(
        BatsmanInnings.player_id == player_id
    ).order_by(Match.created_at.desc()).limit(5).all()

    recent_scores = [r.runs for r in recent]
    avg_recent    = sum(recent_scores) / len(recent_scores) if recent_scores else 0
    form = 'Hot Form' if avg_recent >= 25 else ('Average Form' if avg_recent >= 12 else 'Poor Form')

    # Last 5 bowling figures
    recent_bowl = BowlerInnings.query.join(
        Innings, BowlerInnings.innings_id == Innings.id
    ).join(Match, Innings.match_id == Match.id).filter(
        BowlerInnings.player_id == player_id
    ).order_by(Match.created_at.desc()).limit(5).all()

    return jsonify({
        'id'  : player.id,
        'name': player.name,
        'role': player.role,
        'batting': {
            'total_runs'    : cs.total_runs      if cs else 0,
            'balls_faced'   : cs.balls_faced     if cs else 0,
            'matches'       : cs.matches_batted  if cs else 0,
            'highest_score' : cs.highest_score   if cs else 0,
            'average'       : bat_avg,
            'strike_rate'   : sr,
            'fours'         : cs.fours           if cs else 0,
            'sixes'         : cs.sixes           if cs else 0,
            'singles'       : cs.singles         if cs else 0,
            'doubles'       : cs.doubles         if cs else 0,
            'triples'       : cs.triples         if cs else 0,
            'times_out'     : cs.times_out       if cs else 0,
        },
        'bowling': {
            'matches'       : cs.matches_bowled  if cs else 0,
            'overs'         : overs_display,
            'balls'         : cs.balls_bowled    if cs else 0,
            'runs'          : cs.runs_conceded   if cs else 0,
            'wickets'       : cs.wickets         if cs else 0,
            'economy'       : econ,
            'average'       : bowl_avg,
            'best'          : f"{cs.best_wickets}/{cs.best_runs}" if cs and cs.best_wickets > 0 else '—',
        },
        'overall': {
            'matches_played': cs.matches_played  if cs else 0,
            'wins'          : cs.wins            if cs else 0,
            'mvp_awards'    : cs.mvp_awards      if cs else 0,
        },
        'recent_form': {
            'form'          : form,
            'last_5_scores' : recent_scores,
            'last_5_bowling': [f"{b.wickets}/{b.runs_conceded}" for b in recent_bowl],
        }
    })


@players_bp.route('/add', methods=['POST'])
@login_required
def add_player():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    if Player.query.filter_by(name=name).first():
        return jsonify({'error': 'Player already exists'}), 400
    p  = Player(name=name, role='All Rounder')
    db.session.add(p)
    db.session.commit()
    cs = PlayerCareerStats(player_id=p.id)
    db.session.add(cs)
    db.session.commit()
    return jsonify({'success': True, 'id': p.id, 'name': p.name})


@players_bp.route('/leaderboard/weekly', methods=['GET'])
def weekly_leaderboard():
    from sqlalchemy import text
    try:
        result = db.session.execute(text("SELECT * FROM v_weekly_leaderboard")).fetchall()
        return jsonify([dict(r._mapping) for r in result])
    except Exception:
        return jsonify([])


@players_bp.route('/leaderboard/monthly', methods=['GET'])
def monthly_leaderboard():
    from sqlalchemy import text
    try:
        result = db.session.execute(text("SELECT * FROM v_monthly_leaderboard")).fetchall()
        return jsonify([dict(r._mapping) for r in result])
    except Exception:
        return jsonify([])