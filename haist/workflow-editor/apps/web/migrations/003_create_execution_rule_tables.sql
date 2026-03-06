-- Migration: Create execution rule tables for automated trigger processing
-- Run this after 002_create_conversation_tables.sql

-- ============================================================================
-- EXECUTION_RULE TABLE
-- Stores user-defined rules for automatic trigger processing
-- ============================================================================
CREATE TABLE IF NOT EXISTS execution_rule (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,

  -- Rule metadata
  name TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  priority INTEGER DEFAULT 0,  -- Higher = checked first

  -- Input validation: which triggers this rule accepts
  -- Array of trigger slugs, e.g., ["GMAIL_NEW_EMAIL", "SLACK_MESSAGE_RECEIVED"]
  -- NULL or empty array means accepts all triggers
  accepted_triggers JSONB DEFAULT '[]'::jsonb,

  -- Topic relevancy: human language condition for when to activate
  -- AI will evaluate incoming content against this condition
  topic_condition TEXT NOT NULL,

  -- Execution steps: array of step objects
  -- Each step can be either:
  --   { "type": "instruction", "content": "Human language instruction" }
  --   { "type": "action", "toolName": "GMAIL_SEND_EMAIL", "parameters": {...} }
  execution_steps JSONB NOT NULL DEFAULT '[]'::jsonb,

  -- Output configuration
  output_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- Structure:
  -- {
  --   "platform": "slack" | "gmail" | "webhook" | "none",
  --   "destination": "channel_id" | "email@example.com" | "https://...",
  --   "format": "summary" | "detailed" | "raw",
  --   "template": "Optional message template with {{result}} placeholders"
  -- }

  -- Stats
  execution_count INTEGER DEFAULT 0,
  last_executed_at TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_execution_rule_user_id ON execution_rule(user_id);
CREATE INDEX IF NOT EXISTS idx_execution_rule_is_active ON execution_rule(is_active);
CREATE INDEX IF NOT EXISTS idx_execution_rule_priority ON execution_rule(priority DESC);
CREATE INDEX IF NOT EXISTS idx_execution_rule_user_active ON execution_rule(user_id, is_active)
  WHERE is_active = true;

-- ============================================================================
-- AUTO-UPDATE TRIGGER
-- ============================================================================
CREATE OR REPLACE FUNCTION update_execution_rule_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_execution_rule_updated_at ON execution_rule;
CREATE TRIGGER trigger_execution_rule_updated_at
  BEFORE UPDATE ON execution_rule
  FOR EACH ROW
  EXECUTE FUNCTION update_execution_rule_updated_at();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE execution_rule IS 'User-defined rules for automatic trigger processing';
COMMENT ON COLUMN execution_rule.priority IS 'Higher priority rules are checked first (0 is default)';
COMMENT ON COLUMN execution_rule.accepted_triggers IS 'Array of trigger slugs this rule accepts, empty means all';
COMMENT ON COLUMN execution_rule.topic_condition IS 'Human language condition for AI to evaluate';
COMMENT ON COLUMN execution_rule.execution_steps IS 'Array of steps: instructions or structured actions';
COMMENT ON COLUMN execution_rule.output_config IS 'Where and how to send execution results';
