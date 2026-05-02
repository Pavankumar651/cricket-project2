-- ============================================================
-- SMART DAILY CRICKET SCORING & PLAYER ANALYTICS SYSTEM
-- Complete PostgreSQL Database Schema
-- ============================================================

-- Drop existing tables if re-running
DROP TABLE IF EXISTS ball_by_ball CASCADE;
DROP TABLE IF EXISTS innings CASCADE;
DROP TABLE IF EXISTS match_teams CASCADE;
DROP TABLE IF EXISTS daily_teams CASCADE;
DROP TABLE IF EXISTS matches CASCADE;
DROP TABLE IF EXISTS days CASCADE;
DROP TABLE IF EXISTS player_career_stats CASCADE;
DROP TABLE IF EXISTS players CASCADE;
DROP TABLE IF EXISTS admins CASCADE;

-- ============================================================
-- ADMINS TABLE
-- ============================================================
CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- PLAYERS TABLE (Fixed master list, created once)
-- ============================================================
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(20) DEFAULT 'All Rounder',
    is_active BOOLEAN DEFAULT TRUE,
    jersey_number INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- PLAYER CAREER STATS (Aggregated, always updated)
-- ============================================================
CREATE TABLE player_career_stats (
    player_id INT PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
    -- Batting
    total_runs INT DEFAULT 0,
    balls_faced INT DEFAULT 0,
    matches_batted INT DEFAULT 0,
    highest_score INT DEFAULT 0,
    times_out INT DEFAULT 0,
    fours INT DEFAULT 0,
    sixes INT DEFAULT 0,
    singles INT DEFAULT 0,
    doubles INT DEFAULT 0,
    triples INT DEFAULT 0,
    -- Bowling
    overs_bowled NUMERIC(6,1) DEFAULT 0,
    balls_bowled INT DEFAULT 0,
    runs_conceded INT DEFAULT 0,
    wickets INT DEFAULT 0,
    matches_bowled INT DEFAULT 0,
    best_wickets INT DEFAULT 0,
    best_runs INT DEFAULT 999,
    -- Overall
    matches_played INT DEFAULT 0,
    wins INT DEFAULT 0,
    mvp_awards INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- DAYS TABLE (Each cricket day session)
-- ============================================================
CREATE TABLE days (
    id SERIAL PRIMARY KEY,
    day_date DATE UNIQUE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(20) DEFAULT 'active', -- active, completed
    mvp_player_id INT REFERENCES players(id),
    top_scorer_id INT REFERENCES players(id),
    top_wicket_taker_id INT REFERENCES players(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- ============================================================
-- DAILY TEAMS (Team A and Team B per day)
-- ============================================================
CREATE TABLE daily_teams (
    id SERIAL PRIMARY KEY,
    day_id INT NOT NULL REFERENCES days(id) ON DELETE CASCADE,
    team_label VARCHAR(10) NOT NULL, -- 'A' or 'B'
    team_name VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(day_id, team_label)
);

-- ============================================================
-- TEAM PLAYERS (Which players are in each daily team)
-- ============================================================
CREATE TABLE team_players (
    id SERIAL PRIMARY KEY,
    daily_team_id INT NOT NULL REFERENCES daily_teams(id) ON DELETE CASCADE,
    player_id INT NOT NULL REFERENCES players(id),
    UNIQUE(daily_team_id, player_id)
);

-- ============================================================
-- MATCHES TABLE (Multiple matches per day)
-- ============================================================
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    day_id INT NOT NULL REFERENCES days(id) ON DELETE CASCADE,
    match_number INT NOT NULL, -- 1,2,3,4,5 per day
    team_a_id INT NOT NULL REFERENCES daily_teams(id),
    team_b_id INT NOT NULL REFERENCES daily_teams(id),
    toss_winner VARCHAR(10), -- 'A' or 'B'
    batting_first VARCHAR(10), -- 'A' or 'B'
    total_overs INT DEFAULT 10,
    status VARCHAR(20) DEFAULT 'upcoming', -- upcoming, live, innings2, completed
    winner VARCHAR(10), -- 'A', 'B', or 'tie'
    win_margin INT DEFAULT 0,
    win_type VARCHAR(20), -- 'runs', 'wickets', 'tie'
    -- Predictions (ML)
    team_a_win_prob NUMERIC(5,2) DEFAULT 50.00,
    team_b_win_prob NUMERIC(5,2) DEFAULT 50.00,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- ============================================================
-- INNINGS TABLE (2 innings per match)
-- ============================================================
CREATE TABLE innings (
    id SERIAL PRIMARY KEY,
    match_id INT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    innings_number INT NOT NULL, -- 1 or 2
    batting_team_id INT NOT NULL REFERENCES daily_teams(id),
    bowling_team_id INT NOT NULL REFERENCES daily_teams(id),
    total_runs INT DEFAULT 0,
    total_wickets INT DEFAULT 0,
    total_balls INT DEFAULT 0,
    total_extras INT DEFAULT 0,
    wides INT DEFAULT 0,
    no_balls INT DEFAULT 0,
    byes INT DEFAULT 0,
    leg_byes INT DEFAULT 0,
    current_striker_id INT REFERENCES players(id),
    current_non_striker_id INT REFERENCES players(id),
    current_bowler_id INT REFERENCES players(id),
    status VARCHAR(20) DEFAULT 'live', -- live, completed
    completed_at TIMESTAMP,
    UNIQUE(match_id, innings_number)
);

-- ============================================================
-- BALL BY BALL TABLE (Every delivery recorded)
-- ============================================================
CREATE TABLE ball_by_ball (
    id SERIAL PRIMARY KEY,
    innings_id INT NOT NULL REFERENCES innings(id) ON DELETE CASCADE,
    over_number INT NOT NULL,       -- 1-based
    ball_number INT NOT NULL,       -- 1-6 (legal balls)
    delivery_number INT NOT NULL,   -- includes extras
    striker_id INT NOT NULL REFERENCES players(id),
    non_striker_id INT NOT NULL REFERENCES players(id),
    bowler_id INT NOT NULL REFERENCES players(id),
    -- Scoring
    runs_off_bat INT DEFAULT 0,
    extra_runs INT DEFAULT 0,
    extra_type VARCHAR(20) DEFAULT NULL, -- 'wide','noball','bye','legbye'
    total_runs INT DEFAULT 0,       -- runs_off_bat + extra_runs
    -- Wicket
    is_wicket BOOLEAN DEFAULT FALSE,
    wicket_type VARCHAR(30) DEFAULT NULL, -- 'bowled','caught','runout','lbw','stumped','hitwicket'
    dismissed_player_id INT REFERENCES players(id),
    fielder_id INT REFERENCES players(id),
    -- Strike
    strike_changed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- BATSMAN INNINGS STATS (Per batsman per innings)
-- ============================================================
CREATE TABLE batsman_innings (
    id SERIAL PRIMARY KEY,
    innings_id INT NOT NULL REFERENCES innings(id) ON DELETE CASCADE,
    player_id INT NOT NULL REFERENCES players(id),
    batting_order INT,
    runs INT DEFAULT 0,
    balls INT DEFAULT 0,
    fours INT DEFAULT 0,
    sixes INT DEFAULT 0,
    singles INT DEFAULT 0,
    doubles INT DEFAULT 0,
    triples INT DEFAULT 0,
    is_out BOOLEAN DEFAULT FALSE,
    dismissal_type VARCHAR(30),
    bowler_id INT REFERENCES players(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(innings_id, player_id)
);

-- ============================================================
-- BOWLER INNINGS STATS (Per bowler per innings)
-- ============================================================
CREATE TABLE bowler_innings (
    id SERIAL PRIMARY KEY,
    innings_id INT NOT NULL REFERENCES innings(id) ON DELETE CASCADE,
    player_id INT NOT NULL REFERENCES players(id),
    overs_bowled NUMERIC(4,1) DEFAULT 0,
    balls_bowled INT DEFAULT 0,
    runs_conceded INT DEFAULT 0,
    wickets INT DEFAULT 0,
    wides INT DEFAULT 0,
    no_balls INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(innings_id, player_id)
);

-- ============================================================
-- VIEWS
-- ============================================================

-- Player batting averages
CREATE OR REPLACE VIEW v_player_batting AS
SELECT
    p.id,
    p.name,
    p.role,
    cs.matches_batted,
    cs.total_runs,
    cs.balls_faced,
    cs.highest_score,
    cs.times_out,
    cs.fours,
    cs.sixes,
    CASE WHEN cs.balls_faced > 0 THEN ROUND((cs.total_runs::NUMERIC / cs.balls_faced) * 100, 2) ELSE 0 END AS strike_rate,
    CASE WHEN cs.times_out > 0 THEN ROUND(cs.total_runs::NUMERIC / cs.times_out, 2) ELSE cs.total_runs END AS batting_avg
FROM players p
JOIN player_career_stats cs ON p.id = cs.player_id
WHERE p.is_active = TRUE;

-- Player bowling averages
CREATE OR REPLACE VIEW v_player_bowling AS
SELECT
    p.id,
    p.name,
    cs.matches_bowled,
    cs.balls_bowled,
    cs.overs_bowled,
    cs.runs_conceded,
    cs.wickets,
    cs.best_wickets,
    cs.best_runs,
    CASE WHEN cs.balls_bowled > 0 THEN ROUND(cs.runs_conceded::NUMERIC / (cs.balls_bowled / 6.0), 2) ELSE 0 END AS economy,
    CASE WHEN cs.wickets > 0 THEN ROUND(cs.runs_conceded::NUMERIC / cs.wickets, 2) ELSE NULL END AS bowling_avg
FROM players p
JOIN player_career_stats cs ON p.id = cs.player_id
WHERE p.is_active = TRUE;

-- Weekly leaderboard
CREATE OR REPLACE VIEW v_weekly_leaderboard AS
SELECT
    p.id,
    p.name,
    SUM(bi.runs) AS weekly_runs,
    SUM(bwi.wickets) AS weekly_wickets,
    COUNT(DISTINCT bi.innings_id) AS innings_played
FROM players p
LEFT JOIN batsman_innings bi ON p.id = bi.player_id
LEFT JOIN innings i ON bi.innings_id = i.id
LEFT JOIN matches m ON i.match_id = m.id
LEFT JOIN days d ON m.day_id = d.id
LEFT JOIN bowler_innings bwi ON p.id = bwi.player_id AND bwi.innings_id = i.id
WHERE d.day_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY p.id, p.name
ORDER BY weekly_runs DESC;

-- Monthly leaderboard
CREATE OR REPLACE VIEW v_monthly_leaderboard AS
SELECT
    p.id,
    p.name,
    SUM(bi.runs) AS monthly_runs,
    SUM(bwi.wickets) AS monthly_wickets,
    COUNT(DISTINCT bi.innings_id) AS innings_played,
    cs.mvp_awards
FROM players p
LEFT JOIN batsman_innings bi ON p.id = bi.player_id
LEFT JOIN innings i ON bi.innings_id = i.id
LEFT JOIN matches m ON i.match_id = m.id
LEFT JOIN days d ON m.day_id = d.id
LEFT JOIN bowler_innings bwi ON p.id = bwi.player_id AND bwi.innings_id = i.id
LEFT JOIN player_career_stats cs ON p.id = cs.player_id
WHERE d.day_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY p.id, p.name, cs.mvp_awards
ORDER BY monthly_runs DESC;

-- Current live match view
CREATE OR REPLACE VIEW v_live_match AS
SELECT
    m.id AS match_id,
    m.match_number,
    m.status,
    m.batting_first,
    i.innings_number,
    i.total_runs,
    i.total_wickets,
    i.total_balls,
    i.total_extras,
    striker.name AS striker_name,
    non_striker.name AS non_striker_name,
    bowler.name AS bowler_name,
    m.total_overs,
    d.day_date
FROM matches m
JOIN innings i ON m.id = i.match_id AND i.status = 'live'
JOIN days d ON m.day_id = d.id
LEFT JOIN players striker ON i.current_striker_id = striker.id
LEFT JOIN players non_striker ON i.current_non_striker_id = non_striker.id
LEFT JOIN players bowler ON i.current_bowler_id = bowler.id
WHERE m.status IN ('live', 'innings2')
LIMIT 1;

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Function: Get current over balls for a bowler in an innings
CREATE OR REPLACE FUNCTION get_bowler_balls(p_innings_id INT, p_player_id INT)
RETURNS INT AS $$
BEGIN
    RETURN COALESCE(
        (SELECT balls_bowled FROM bowler_innings
         WHERE innings_id = p_innings_id AND player_id = p_player_id),
        0
    );
END;
$$ LANGUAGE plpgsql;

-- Function: Check if bowler can bowl (max 2 overs = 12 balls)
CREATE OR REPLACE FUNCTION can_bowler_bowl(p_innings_id INT, p_player_id INT)
RETURNS BOOLEAN AS $$
DECLARE
    v_balls INT;
BEGIN
    SELECT COALESCE(balls_bowled, 0) INTO v_balls
    FROM bowler_innings
    WHERE innings_id = p_innings_id AND player_id = p_player_id;

    IF v_balls IS NULL THEN
        RETURN TRUE;
    END IF;

    RETURN v_balls < 12; -- 2 overs = 12 balls
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate current run rate
CREATE OR REPLACE FUNCTION get_run_rate(p_innings_id INT)
RETURNS NUMERIC AS $$
DECLARE
    v_runs INT;
    v_balls INT;
BEGIN
    SELECT total_runs, total_balls INTO v_runs, v_balls
    FROM innings WHERE id = p_innings_id;

    IF v_balls = 0 THEN RETURN 0; END IF;
    RETURN ROUND((v_runs::NUMERIC / v_balls) * 6, 2);
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate required run rate (2nd innings)
CREATE OR REPLACE FUNCTION get_required_rate(p_innings_id INT)
RETURNS NUMERIC AS $$
DECLARE
    v_target INT;
    v_current_runs INT;
    v_balls_left INT;
    v_total_overs INT;
BEGIN
    SELECT
        (SELECT total_runs + 1 FROM innings WHERE match_id = i.match_id AND innings_number = 1),
        i.total_runs,
        (m.total_overs * 6) - i.total_balls,
        m.total_overs
    INTO v_target, v_current_runs, v_balls_left, v_total_overs
    FROM innings i
    JOIN matches m ON i.match_id = m.id
    WHERE i.id = p_innings_id;

    IF v_balls_left <= 0 THEN RETURN 0; END IF;
    RETURN ROUND(((v_target - v_current_runs)::NUMERIC / v_balls_left) * 6, 2);
END;
$$ LANGUAGE plpgsql;

-- Function: Get player form (last 5 matches average)
CREATE OR REPLACE FUNCTION get_player_form(p_player_id INT)
RETURNS VARCHAR AS $$
DECLARE
    v_avg_runs NUMERIC;
BEGIN
    SELECT AVG(bi.runs) INTO v_avg_runs
    FROM batsman_innings bi
    JOIN innings i ON bi.innings_id = i.id
    JOIN matches m ON i.match_id = m.id
    ORDER BY m.created_at DESC
    LIMIT 5;

    IF v_avg_runs IS NULL THEN RETURN 'No Data'; END IF;
    IF v_avg_runs >= 25 THEN RETURN 'Hot Form';
    ELSIF v_avg_runs >= 12 THEN RETURN 'Average Form';
    ELSE RETURN 'Poor Form';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- STORED PROCEDURES
-- ============================================================

-- Procedure: Update career stats after innings
CREATE OR REPLACE PROCEDURE update_career_stats_batting(p_player_id INT, p_innings_id INT)
LANGUAGE plpgsql AS $$
DECLARE
    v_bi batsman_innings%ROWTYPE;
BEGIN
    SELECT * INTO v_bi FROM batsman_innings
    WHERE innings_id = p_innings_id AND player_id = p_player_id;

    IF NOT FOUND THEN RETURN; END IF;

    INSERT INTO player_career_stats (player_id)
    VALUES (p_player_id)
    ON CONFLICT (player_id) DO NOTHING;

    UPDATE player_career_stats SET
        total_runs = total_runs + v_bi.runs,
        balls_faced = balls_faced + v_bi.balls,
        fours = fours + v_bi.fours,
        sixes = sixes + v_bi.sixes,
        singles = singles + v_bi.singles,
        doubles = doubles + v_bi.doubles,
        triples = triples + v_bi.triples,
        times_out = times_out + (CASE WHEN v_bi.is_out THEN 1 ELSE 0 END),
        matches_batted = matches_batted + 1,
        highest_score = GREATEST(highest_score, v_bi.runs),
        updated_at = NOW()
    WHERE player_id = p_player_id;
END;
$$;

-- Procedure: Update career stats bowling
CREATE OR REPLACE PROCEDURE update_career_stats_bowling(p_player_id INT, p_innings_id INT)
LANGUAGE plpgsql AS $$
DECLARE
    v_bwi bowler_innings%ROWTYPE;
BEGIN
    SELECT * INTO v_bwi FROM bowler_innings
    WHERE innings_id = p_innings_id AND player_id = p_player_id;

    IF NOT FOUND THEN RETURN; END IF;

    INSERT INTO player_career_stats (player_id)
    VALUES (p_player_id)
    ON CONFLICT (player_id) DO NOTHING;

    UPDATE player_career_stats SET
        balls_bowled = balls_bowled + v_bwi.balls_bowled,
        overs_bowled = overs_bowled + (v_bwi.balls_bowled / 6.0),
        runs_conceded = runs_conceded + v_bwi.runs_conceded,
        wickets = wickets + v_bwi.wickets,
        matches_bowled = matches_bowled + 1,
        best_wickets = CASE WHEN v_bwi.wickets > best_wickets THEN v_bwi.wickets
                            WHEN v_bwi.wickets = best_wickets AND v_bwi.runs_conceded < best_runs THEN v_bwi.wickets
                            ELSE best_wickets END,
        best_runs = CASE WHEN v_bwi.wickets > best_wickets THEN v_bwi.runs_conceded
                         WHEN v_bwi.wickets = best_wickets AND v_bwi.runs_conceded < best_runs THEN v_bwi.runs_conceded
                         ELSE best_runs END,
        updated_at = NOW()
    WHERE player_id = p_player_id;
END;
$$;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Trigger: Auto-create career stats row when player is inserted
CREATE OR REPLACE FUNCTION trg_create_career_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO player_career_stats (player_id)
    VALUES (NEW.id)
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_player_insert
AFTER INSERT ON players
FOR EACH ROW EXECUTE FUNCTION trg_create_career_stats();

-- Trigger: Auto-update innings totals when ball is recorded
CREATE OR REPLACE FUNCTION trg_update_innings_totals()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE innings SET
        total_runs = total_runs + NEW.total_runs,
        total_balls = CASE WHEN NEW.extra_type IN ('wide', 'noball') THEN total_balls ELSE total_balls + 1 END,
        total_extras = total_extras + NEW.extra_runs,
        wides = wides + (CASE WHEN NEW.extra_type = 'wide' THEN 1 ELSE 0 END),
        no_balls = no_balls + (CASE WHEN NEW.extra_type = 'noball' THEN 1 ELSE 0 END),
        byes = byes + (CASE WHEN NEW.extra_type = 'bye' THEN NEW.extra_runs ELSE 0 END),
        leg_byes = leg_byes + (CASE WHEN NEW.extra_type = 'legbye' THEN NEW.extra_runs ELSE 0 END),
        total_wickets = total_wickets + (CASE WHEN NEW.is_wicket THEN 1 ELSE 0 END)
    WHERE id = NEW.innings_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_ball_insert
AFTER INSERT ON ball_by_ball
FOR EACH ROW EXECUTE FUNCTION trg_update_innings_totals();

-- Trigger: Auto-update batsman innings stats after each ball
CREATE OR REPLACE FUNCTION trg_update_batsman_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Upsert striker stats
    INSERT INTO batsman_innings (innings_id, player_id, runs, balls, fours, sixes, singles, doubles, triples, is_out, dismissal_type, bowler_id)
    VALUES (NEW.innings_id, NEW.striker_id, 0, 0, 0, 0, 0, 0, 0, FALSE, NULL, NULL)
    ON CONFLICT (innings_id, player_id) DO NOTHING;

    -- Update stats (only for legal balls, not wides)
    IF NEW.extra_type IS DISTINCT FROM 'wide' THEN
        UPDATE batsman_innings SET
            balls = balls + 1,
            runs = runs + NEW.runs_off_bat,
            fours = fours + (CASE WHEN NEW.runs_off_bat = 4 THEN 1 ELSE 0 END),
            sixes = sixes + (CASE WHEN NEW.runs_off_bat = 6 THEN 1 ELSE 0 END),
            singles = singles + (CASE WHEN NEW.runs_off_bat = 1 THEN 1 ELSE 0 END),
            doubles = doubles + (CASE WHEN NEW.runs_off_bat = 2 THEN 1 ELSE 0 END),
            triples = triples + (CASE WHEN NEW.runs_off_bat = 3 THEN 1 ELSE 0 END),
            is_out = CASE WHEN NEW.is_wicket AND NEW.dismissed_player_id = NEW.striker_id THEN TRUE ELSE is_out END,
            dismissal_type = CASE WHEN NEW.is_wicket AND NEW.dismissed_player_id = NEW.striker_id THEN NEW.wicket_type ELSE dismissal_type END,
            bowler_id = CASE WHEN NEW.is_wicket AND NEW.dismissed_player_id = NEW.striker_id THEN NEW.bowler_id ELSE bowler_id END
        WHERE innings_id = NEW.innings_id AND player_id = NEW.striker_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_ball_batsman
AFTER INSERT ON ball_by_ball
FOR EACH ROW EXECUTE FUNCTION trg_update_batsman_stats();

-- Trigger: Auto-update bowler innings stats
CREATE OR REPLACE FUNCTION trg_update_bowler_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO bowler_innings (innings_id, player_id, balls_bowled, runs_conceded, wickets, wides, no_balls)
    VALUES (NEW.innings_id, NEW.bowler_id, 0, 0, 0, 0, 0)
    ON CONFLICT (innings_id, player_id) DO NOTHING;

    UPDATE bowler_innings SET
        balls_bowled = balls_bowled + (CASE WHEN NEW.extra_type IN ('wide', 'noball') THEN 0 ELSE 1 END),
        runs_conceded = runs_conceded + NEW.total_runs,
        wickets = wickets + (CASE WHEN NEW.is_wicket AND NEW.wicket_type != 'runout' THEN 1 ELSE 0 END),
        wides = wides + (CASE WHEN NEW.extra_type = 'wide' THEN 1 ELSE 0 END),
        no_balls = no_balls + (CASE WHEN NEW.extra_type = 'noball' THEN 1 ELSE 0 END),
        overs_bowled = FLOOR((balls_bowled + (CASE WHEN NEW.extra_type IN ('wide', 'noball') THEN 0 ELSE 1 END)) / 6.0)
    WHERE innings_id = NEW.innings_id AND player_id = NEW.bowler_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_ball_bowler
AFTER INSERT ON ball_by_ball
FOR EACH ROW EXECUTE FUNCTION trg_update_bowler_stats();

-- ============================================================
-- SEED DATA - Insert 15 Players
-- ============================================================
INSERT INTO players (id, name, role) VALUES
(1,  'Pavankumar', 'All Rounder'),
(2,  'Veeresh',    'All Rounder'),
(3,  'Darshan',    'All Rounder'),
(4,  'Sukin',      'All Rounder'),
(5,  'Yashwanth',  'All Rounder'),
(6,  'Santhosh',   'All Rounder'),
(7,  'Pramod',     'All Rounder'),
(8,  'Rakesh',     'All Rounder'),
(9,  'Sachin',     'All Rounder'),
(10, 'Nishanth',   'All Rounder'),
(11, 'Neeraj',     'All Rounder'),
(12, 'Putraju',    'All Rounder'),
(13, 'Shivu',      'All Rounder'),
(14, 'Prashant',   'All Rounder'),
(15, 'Praveen',    'All Rounder');

-- Reset sequence to continue from 16
SELECT setval('players_id_seq', 15);

-- Insert default admin
INSERT INTO admins (username, password_hash)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMbNq/fxEGwCKQVFqoVRUwdFqO');
-- Default password: admin123 (bcrypt hashed)