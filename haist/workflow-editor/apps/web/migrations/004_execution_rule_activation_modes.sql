-- Migration: Add activation modes to execution_rule table
-- Run this after 003_create_execution_rule_tables.sql

-- ============================================================================
-- NEW COLUMNS FOR ACTIVATION MODES
-- ============================================================================

-- Activation mode: how the rule can be triggered
-- 'trigger' - Only fires on Composio webhook events (default, existing behavior)
-- 'manual' - User invokes via @RuleName in AI Assistant chat
-- 'scheduled' - Runs automatically on preset intervals
-- 'all' - Can be triggered by any method
ALTER TABLE execution_rule
ADD COLUMN IF NOT EXISTS activation_mode TEXT DEFAULT 'trigger';

-- Schedule configuration columns
ALTER TABLE execution_rule
ADD COLUMN IF NOT EXISTS schedule_enabled BOOLEAN DEFAULT false;

-- Schedule interval: '15min' | 'hourly' | 'daily' | 'weekly'
ALTER TABLE execution_rule
ADD COLUMN IF NOT EXISTS schedule_interval TEXT;

-- Last time the scheduled rule ran
ALTER TABLE execution_rule
ADD COLUMN IF NOT EXISTS schedule_last_run TIMESTAMPTZ;

-- Next scheduled run time (pre-calculated for efficient querying)
ALTER TABLE execution_rule
ADD COLUMN IF NOT EXISTS schedule_next_run TIMESTAMPTZ;

-- ============================================================================
-- CONSTRAINTS
-- ============================================================================

-- Ensure activation_mode has valid values
ALTER TABLE execution_rule
DROP CONSTRAINT IF EXISTS check_activation_mode;

ALTER TABLE execution_rule
ADD CONSTRAINT check_activation_mode
CHECK (activation_mode IN ('trigger', 'manual', 'scheduled', 'all'));

-- Ensure schedule_interval has valid values when present
ALTER TABLE execution_rule
DROP CONSTRAINT IF EXISTS check_schedule_interval;

ALTER TABLE execution_rule
ADD CONSTRAINT check_schedule_interval
CHECK (schedule_interval IS NULL OR schedule_interval IN ('15min', 'hourly', 'daily', 'weekly'));

-- ============================================================================
-- INDEX FOR SCHEDULED QUERIES
-- ============================================================================

-- Index for efficiently querying rules that are due to run
-- This supports the cron endpoint query: WHERE schedule_enabled = true AND schedule_next_run <= NOW()
CREATE INDEX IF NOT EXISTS idx_execution_rule_scheduled
  ON execution_rule(schedule_enabled, schedule_next_run)
  WHERE schedule_enabled = true;

-- Index for querying rules by activation mode (useful for manual invocation dropdown)
CREATE INDEX IF NOT EXISTS idx_execution_rule_activation_mode
  ON execution_rule(activation_mode)
  WHERE is_active = true;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON COLUMN execution_rule.activation_mode IS 'How the rule can be triggered: trigger (webhook), manual (@mention), scheduled (cron), or all';
COMMENT ON COLUMN execution_rule.schedule_enabled IS 'Whether scheduled execution is enabled for this rule';
COMMENT ON COLUMN execution_rule.schedule_interval IS 'Schedule interval: 15min, hourly, daily, or weekly';
COMMENT ON COLUMN execution_rule.schedule_last_run IS 'Timestamp of last scheduled execution';
COMMENT ON COLUMN execution_rule.schedule_next_run IS 'Pre-calculated next scheduled run time for efficient cron queries';
