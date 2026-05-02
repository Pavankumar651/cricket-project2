-- ============================================================
-- PATCH FILE: Run this IMMEDIATELY after schema.sql
-- Fixes the double-counting bug by removing triggers that
-- duplicate what the Python scoring engine already does.
-- ============================================================

-- Drop ALL ball_by_ball triggers (Python handles all updates)
DROP TRIGGER IF EXISTS after_ball_insert    ON ball_by_ball;
DROP TRIGGER IF EXISTS after_ball_batsman   ON ball_by_ball;
DROP TRIGGER IF EXISTS after_ball_bowler    ON ball_by_ball;
DROP TRIGGER IF EXISTS after_player_insert  ON players;

-- Drop the trigger functions too
DROP FUNCTION IF EXISTS trg_update_innings_totals() CASCADE;
DROP FUNCTION IF EXISTS trg_update_batsman_stats()  CASCADE;
DROP FUNCTION IF EXISTS trg_update_bowler_stats()   CASCADE;

-- Keep only the career-stats auto-create trigger (harmless)
-- trg_create_career_stats stays

-- Reset all totals to 0 if testing fresh (OPTIONAL - comment out in production)
-- UPDATE innings SET total_runs=0, total_balls=0, total_wickets=0, total_extras=0,
--   wides=0, no_balls=0, byes=0, leg_byes=0 WHERE id > 0;
-- DELETE FROM ball_by_ball;
-- DELETE FROM batsman_innings;
-- DELETE FROM bowler_innings;

-- Verify triggers removed
SELECT trigger_name, event_object_table
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table;

-- Add missing columns if they don't exist (safe ALTER TABLE)
DO $$
BEGIN
    -- batsman_innings singles/doubles/triples
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='batsman_innings' AND column_name='singles') THEN
        ALTER TABLE batsman_innings ADD COLUMN singles INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='batsman_innings' AND column_name='doubles') THEN
        ALTER TABLE batsman_innings ADD COLUMN doubles INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='batsman_innings' AND column_name='triples') THEN
        ALTER TABLE batsman_innings ADD COLUMN triples INT DEFAULT 0;
    END IF;

    -- bowler_innings wides/no_balls
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='bowler_innings' AND column_name='wides') THEN
        ALTER TABLE bowler_innings ADD COLUMN wides INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='bowler_innings' AND column_name='no_balls') THEN
        ALTER TABLE bowler_innings ADD COLUMN no_balls INT DEFAULT 0;
    END IF;

    -- innings extras breakdown
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='innings' AND column_name='wides') THEN
        ALTER TABLE innings ADD COLUMN wides INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='innings' AND column_name='no_balls') THEN
        ALTER TABLE innings ADD COLUMN no_balls INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='innings' AND column_name='byes') THEN
        ALTER TABLE innings ADD COLUMN byes INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='innings' AND column_name='leg_byes') THEN
        ALTER TABLE innings ADD COLUMN leg_byes INT DEFAULT 0;
    END IF;
END $$;

-- Update overs_bowled computed column in bowler_innings when queried
-- (stored as integer balls_bowled, displayed as X.Y)

-- Ensure player_career_stats has all needed columns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='player_career_stats' AND column_name='singles') THEN
        ALTER TABLE player_career_stats ADD COLUMN singles INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='player_career_stats' AND column_name='doubles') THEN
        ALTER TABLE player_career_stats ADD COLUMN doubles INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='player_career_stats' AND column_name='triples') THEN
        ALTER TABLE player_career_stats ADD COLUMN triples INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='player_career_stats' AND column_name='wins') THEN
        ALTER TABLE player_career_stats ADD COLUMN wins INT DEFAULT 0;
    END IF;
END $$;

-- Fix matches table missing win columns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='matches' AND column_name='win_margin') THEN
        ALTER TABLE matches ADD COLUMN win_margin INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='matches' AND column_name='win_type') THEN
        ALTER TABLE matches ADD COLUMN win_type VARCHAR(20);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='matches' AND column_name='completed_at') THEN
        ALTER TABLE matches ADD COLUMN completed_at TIMESTAMP;
    END IF;
END $$;

SELECT 'Patch applied successfully. Triggers removed. Schema fixed.' AS status;