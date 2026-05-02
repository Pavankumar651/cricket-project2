"""
Machine Learning Module - Team Win Probability Prediction
Uses Scikit-learn with player performance features
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'win_predictor.pkl')
SCALER_PATH = os.path.join(os.path.dirname(__file__), 'scaler.pkl')


def extract_team_features(player_ids):
    """
    Extract features for a team based on player career stats.
    Returns a feature vector for ML prediction.
    """
    from backend.models.models import PlayerCareerStats
    
    total_runs = 0
    total_balls_faced = 0
    total_wickets = 0
    total_balls_bowled = 0
    total_matches = 0
    win_rate = 0
    avg_sr = 0
    avg_economy = 0
    mvp_count = 0

    for pid in player_ids:
        cs = PlayerCareerStats.query.get(pid)
        if cs:
            total_runs += cs.total_runs
            total_balls_faced += cs.balls_faced
            total_wickets += cs.wickets
            total_balls_bowled += cs.balls_bowled
            total_matches += cs.matches_played
            win_rate += (cs.wins / cs.matches_played) if cs.matches_played > 0 else 0.5
            mvp_count += cs.mvp_awards

    n = len(player_ids) if player_ids else 1
    avg_sr = (total_runs / total_balls_faced * 100) if total_balls_faced > 0 else 50
    avg_economy = (total_runs / (total_balls_bowled / 6)) if total_balls_bowled > 0 else 8
    avg_win_rate = win_rate / n

    return [
        total_runs / n,           # avg runs per player
        avg_sr,                   # team batting strike rate
        total_wickets / n,        # avg wickets per player
        avg_economy,              # team bowling economy
        avg_win_rate,             # historical win rate
        mvp_count / n,            # MVP per player
        total_matches / n,        # experience
    ]


def predict_win_probability(team_a_ids, team_b_ids):
    """
    Predict win probability for both teams.
    Returns {'team_a': float, 'team_b': float}
    """
    feat_a = extract_team_features(team_a_ids)
    feat_b = extract_team_features(team_b_ids)

    # Relative features (A vs B)
    features = [
        feat_a[0] - feat_b[0],   # runs advantage
        feat_a[1] - feat_b[1],   # SR advantage
        feat_a[2] - feat_b[2],   # wicket advantage
        feat_b[3] - feat_a[3],   # economy advantage (lower is better for bowling team)
        feat_a[4] - feat_b[4],   # win rate advantage
        feat_a[5] - feat_b[5],   # MVP advantage
        feat_a[6] - feat_b[6],   # experience advantage
    ]

    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            scaler = joblib.load(SCALER_PATH)
            X = scaler.transform([features])
            prob = model.predict_proba(X)[0]
            team_a_prob = round(prob[1] * 100, 1)
            team_b_prob = round((1 - prob[1]) * 100, 1)
            return {'team_a': team_a_prob, 'team_b': team_b_prob}
        except Exception:
            pass

    # Fallback: weighted heuristic
    team_a_prob = _heuristic_probability(feat_a, feat_b)
    team_b_prob = round(100 - team_a_prob, 1)
    return {'team_a': team_a_prob, 'team_b': team_b_prob}


def _heuristic_probability(feat_a, feat_b):
    """Simple weighted heuristic when ML model not trained yet"""
    weights = [0.3, 0.2, 0.25, 0.1, 0.1, 0.05]
    score_a = 0
    score_b = 0

    comparisons = [
        (feat_a[0], feat_b[0]),   # runs
        (feat_a[1], feat_b[1]),   # SR
        (feat_a[2], feat_b[2]),   # wickets
        (feat_b[3], feat_a[3]),   # economy (inverted)
        (feat_a[4], feat_b[4]),   # win rate
        (feat_a[5], feat_b[5]),   # MVP
    ]

    for i, (a_val, b_val) in enumerate(comparisons):
        total = a_val + b_val
        if total == 0:
            score_a += 0.5 * weights[i]
            score_b += 0.5 * weights[i]
        else:
            score_a += (a_val / total) * weights[i]
            score_b += (b_val / total) * weights[i]

    total_score = score_a + score_b
    prob_a = round((score_a / total_score) * 100, 1) if total_score > 0 else 50.0
    return prob_a


def train_model_from_history():
    """
    Train ML model from historical match data.
    Called when enough data is available (>= 20 matches).
    """
    from backend.models.models import Match, TeamPlayer
    
    matches = Match.query.filter_by(status='completed').all()
    if len(matches) < 20:
        return {'trained': False, 'reason': f'Need at least 20 matches. Have {len(matches)}.'}

    X = []
    y = []

    for m in matches:
        if not m.winner:
            continue
        team_a_players = [tp.player_id for tp in TeamPlayer.query.filter_by(daily_team_id=m.team_a_id).all()]
        team_b_players = [tp.player_id for tp in TeamPlayer.query.filter_by(daily_team_id=m.team_b_id).all()]

        feat_a = extract_team_features(team_a_players)
        feat_b = extract_team_features(team_b_players)

        features = [a - b for a, b in zip(feat_a, feat_b)]
        features[3] = feat_b[3] - feat_a[3]  # economy: B-A (lower is better)

        X.append(features)
        y.append(1 if m.winner == 'A' else 0)

    X = np.array(X)
    y = np.array(y)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    return {'trained': True, 'matches_used': len(X)}


def get_player_form(player_id, last_n=5):
    """Returns form indicator for a player based on last N matches"""
    from backend.models.models import BatsmanInnings, Innings, Match
    
    recent = db.session.query(BatsmanInnings).join(
        Innings, BatsmanInnings.innings_id == Innings.id
    ).join(Match, Innings.match_id == Match.id).filter(
        BatsmanInnings.player_id == player_id
    ).order_by(Match.created_at.desc()).limit(last_n).all()

    if not recent:
        return {'form': 'No Data', 'avg': 0, 'matches': 0}

    avg_runs = sum(r.runs for r in recent) / len(recent)
    form = 'Hot Form' if avg_runs >= 25 else ('Average Form' if avg_runs >= 12 else 'Poor Form')

    return {
        'form': form,
        'avg': round(avg_runs, 1),
        'matches': len(recent),
        'scores': [r.runs for r in recent]
    }