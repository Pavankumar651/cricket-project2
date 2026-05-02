from flask import Blueprint, request, jsonify
from flask_login import login_required
from backend.app import db
from backend.models.models import Match, Innings, TeamPlayer, Player, BowlerInnings
from backend.utils.scoring_engine import ScoringEngine

scoring_bp = Blueprint('scoring', __name__)


def drop_triggers():
    from sqlalchemy import text
    for t in ["after_ball_insert", "after_ball_batsman", "after_ball_bowler"]:
        db.session.execute(text(f"DROP TRIGGER IF EXISTS {t} ON ball_by_ball;"))
    db.session.commit()


@scoring_bp.route('/start-innings', methods=['POST'])
@login_required
def start_innings():
    data = request.json
    match_id       = int(data['match_id'])
    innings_number = int(data['innings_number'])
    striker_id     = int(data['striker_id'])
    non_striker_id = int(data['non_striker_id'])
    bowler_id      = int(data['bowler_id'])

    if striker_id == non_striker_id:
        return jsonify({'error': 'Striker and Non-Striker must be different'}), 400

    match = db.session.get(Match, match_id)
    if not match:
        return jsonify({'error': 'Match not found'}), 404

    existing = Innings.query.filter_by(match_id=match_id, innings_number=innings_number).first()
    if existing:
        return jsonify({'success': True, 'innings_id': existing.id})

    if innings_number == 1:
        batting_team_id = match.team_a_id if match.batting_first == 'A' else match.team_b_id
        bowling_team_id = match.team_b_id if match.batting_first == 'A' else match.team_a_id
    else:
        inn1 = Innings.query.filter_by(match_id=match_id, innings_number=1).first()
        if not inn1:
            return jsonify({'error': 'Innings 1 not found'}), 400
        batting_team_id = inn1.bowling_team_id
        bowling_team_id = inn1.batting_team_id

    innings = Innings(
        match_id=match_id,
        innings_number=innings_number,
        batting_team_id=batting_team_id,
        bowling_team_id=bowling_team_id,
        current_striker_id=striker_id,
        current_non_striker_id=non_striker_id,
        current_bowler_id=bowler_id,
        status='live',
    )
    db.session.add(innings)
    match.status = 'live' if innings_number == 1 else 'innings2'
    db.session.commit()

    try:
        drop_triggers()
    except Exception:
        pass

    return jsonify({'success': True, 'innings_id': innings.id})


@scoring_bp.route('/record-ball', methods=['POST'])
@login_required
def record_ball():
    data = request.json
    innings_id = int(data['innings_id'])

    innings = db.session.get(Innings, innings_id)
    if not innings:
        return jsonify({'error': 'Innings not found'}), 404
    if innings.status != 'live':
        return jsonify({'error': 'Innings is not live'}), 400

    bowler_id = int(data['bowler_id'])
    if not ScoringEngine.can_bowler_bowl(innings_id, bowler_id):
        return jsonify({'error': 'Bowler 2-over limit reached', 'code': 'BOWLER_LIMIT'}), 400

    result = ScoringEngine.record_ball(innings_id, data)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@scoring_bp.route('/scorecard/<int:match_id>', methods=['GET'])
def get_scorecard(match_id):
    innings = (
        Innings.query.filter_by(match_id=match_id, status='live').first() or
        Innings.query.filter_by(match_id=match_id).order_by(Innings.innings_number.desc()).first()
    )
    if not innings:
        return jsonify({'error': 'No innings found'}), 404
    sc = ScoringEngine.get_scorecard(innings.id)
    return jsonify(sc) if sc else (jsonify({'error': 'Scorecard error'}), 500)


@scoring_bp.route('/scorecard-innings/<int:innings_id>', methods=['GET'])
def scorecard_by_innings(innings_id):
    sc = ScoringEngine.get_scorecard(innings_id)
    return jsonify(sc) if sc else (jsonify({'error': 'Not found'}), 404)


@scoring_bp.route('/full-scorecard/<int:match_id>', methods=['GET'])
def full_scorecard(match_id):
    return jsonify(ScoringEngine.get_match_scorecard(match_id))


@scoring_bp.route('/set-new-batsman', methods=['POST'])
@login_required
def set_new_batsman():
    data = request.json
    innings = db.session.get(Innings, int(data['innings_id']))
    if not innings:
        return jsonify({'error': 'Innings not found'}), 404
    pid = int(data['new_batsman_id'])
    if data['position'] == 'striker':
        innings.current_striker_id = pid
    else:
        innings.current_non_striker_id = pid
    db.session.commit()
    return jsonify({'success': True,
                    'striker_id': innings.current_striker_id,
                    'non_striker_id': innings.current_non_striker_id})


@scoring_bp.route('/set-new-bowler', methods=['POST'])
@login_required
def set_new_bowler():
    data = request.json
    innings   = db.session.get(Innings, int(data['innings_id']))
    bowler_id = int(data['bowler_id'])
    if not innings:
        return jsonify({'error': 'Innings not found'}), 404
    if not ScoringEngine.can_bowler_bowl(innings.id, bowler_id):
        return jsonify({'error': 'Bowler 2-over limit', 'code': 'BOWLER_LIMIT'}), 400

    innings.current_bowler_id = bowler_id
    # Over-end strike rotation
    innings.current_striker_id, innings.current_non_striker_id = (
        innings.current_non_striker_id, innings.current_striker_id
    )
    db.session.commit()
    return jsonify({
        'success'           : True,
        'new_striker_id'    : innings.current_striker_id,
        'new_non_striker_id': innings.current_non_striker_id,
    })


@scoring_bp.route('/bowler-status/<int:innings_id>', methods=['GET'])
def bowler_status(innings_id):
    innings = db.session.get(Innings, innings_id)
    if not innings:
        return jsonify([])
    out = []
    for tp in TeamPlayer.query.filter_by(daily_team_id=innings.bowling_team_id).all():
        p   = Player.query.get(tp.player_id)
        bwi = BowlerInnings.query.filter_by(innings_id=innings_id, player_id=tp.player_id).first()
        balls = bwi.balls_bowled if bwi else 0
        out.append({
            'player_id'   : tp.player_id,
            'name'        : p.name,
            'overs_bowled': balls // 6,
            'balls_extra' : balls % 6,
            'can_bowl'    : balls < 12,
            'is_current'  : tp.player_id == innings.current_bowler_id,
        })
    return jsonify(out)


@scoring_bp.route('/complete-match', methods=['POST'])
@login_required
def complete_match():
    data = request.json
    result = ScoringEngine.complete_match(int(data['match_id']))
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@scoring_bp.route('/undo-ball', methods=['POST'])
@login_required
def undo_ball():
    data = request.json
    result = ScoringEngine.undo_last_ball(int(data['innings_id']))
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@scoring_bp.route('/live', methods=['GET'])
def get_live():
    innings = Innings.query.filter_by(status='live').order_by(Innings.id.desc()).first()
    if not innings:
        return jsonify({'live': False})
    sc = ScoringEngine.get_scorecard(innings.id)
    if not sc:
        return jsonify({'live': False})
    sc['live']     = True
    sc['match_id'] = innings.match_id
    return jsonify(sc)