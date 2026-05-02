"""
FIXED Scoring Engine - No double counting.
ALL updates done in Python. Triggers must be disabled/dropped.
"""
from backend.app import db
from backend.models.models import (
    Innings, BallByBall, BatsmanInnings, BowlerInnings,
    Match, Player, TeamPlayer
)
from datetime import datetime


class ScoringEngine:

    @staticmethod
    def get_live_innings(match_id):
        return Innings.query.filter_by(match_id=match_id, status='live').first()

    @staticmethod
    def can_bowler_bowl(innings_id, bowler_id):
        bwi = BowlerInnings.query.filter_by(innings_id=innings_id, player_id=bowler_id).first()
        return (bwi.balls_bowled if bwi else 0) < 12

    @staticmethod
    def get_batting_players(innings):
        return [r.player_id for r in TeamPlayer.query.filter_by(daily_team_id=innings.batting_team_id).all()]

    @staticmethod
    def _rotate_strike(runs_off_bat, extra_type, is_end_of_over):
        """
        Correct cricket strike rotation:
        - Odd runs off bat = strike rotates
        - End of over: rotate if NOT already rotated (XOR)
        - Wide with odd extra runs: no rotation (batter didn't run off bat)
        """
        run_rotates = (runs_off_bat % 2 == 1)
        if is_end_of_over:
            return not run_rotates   # XOR: net effect after over
        return run_rotates

    @staticmethod
    def record_ball(innings_id, data):
        innings = db.session.get(Innings, innings_id)
        if not innings:
            return {'error': 'Innings not found'}
        if innings.status != 'live':
            return {'error': 'Innings is not live'}

        match = db.session.get(Match, innings.match_id)

        striker_id     = int(data['striker_id'])
        non_striker_id = int(data['non_striker_id'])
        bowler_id      = int(data['bowler_id'])
        runs_off_bat   = int(data.get('runs_off_bat', 0))
        extra_type     = data.get('extra_type') or None
        extra_runs     = int(data.get('extra_runs', 0))
        is_wicket      = bool(data.get('is_wicket', False))
        wicket_type    = data.get('wicket_type') or None
        dismissed_id   = data.get('dismissed_player_id')
        dismissed_id   = int(dismissed_id) if dismissed_id else None

        # Normalize extras
        if extra_type == 'wide':
            runs_off_bat = 0
            if extra_runs == 0: extra_runs = 1
        elif extra_type == 'noball':
            if extra_runs == 0: extra_runs = 1
        elif extra_type in ('bye', 'legbye'):
            if extra_runs == 0: extra_runs = 1

        total_runs = runs_off_bat + extra_runs
        is_legal   = extra_type not in ('wide', 'noball')

        # Over/ball position BEFORE this delivery
        balls_so_far  = innings.total_balls
        over_number   = (balls_so_far // 6) + 1
        ball_in_over  = (balls_so_far % 6) + 1
        will_end_over = is_legal and (ball_in_over == 6)

        delivery_num = BallByBall.query.filter_by(innings_id=innings_id).count() + 1

        rotate = ScoringEngine._rotate_strike(runs_off_bat, extra_type, will_end_over)

        # ── INSERT BALL ──────────────────────────────────
        ball = BallByBall(
            innings_id=innings_id,
            over_number=over_number,
            ball_number=ball_in_over,
            delivery_number=delivery_num,
            striker_id=striker_id,
            non_striker_id=non_striker_id,
            bowler_id=bowler_id,
            runs_off_bat=runs_off_bat,
            extra_runs=extra_runs,
            extra_type=extra_type,
            total_runs=total_runs,
            is_wicket=is_wicket,
            wicket_type=wicket_type,
            dismissed_player_id=dismissed_id,
            strike_changed=rotate,
        )
        db.session.add(ball)
        db.session.flush()

        # ── UPDATE INNINGS ────────────────────────────────
        innings.total_runs   += total_runs
        innings.total_extras += extra_runs
        if is_legal:
            innings.total_balls += 1
        if extra_type == 'wide':
            innings.wides    += 1
        elif extra_type == 'noball':
            innings.no_balls += 1
        elif extra_type == 'bye':
            innings.byes     += extra_runs
        elif extra_type == 'legbye':
            innings.leg_byes += extra_runs
        if is_wicket:
            innings.total_wickets += 1

        # ── UPDATE BATSMAN ────────────────────────────────
        if extra_type != 'wide':
            bi = BatsmanInnings.query.filter_by(innings_id=innings_id, player_id=striker_id).first()
            if not bi:
                order = BatsmanInnings.query.filter_by(innings_id=innings_id).count() + 1
                bi = BatsmanInnings(innings_id=innings_id, player_id=striker_id, batting_order=order)
                db.session.add(bi)
                db.session.flush()
            bi.balls  += 1
            bi.runs   += runs_off_bat
            if runs_off_bat == 4: bi.fours   += 1
            if runs_off_bat == 6: bi.sixes   += 1
            if runs_off_bat == 1: bi.singles += 1
            if runs_off_bat == 2: bi.doubles += 1
            if runs_off_bat == 3: bi.triples += 1
            if is_wicket and dismissed_id == striker_id:
                bi.is_out = True
                bi.dismissal_type = wicket_type
                bi.bowler_id = bowler_id if wicket_type != 'runout' else None

        if is_wicket and dismissed_id and dismissed_id == non_striker_id:
            nbi = BatsmanInnings.query.filter_by(innings_id=innings_id, player_id=non_striker_id).first()
            if not nbi:
                order = BatsmanInnings.query.filter_by(innings_id=innings_id).count() + 1
                nbi = BatsmanInnings(innings_id=innings_id, player_id=non_striker_id, batting_order=order)
                db.session.add(nbi)
                db.session.flush()
            nbi.is_out = True
            nbi.dismissal_type = 'runout'

        # ── UPDATE BOWLER ─────────────────────────────────
        bwi = BowlerInnings.query.filter_by(innings_id=innings_id, player_id=bowler_id).first()
        if not bwi:
            bwi = BowlerInnings(innings_id=innings_id, player_id=bowler_id)
            db.session.add(bwi)
            db.session.flush()
        bwi.runs_conceded += total_runs
        if is_legal:
            bwi.balls_bowled += 1
        if extra_type == 'wide':  bwi.wides    += 1
        if extra_type == 'noball': bwi.no_balls += 1
        if is_wicket and wicket_type != 'runout':
            bwi.wickets += 1

        # ── ROTATE STRIKE ─────────────────────────────────
        if rotate and not is_wicket:
            innings.current_striker_id, innings.current_non_striker_id = (
                innings.current_non_striker_id, innings.current_striker_id
            )
        if is_wicket:
            if dismissed_id == striker_id:
                innings.current_striker_id = None
            elif dismissed_id == non_striker_id:
                innings.current_non_striker_id = None

        # ── COMMIT ───────────────────────────────────────
        db.session.commit()

        # ── CHECK INNINGS END ─────────────────────────────
        db.session.refresh(innings)  # reload committed values
        batting_players = ScoringEngine.get_batting_players(innings)
        max_wickets     = max(len(batting_players) - 1, 1)
        innings_over    = (
            innings.total_balls >= match.total_overs * 6
            or innings.total_wickets >= max_wickets
        )
        if innings_over:
            ScoringEngine.complete_innings(innings_id)

        return {
            'ball_recorded'     : True,
            'over'              : over_number,
            'ball'              : ball_in_over,
            'is_legal'          : is_legal,
            'total_runs'        : innings.total_runs,
            'total_wickets'     : innings.total_wickets,
            'total_balls'       : innings.total_balls,
            'rotate_strike'     : rotate,
            'new_striker_id'    : innings.current_striker_id,
            'new_non_striker_id': innings.current_non_striker_id,
            'is_end_of_over'    : will_end_over,
            'is_innings_over'   : innings_over,
            'is_wicket'         : is_wicket,
            'need_new_batsman'  : is_wicket,
            'need_new_bowler'   : will_end_over and not innings_over,
        }

    @staticmethod
    def undo_last_ball(innings_id):
        innings = db.session.get(Innings, innings_id)
        if not innings:
            return {'error': 'Innings not found'}

        ball = BallByBall.query.filter_by(
            innings_id=innings_id
        ).order_by(BallByBall.id.desc()).first()
        if not ball:
            return {'error': 'No balls to undo'}

        is_legal = ball.extra_type not in ('wide', 'noball')

        # Reverse innings
        innings.total_runs   -= ball.total_runs
        innings.total_extras -= ball.extra_runs
        if is_legal: innings.total_balls -= 1
        if ball.extra_type == 'wide':    innings.wides    -= 1
        elif ball.extra_type == 'noball': innings.no_balls -= 1
        elif ball.extra_type == 'bye':   innings.byes     -= ball.extra_runs
        elif ball.extra_type == 'legbye': innings.leg_byes -= ball.extra_runs
        if ball.is_wicket: innings.total_wickets -= 1

        # Reverse batsman
        if ball.extra_type != 'wide' and is_legal:
            bi = BatsmanInnings.query.filter_by(innings_id=innings_id, player_id=ball.striker_id).first()
            if bi:
                bi.balls  -= 1
                bi.runs   -= ball.runs_off_bat
                if ball.runs_off_bat == 4: bi.fours   -= 1
                if ball.runs_off_bat == 6: bi.sixes   -= 1
                if ball.runs_off_bat == 1: bi.singles -= 1
                if ball.runs_off_bat == 2: bi.doubles -= 1
                if ball.runs_off_bat == 3: bi.triples -= 1
                if ball.is_wicket and ball.dismissed_player_id == ball.striker_id:
                    bi.is_out = False
                    bi.dismissal_type = None
                    bi.bowler_id = None

        # Reverse bowler
        bwi = BowlerInnings.query.filter_by(innings_id=innings_id, player_id=ball.bowler_id).first()
        if bwi:
            bwi.runs_conceded -= ball.total_runs
            if is_legal: bwi.balls_bowled -= 1
            if ball.extra_type == 'wide':    bwi.wides    -= 1
            if ball.extra_type == 'noball':  bwi.no_balls -= 1
            if ball.is_wicket and ball.wicket_type != 'runout':
                bwi.wickets -= 1

        # Restore players
        innings.current_striker_id     = ball.striker_id
        innings.current_non_striker_id = ball.non_striker_id
        innings.current_bowler_id      = ball.bowler_id

        db.session.delete(ball)
        db.session.commit()
        return {'success': True, 'message': 'Last ball undone'}

    @staticmethod
    def complete_innings(innings_id):
        innings = db.session.get(Innings, innings_id)
        if not innings or innings.status == 'completed':
            return
        innings.status       = 'completed'
        innings.completed_at = datetime.utcnow()
        db.session.commit()

        for bi in BatsmanInnings.query.filter_by(innings_id=innings_id).all():
            ScoringEngine._update_career_batting(bi.player_id, bi)
        for bwi in BowlerInnings.query.filter_by(innings_id=innings_id).all():
            ScoringEngine._update_career_bowling(bwi.player_id, bwi)

    @staticmethod
    def _update_career_batting(player_id, bi):
        from backend.models.models import PlayerCareerStats
        cs = PlayerCareerStats.query.get(player_id)
        if not cs:
            cs = PlayerCareerStats(player_id=player_id)
            db.session.add(cs)
        cs.total_runs    += bi.runs
        cs.balls_faced   += bi.balls
        cs.fours         += bi.fours
        cs.sixes         += bi.sixes
        cs.singles       += bi.singles
        cs.doubles       += bi.doubles
        cs.triples       += bi.triples
        cs.matches_batted += 1
        if bi.is_out: cs.times_out += 1
        if bi.runs > cs.highest_score: cs.highest_score = bi.runs
        cs.matches_played = max(cs.matches_played, cs.matches_batted)
        cs.updated_at = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def _update_career_bowling(player_id, bwi):
        from backend.models.models import PlayerCareerStats
        cs = PlayerCareerStats.query.get(player_id)
        if not cs:
            cs = PlayerCareerStats(player_id=player_id)
            db.session.add(cs)
        cs.balls_bowled   += bwi.balls_bowled
        cs.runs_conceded  += bwi.runs_conceded
        cs.wickets        += bwi.wickets
        cs.matches_bowled += 1
        if (bwi.wickets > cs.best_wickets or
                (bwi.wickets == cs.best_wickets and bwi.runs_conceded < cs.best_runs and cs.best_runs != 999)):
            cs.best_wickets = bwi.wickets
            cs.best_runs    = bwi.runs_conceded
        cs.updated_at = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def complete_match(match_id):
        match    = db.session.get(Match, match_id)
        innings1 = Innings.query.filter_by(match_id=match_id, innings_number=1).first()
        innings2 = Innings.query.filter_by(match_id=match_id, innings_number=2).first()
        if not innings1:
            return {'error': 'Innings 1 not found'}

        runs1 = innings1.total_runs
        runs2 = innings2.total_runs if innings2 else 0

        for inn in [innings1, innings2]:
            if inn and inn.status == 'live':
                inn.status = 'completed'
                inn.completed_at = datetime.utcnow()

        if not innings2:
            match.winner = match.batting_first
            match.win_type = 'innings'
            match.win_margin = 0
        elif runs1 > runs2:
            match.winner     = match.batting_first
            match.win_type   = 'runs'
            match.win_margin = runs1 - runs2
        elif runs2 > runs1:
            match.winner     = 'B' if match.batting_first == 'A' else 'A'
            match.win_type   = 'wickets'
            bat2_count = TeamPlayer.query.filter_by(daily_team_id=innings2.batting_team_id).count()
            match.win_margin = (bat2_count - 1) - innings2.total_wickets
        else:
            match.winner = 'tie'
            match.win_type = 'tie'
            match.win_margin = 0

        match.status       = 'completed'
        match.completed_at = datetime.utcnow()
        db.session.commit()

        # Update wins
        if match.winner not in ('tie', None):
            winning_team_id = match.team_a_id if match.winner == 'A' else match.team_b_id
            from backend.models.models import PlayerCareerStats
            for w in TeamPlayer.query.filter_by(daily_team_id=winning_team_id).all():
                cs = PlayerCareerStats.query.get(w.player_id)
                if cs: cs.wins += 1
            db.session.commit()

        return {
            'success'   : True,
            'winner'    : match.winner,
            'win_type'  : match.win_type,
            'win_margin': match.win_margin,
            'team1_runs': runs1,
            'team2_runs': runs2,
        }

    @staticmethod
    def get_scorecard(innings_id):
        innings = db.session.get(Innings, innings_id)
        if not innings: return None

        match       = db.session.get(Match, innings.match_id)
        batsmen_rows = BatsmanInnings.query.filter_by(innings_id=innings_id).order_by(BatsmanInnings.batting_order).all()
        bowler_rows  = BowlerInnings.query.filter_by(innings_id=innings_id).all()

        striker     = db.session.get(Player, innings.current_striker_id)     if innings.current_striker_id     else None
        non_striker = db.session.get(Player, innings.current_non_striker_id) if innings.current_non_striker_id else None
        bowler      = db.session.get(Player, innings.current_bowler_id)      if innings.current_bowler_id      else None

        current_over_num = (innings.total_balls // 6) + 1
        over_ball_rows   = BallByBall.query.filter_by(
            innings_id=innings_id, over_number=current_over_num
        ).order_by(BallByBall.id.asc()).all()

        current_over_balls = []
        for b in over_ball_rows:
            if b.is_wicket:                                 current_over_balls.append('W')
            elif b.extra_type == 'wide':                    current_over_balls.append('Wd')
            elif b.extra_type == 'noball':                  current_over_balls.append('Nb')
            elif b.extra_type in ('bye', 'legbye'):         current_over_balls.append(f'{b.extra_runs}B')
            elif b.runs_off_bat == 0:                       current_over_balls.append('•')
            else:                                           current_over_balls.append(str(b.runs_off_bat))

        # Fall of wickets
        fow = []
        for wb in BallByBall.query.filter_by(innings_id=innings_id, is_wicket=True).order_by(BallByBall.id).all():
            r = db.session.query(db.func.sum(BallByBall.total_runs)).filter(
                BallByBall.innings_id == innings_id, BallByBall.id <= wb.id
            ).scalar() or 0
            p = db.session.get(Player, wb.dismissed_player_id) if wb.dismissed_player_id else None
            fow.append({'wicket': len(fow)+1, 'runs': r, 'over': f"{wb.over_number-1}.{wb.ball_number}", 'player': p.name if p else '?'})

        crr = round(innings.total_runs / innings.total_balls * 6, 2) if innings.total_balls > 0 else 0.0
        target = rrr = None
        if innings.innings_number == 2:
            inn1 = Innings.query.filter_by(match_id=innings.match_id, innings_number=1).first()
            if inn1:
                target = inn1.total_runs + 1
                balls_left = (match.total_overs * 6) - innings.total_balls
                rrr = round((target - innings.total_runs) / balls_left * 6, 2) if balls_left > 0 else 0.0

        def fmt_bat(bi):
            p = db.session.get(Player, bi.player_id)
            bwlr = db.session.get(Player, bi.bowler_id) if bi.bowler_id else None
            how_out = bi.dismissal_type
            if how_out and bwlr and how_out != 'runout': how_out = f"{how_out} b {bwlr.name}"
            return {
                'player_id' : bi.player_id,
                'name'      : p.name if p else '?',
                'runs'      : bi.runs,
                'balls'     : bi.balls,
                'fours'     : bi.fours,
                'sixes'     : bi.sixes,
                'singles'   : bi.singles,
                'doubles'   : bi.doubles,
                'triples'   : bi.triples,
                'sr'        : round(bi.runs / bi.balls * 100, 2) if bi.balls > 0 else 0.0,
                'is_out'    : bi.is_out,
                'dismissal' : how_out or 'not out',
                'is_striker': bi.player_id == innings.current_striker_id,
                'is_batting': not bi.is_out,
            }

        def fmt_bowl(bwi):
            p  = db.session.get(Player, bwi.player_id)
            ec = round(bwi.runs_conceded / (bwi.balls_bowled / 6), 2) if bwi.balls_bowled > 0 else 0.0
            return {
                'player_id'    : bwi.player_id,
                'name'         : p.name if p else '?',
                'overs'        : f"{bwi.balls_bowled // 6}.{bwi.balls_bowled % 6}",
                'balls_bowled' : bwi.balls_bowled,
                'runs'         : bwi.runs_conceded,
                'wickets'      : bwi.wickets,
                'economy'      : ec,
                'wides'        : bwi.wides,
                'no_balls'     : bwi.no_balls,
                'can_bowl_more': bwi.balls_bowled < 12,
            }

        return {
            'innings_id'        : innings.id,
            'innings_number'    : innings.innings_number,
            'status'            : innings.status,
            'total_runs'        : innings.total_runs,
            'total_wickets'     : innings.total_wickets,
            'total_balls'       : innings.total_balls,
            'total_extras'      : innings.total_extras,
            'wides'             : innings.wides,
            'no_balls'          : innings.no_balls,
            'byes'              : innings.byes,
            'leg_byes'          : innings.leg_byes,
            'overs_display'     : f"{innings.total_balls // 6}.{innings.total_balls % 6}",
            'current_run_rate'  : crr,
            'total_overs'       : match.total_overs,
            'target'            : target,
            'required_run_rate' : rrr,
            'striker'           : {'id': striker.id, 'name': striker.name} if striker else None,
            'non_striker'       : {'id': non_striker.id, 'name': non_striker.name} if non_striker else None,
            'current_bowler'    : {'id': bowler.id, 'name': bowler.name} if bowler else None,
            'batsmen'           : [fmt_bat(bi) for bi in batsmen_rows],
            'bowlers'           : [fmt_bowl(bwi) for bwi in bowler_rows],
            'current_over_balls': current_over_balls,
            'fall_of_wickets'   : fow,
        }

    @staticmethod
    def get_match_scorecard(match_id):
        return [
            ScoringEngine.get_scorecard(i.id)
            for i in Innings.query.filter_by(match_id=match_id).order_by(Innings.innings_number).all()
        ]