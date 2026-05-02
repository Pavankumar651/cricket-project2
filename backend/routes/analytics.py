"""
Fixed Analytics - Orange Cap and Purple Cap CAN be same person (correct cricket rule)
but they show separate awards. Also fixed head-to-head and allrounder ranking.
"""
from flask import Blueprint, jsonify
from backend.app import db
from backend.models.models import Match, Player, PlayerCareerStats, Innings

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/orange-cap', methods=['GET'])
def orange_cap():
    """Top 5 run scorers. One player can hold Orange Cap."""
    result = db.session.query(
        Player.id, Player.name,
        PlayerCareerStats.total_runs,
        PlayerCareerStats.matches_batted,
        PlayerCareerStats.highest_score,
        PlayerCareerStats.balls_faced,
        PlayerCareerStats.times_out,
    ).join(PlayerCareerStats, Player.id == PlayerCareerStats.player_id
    ).filter(Player.is_active == True
    ).order_by(PlayerCareerStats.total_runs.desc()).limit(5).all()

    out = []
    for i, r in enumerate(result):
        avg = round(r[2] / r[6], 1) if r[6] > 0 else r[2]
        sr  = round(r[2] / r[5] * 100, 1) if r[5] > 0 else 0
        out.append({
            'rank'   : i + 1,
            'id'     : r[0],
            'name'   : r[1],
            'runs'   : r[2],
            'matches': r[3],
            'highest': r[4],
            'average': avg,
            'sr'     : sr,
        })
    return jsonify(out)


@analytics_bp.route('/purple-cap', methods=['GET'])
def purple_cap():
    """Top 5 wicket takers. Can be same person as orange cap – that's cricket."""
    result = db.session.query(
        Player.id, Player.name,
        PlayerCareerStats.wickets,
        PlayerCareerStats.matches_bowled,
        PlayerCareerStats.best_wickets,
        PlayerCareerStats.best_runs,
        PlayerCareerStats.runs_conceded,
        PlayerCareerStats.balls_bowled,
    ).join(PlayerCareerStats, Player.id == PlayerCareerStats.player_id
    ).filter(Player.is_active == True
    ).order_by(
        PlayerCareerStats.wickets.desc(),
        PlayerCareerStats.runs_conceded.asc()     # tiebreak: fewer runs = better
    ).limit(5).all()

    out = []
    for i, r in enumerate(result):
        econ = round(r[6] / (r[7] / 6), 2) if r[7] > 0 else 0
        out.append({
            'rank'   : i + 1,
            'id'     : r[0],
            'name'   : r[1],
            'wickets': r[2],
            'matches': r[3],
            'best'   : f"{r[4]}/{r[5]}" if r[4] > 0 else '—',
            'economy': econ,
        })
    return jsonify(out)


@analytics_bp.route('/mvp-all-time', methods=['GET'])
def mvp_all_time():
    result = db.session.query(
        Player.id, Player.name,
        PlayerCareerStats.mvp_awards,
        PlayerCareerStats.matches_played,
    ).join(PlayerCareerStats, Player.id == PlayerCareerStats.player_id
    ).order_by(PlayerCareerStats.mvp_awards.desc()).limit(5).all()

    return jsonify([{
        'rank': i+1, 'id': r[0], 'name': r[1],
        'mvp_awards': r[2], 'matches': r[3]
    } for i, r in enumerate(result)])


@analytics_bp.route('/best-allrounder', methods=['GET'])
def best_allrounder():
    """Best allrounder: (runs * 0.6) + (wickets * 15 * 0.4) composite score."""
    result = db.session.query(
        Player.id, Player.name,
        PlayerCareerStats.total_runs,
        PlayerCareerStats.wickets,
        PlayerCareerStats.matches_played,
    ).join(PlayerCareerStats, Player.id == PlayerCareerStats.player_id
    ).filter(Player.is_active == True).all()

    scores = sorted([{
        'id'     : r[0],
        'name'   : r[1],
        'runs'   : r[2],
        'wickets': r[3],
        'matches': r[4],
        'score'  : round(r[2] * 0.6 + r[3] * 15 * 0.4, 1),
    } for r in result], key=lambda x: x['score'], reverse=True)

    for i, s in enumerate(scores[:5]):
        s['rank'] = i + 1
    return jsonify(scores[:5])


@analytics_bp.route('/head-to-head', methods=['GET'])
def head_to_head():
    matches = Match.query.filter_by(status='completed').all()
    return jsonify({
        'total_matches': len(matches),
        'team_a_wins'  : sum(1 for m in matches if m.winner == 'A'),
        'team_b_wins'  : sum(1 for m in matches if m.winner == 'B'),
        'ties'         : sum(1 for m in matches if m.winner == 'tie'),
    })


@analytics_bp.route('/day-summary/<int:day_id>', methods=['GET'])
def day_summary(day_id):
    """Day MVP, top scorer, top wicket taker."""
    from backend.models.models import Day, BatsmanInnings, BowlerInnings
    day = Day.query.get_or_404(day_id)

    player_runs    = {}
    player_wickets = {}

    for m in Match.query.filter_by(day_id=day_id, status='completed').all():
        for inn in Innings.query.filter_by(match_id=m.id).all():
            for bi in BatsmanInnings.query.filter_by(innings_id=inn.id).all():
                player_runs[bi.player_id] = player_runs.get(bi.player_id, 0) + bi.runs
            for bwi in BowlerInnings.query.filter_by(innings_id=inn.id).all():
                player_wickets[bwi.player_id] = player_wickets.get(bwi.player_id, 0) + bwi.wickets

    def pid_to_name(pid):
        p = Player.query.get(pid)
        return p.name if p else '?'

    top_scorer_id  = max(player_runs,    key=player_runs.get)    if player_runs    else None
    top_wicket_id  = max(player_wickets, key=player_wickets.get) if player_wickets else None

    # MVP: combined score
    all_pids = set(list(player_runs.keys()) + list(player_wickets.keys()))
    mvp_score = {pid: player_runs.get(pid, 0) * 0.6 + player_wickets.get(pid, 0) * 15 * 0.4
                 for pid in all_pids}
    mvp_id = max(mvp_score, key=mvp_score.get) if mvp_score else None

    return jsonify({
        'mvp'        : {'id': mvp_id,       'name': pid_to_name(mvp_id)}       if mvp_id       else None,
        'top_scorer' : {'id': top_scorer_id, 'name': pid_to_name(top_scorer_id),
                        'runs': player_runs.get(top_scorer_id, 0)}              if top_scorer_id else None,
        'top_wickets': {'id': top_wicket_id, 'name': pid_to_name(top_wicket_id),
                        'wickets': player_wickets.get(top_wicket_id, 0)}        if top_wicket_id else None,
    })