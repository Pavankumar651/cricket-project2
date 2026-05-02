"""
Matches Routes - Team selection, match management
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from backend.app import db
from backend.models.models import (
    Match, Day, DailyTeam, TeamPlayer, Player, Innings
)
from backend.ml.predictor import predict_win_probability
from datetime import date, datetime

matches_bp = Blueprint('matches', __name__)


@matches_bp.route('/today', methods=['GET'])
def get_today():
    """Get or create today's day session"""
    today = date.today()
    day = Day.query.filter_by(day_date=today).first()
    if not day:
        return jsonify({'day': None, 'teams': None, 'matches': []})

    teams = DailyTeam.query.filter_by(day_id=day.id).all()
    team_data = {}
    for t in teams:
        players = TeamPlayer.query.filter_by(daily_team_id=t.id).all()
        team_data[t.team_label] = {
            'id': t.id,
            'label': t.team_label,
            'players': [
                {'id': p.player_id, 'name': Player.query.get(p.player_id).name}
                for p in players
            ]
        }

    matches = Match.query.filter_by(day_id=day.id).order_by(Match.match_number).all()

    return jsonify({
        'day': {'id': day.id, 'date': str(day.day_date), 'status': day.status},
        'teams': team_data,
        'matches': [
            {
                'id': m.id,
                'match_number': m.match_number,
                'status': m.status,
                'batting_first': m.batting_first,
                'winner': m.winner,
                'team_a_prob': float(m.team_a_win_prob),
                'team_b_prob': float(m.team_b_win_prob),
            }
            for m in matches
        ]
    })


@matches_bp.route('/start-day', methods=['POST'])
@login_required
def start_day():
    """Start a new day session"""
    today = date.today()
    existing = Day.query.filter_by(day_date=today).first()
    if existing:
        return jsonify({'error': 'Day already started', 'day_id': existing.id}), 400

    day = Day(day_date=today)
    db.session.add(day)
    db.session.flush()

    team_a = DailyTeam(day_id=day.id, team_label='A')
    team_b = DailyTeam(day_id=day.id, team_label='B')
    db.session.add_all([team_a, team_b])
    db.session.commit()

    return jsonify({'success': True, 'day_id': day.id})


@matches_bp.route('/select-team', methods=['POST'])
@login_required
def select_team():
    """Select players for a team"""
    data = request.json
    day_id = data['day_id']
    team_label = data['team_label']
    player_ids = data['player_ids']

    team = DailyTeam.query.filter_by(day_id=day_id, team_label=team_label).first()
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    # Check no player is in the other team
    other_label = 'B' if team_label == 'A' else 'A'
    other_team = DailyTeam.query.filter_by(day_id=day_id, team_label=other_label).first()
    if other_team:
        other_players = {tp.player_id for tp in TeamPlayer.query.filter_by(daily_team_id=other_team.id).all()}
        conflict = set(player_ids) & other_players
        if conflict:
            names = [Player.query.get(pid).name for pid in conflict]
            return jsonify({'error': f'Players already in other team: {", ".join(names)}'}), 400

    # Clear existing selection
    TeamPlayer.query.filter_by(daily_team_id=team.id).delete()

    for pid in player_ids:
        tp = TeamPlayer(daily_team_id=team.id, player_id=pid)
        db.session.add(tp)

    db.session.commit()
    return jsonify({'success': True})


@matches_bp.route('/create-match', methods=['POST'])
@login_required
def create_match():
    """Create a new match for today"""
    data = request.json
    day_id = data['day_id']
    toss_winner = data['toss_winner']
    batting_first = data['batting_first']
    total_overs = data.get('total_overs', 10)

    day = Day.query.get_or_404(day_id)
    match_count = Match.query.filter_by(day_id=day_id).count()

    team_a = DailyTeam.query.filter_by(day_id=day_id, team_label='A').first()
    team_b = DailyTeam.query.filter_by(day_id=day_id, team_label='B').first()

    if not team_a or not team_b:
        return jsonify({'error': 'Teams not set up'}), 400

    # Get player IDs for ML prediction
    team_a_ids = [tp.player_id for tp in TeamPlayer.query.filter_by(daily_team_id=team_a.id).all()]
    team_b_ids = [tp.player_id for tp in TeamPlayer.query.filter_by(daily_team_id=team_b.id).all()]

    probs = predict_win_probability(team_a_ids, team_b_ids)

    match = Match(
        day_id=day_id,
        match_number=match_count + 1,
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        toss_winner=toss_winner,
        batting_first=batting_first,
        total_overs=total_overs,
        status='live',
        team_a_win_prob=probs['team_a'],
        team_b_win_prob=probs['team_b']
    )
    db.session.add(match)
    db.session.commit()

    return jsonify({
        'success': True,
        'match_id': match.id,
        'match_number': match.match_number,
        'predictions': probs
    })


@matches_bp.route('/<int:match_id>', methods=['GET'])
def get_match(match_id):
    m = Match.query.get_or_404(match_id)
    innings = Innings.query.filter_by(match_id=match_id).order_by(Innings.innings_number).all()

    team_a = DailyTeam.query.get(m.team_a_id)
    team_b = DailyTeam.query.get(m.team_b_id)

    return jsonify({
        'id': m.id,
        'match_number': m.match_number,
        'status': m.status,
        'toss_winner': m.toss_winner,
        'batting_first': m.batting_first,
        'total_overs': m.total_overs,
        'winner': m.winner,
        'win_margin': m.win_margin,
        'win_type': m.win_type,
        'team_a': {
            'id': team_a.id,
            'label': 'A',
            'players': [
                {'id': tp.player_id, 'name': Player.query.get(tp.player_id).name}
                for tp in TeamPlayer.query.filter_by(daily_team_id=team_a.id).all()
            ]
        },
        'team_b': {
            'id': team_b.id,
            'label': 'B',
            'players': [
                {'id': tp.player_id, 'name': Player.query.get(tp.player_id).name}
                for tp in TeamPlayer.query.filter_by(daily_team_id=team_b.id).all()
            ]
        },
        'predictions': {
            'team_a': float(m.team_a_win_prob),
            'team_b': float(m.team_b_win_prob)
        },
        'innings': [
            {
                'innings_number': i.innings_number,
                'runs': i.total_runs,
                'wickets': i.total_wickets,
                'overs': f"{i.total_balls // 6}.{i.total_balls % 6}",
                'extras': i.total_extras,
                'status': i.status
            }
            for i in innings
        ]
    })


@matches_bp.route('/end-day', methods=['POST'])
@login_required
def end_day():
    """End today's session and calculate day stats"""
    data = request.json
    day_id = data['day_id']

    day = Day.query.get_or_404(day_id)
    matches = Match.query.filter_by(day_id=day_id, status='completed').all()

    if not matches:
        return jsonify({'error': 'No completed matches today'}), 400

    # Calculate day MVP
    from backend.models.models import BatsmanInnings, BowlerInnings
    from sqlalchemy import func

    player_scores = {}
    player_wickets = {}

    for m in matches:
        for inn in Innings.query.filter_by(match_id=m.id).all():
            for bi in BatsmanInnings.query.filter_by(innings_id=inn.id).all():
                player_scores[bi.player_id] = player_scores.get(bi.player_id, 0) + bi.runs
            for bwi in BowlerInnings.query.filter_by(innings_id=inn.id).all():
                player_wickets[bwi.player_id] = player_wickets.get(bwi.player_id, 0) + bwi.wickets

    top_scorer_id = max(player_scores, key=player_scores.get) if player_scores else None
    top_wicket_id = max(player_wickets, key=player_wickets.get) if player_wickets else None

    # MVP = weighted (runs*0.6 + wickets*10*0.4)
    mvp_scores = {}
    all_players = set(list(player_scores.keys()) + list(player_wickets.keys()))
    for pid in all_players:
        mvp_scores[pid] = (player_scores.get(pid, 0) * 0.6) + (player_wickets.get(pid, 0) * 10 * 0.4)

    mvp_id = max(mvp_scores, key=mvp_scores.get) if mvp_scores else None

    day.top_scorer_id = top_scorer_id
    day.top_wicket_taker_id = top_wicket_id
    day.mvp_player_id = mvp_id
    day.status = 'completed'
    day.completed_at = datetime.utcnow()

    if mvp_id:
        from backend.models.models import PlayerCareerStats
        cs = PlayerCareerStats.query.get(mvp_id)
        if cs:
            cs.mvp_awards += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'mvp': {'id': mvp_id, 'name': Player.query.get(mvp_id).name if mvp_id else None},
        'top_scorer': {'id': top_scorer_id, 'name': Player.query.get(top_scorer_id).name if top_scorer_id else None, 'runs': player_scores.get(top_scorer_id, 0)},
        'top_wicket_taker': {'id': top_wicket_id, 'name': Player.query.get(top_wicket_id).name if top_wicket_id else None, 'wickets': player_wickets.get(top_wicket_id, 0)}
    })


@matches_bp.route('/history', methods=['GET'])
def match_history():
    """All past matches"""
    matches = Match.query.filter_by(status='completed').order_by(Match.created_at.desc()).limit(50).all()
    result = []
    for m in matches:
        innings1 = Innings.query.filter_by(match_id=m.id, innings_number=1).first()
        innings2 = Innings.query.filter_by(match_id=m.id, innings_number=2).first()
        result.append({
            'id': m.id,
            'date': str(m.created_at.date()),
            'match_number': m.match_number,
            'winner': m.winner,
            'win_margin': m.win_margin,
            'win_type': m.win_type,
            'innings1': {'runs': innings1.total_runs, 'wickets': innings1.total_wickets, 'overs': f"{innings1.total_balls//6}.{innings1.total_balls%6}"} if innings1 else None,
            'innings2': {'runs': innings2.total_runs, 'wickets': innings2.total_wickets, 'overs': f"{innings2.total_balls//6}.{innings2.total_balls%6}"} if innings2 else None,
        })
    return jsonify(result)