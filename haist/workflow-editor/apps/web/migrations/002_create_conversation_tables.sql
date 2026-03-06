-- Migration: Create conversation tables for AI Assistant chat history
-- Run this after 001_create_workflow_tables.sql

-- ============================================================================
-- CONVERSATION TABLE
-- Stores chat conversation metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversation (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  title TEXT NOT NULL DEFAULT 'New conversation',
  mode TEXT NOT NULL CHECK (mode IN ('workflow-generator', 'tool-router')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- CONVERSATION_MESSAGE TABLE
-- Stores individual messages within a conversation
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversation_message (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  content TEXT NOT NULL,
  -- For workflow-generator mode: workflow JSON, required connections
  workflow JSONB,
  required_connections JSONB,
  -- For tool-router mode: tool call results
  tool_calls JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_conversation_user_id ON conversation(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_updated_at ON conversation(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_message_conversation_id ON conversation_message(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_message_created_at ON conversation_message(created_at);

-- ============================================================================
-- AUTO-UPDATE TRIGGER
-- Automatically updates updated_at when conversation is modified
-- ============================================================================
CREATE OR REPLACE FUNCTION update_conversation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_conversation_updated_at ON conversation;
CREATE TRIGGER trigger_conversation_updated_at
  BEFORE UPDATE ON conversation
  FOR EACH ROW
  EXECUTE FUNCTION update_conversation_updated_at();

-- Also update conversation.updated_at when a message is added
CREATE OR REPLACE FUNCTION update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE conversation SET updated_at = NOW() WHERE id = NEW.conversation_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_conversation_on_message ON conversation_message;
CREATE TRIGGER trigger_conversation_on_message
  AFTER INSERT ON conversation_message
  FOR EACH ROW
  EXECUTE FUNCTION update_conversation_on_message();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE conversation IS 'AI Assistant chat conversations';
COMMENT ON TABLE conversation_message IS 'Individual messages within conversations';

COMMENT ON COLUMN conversation.mode IS 'Assistant mode: workflow-generator or tool-router';
COMMENT ON COLUMN conversation_message.workflow IS 'JSON workflow document for workflow-generator messages';
COMMENT ON COLUMN conversation_message.tool_calls IS 'JSON array of tool call results for tool-router messages';
