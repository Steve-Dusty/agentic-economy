-- Migration: Create workflow and execution tables for BetterAuth integration
-- Run this after running `npx @better-auth/cli migrate` which creates the `user` table

-- ============================================================================
-- WORKFLOW TABLE
-- Stores workflow definitions with nodes and edges
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  nodes JSONB DEFAULT '[]'::jsonb,
  edges JSONB DEFAULT '[]'::jsonb,
  settings JSONB,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- EXECUTION TABLE
-- Stores workflow execution history
-- ============================================================================
CREATE TABLE IF NOT EXISTS execution (
  id TEXT PRIMARY KEY,
  workflow_id TEXT NOT NULL REFERENCES workflow(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED')),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  input JSONB,
  output JSONB,
  error TEXT
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_workflow_user_id ON workflow(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_updated_at ON workflow(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_execution_workflow_id ON execution(workflow_id);
CREATE INDEX IF NOT EXISTS idx_execution_user_id ON execution(user_id);
CREATE INDEX IF NOT EXISTS idx_execution_status ON execution(status);
CREATE INDEX IF NOT EXISTS idx_execution_started_at ON execution(started_at DESC);

-- ============================================================================
-- AUTO-UPDATE TRIGGER
-- Automatically updates updated_at when workflow is modified
-- ============================================================================
CREATE OR REPLACE FUNCTION update_workflow_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_workflow_updated_at ON workflow;
CREATE TRIGGER trigger_workflow_updated_at
  BEFORE UPDATE ON workflow
  FOR EACH ROW
  EXECUTE FUNCTION update_workflow_updated_at();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE workflow IS 'User workflow definitions with nodes and edges';
COMMENT ON TABLE execution IS 'Workflow execution history and results';

COMMENT ON COLUMN workflow.nodes IS 'JSON array of workflow nodes (ReactFlow format)';
COMMENT ON COLUMN workflow.edges IS 'JSON array of workflow edges/connections (ReactFlow format)';
COMMENT ON COLUMN workflow.settings IS 'Workflow-specific settings and configuration';

COMMENT ON COLUMN execution.status IS 'Execution status: PENDING, RUNNING, SUCCESS, or FAILED';
COMMENT ON COLUMN execution.input IS 'Input data provided to the workflow execution';
COMMENT ON COLUMN execution.output IS 'Output/result data from the workflow execution';
