-- Migration: Create execution_log table
-- Run this in your Supabase SQL editor or psql

CREATE TABLE execution_log (
  id TEXT PRIMARY KEY,
  rule_id TEXT NOT NULL,
  rule_name TEXT NOT NULL,
  user_id TEXT NOT NULL,
  trigger_slug TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('success', 'failure', 'partial')),
  steps_json JSONB,
  output_text TEXT,
  error_text TEXT,
  duration_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_execution_log_user_id ON execution_log(user_id);
CREATE INDEX idx_execution_log_rule_id ON execution_log(rule_id);
CREATE INDEX idx_execution_log_created_at ON execution_log(created_at);
