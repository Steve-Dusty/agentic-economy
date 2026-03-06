/**
 * Bubble Context Builder
 *
 * Builds comprehensive context strings from bubble registry and Composio tools
 * for inclusion in the LLM system prompt.
 */

import { getBubbleRegistryForAI, type BubbleSummaryForAI } from '@workflow-editor/core';
import type { AIAssistantContext, ComposioToolSummary } from './types';

/**
 * Format a single bubble with FULL parameter details for the AI context
 */
function formatBubbleForAI(bubble: BubbleSummaryForAI): string {
  const lines: string[] = [];

  lines.push(`\n#### ${bubble.name} (${bubble.className})`);
  lines.push(`Type: ${bubble.type} | ${bubble.description}`);

  if (bubble.parameters.length > 0) {
    lines.push('Parameters:');
    for (const param of bubble.parameters) {
      const reqMarker = param.required ? ' (REQUIRED)' : '';
      let typeInfo = param.type;

      if (param.enumValues && param.enumValues.length > 0) {
        typeInfo = `enum: [${param.enumValues.join(', ')}]`;
      }

      const defaultInfo = param.default !== undefined ? ` (default: ${JSON.stringify(param.default)})` : '';
      const desc = param.description ? ` - ${param.description}` : '';

      lines.push(`  - ${param.name}: ${typeInfo}${reqMarker}${defaultInfo}${desc}`);
    }
  }

  return lines.join('\n');
}

/**
 * Format a Composio tool with full parameter details
 */
function formatComposioToolForAI(tool: ComposioToolSummary): string {
  const lines: string[] = [];

  lines.push(`  - ${tool.name}`);
  if (tool.description) {
    lines.push(`    Description: ${tool.description}`);
  }

  if (tool.parameters.length > 0) {
    lines.push(`    Parameters:`);
    for (const param of tool.parameters) {
      const reqMarker = param.required ? ' (REQUIRED)' : '';
      const typeStr = param.enumValues?.length
        ? `enum[${param.enumValues.slice(0, 3).join('|')}${param.enumValues.length > 3 ? '...' : ''}]`
        : param.type;
      const defaultStr = param.default !== undefined ? ` (default: ${JSON.stringify(param.default)})` : '';
      const descStr = param.description ? ` - ${param.description.slice(0, 60)}` : '';

      lines.push(`      - ${param.name}: ${typeStr}${reqMarker}${defaultStr}${descStr}`);
    }
  }

  return lines.join('\n');
}

/**
 * Build the complete context string for the AI system prompt
 */
export function buildContextForAI(context: AIAssistantContext): string {
  const lines: string[] = [];

  // Header
  lines.push('## Available Workflow Components\n');

  // =====================================================
  // Native Bubbles - Services (with FULL details)
  // =====================================================
  lines.push('### Native Service Bubbles');
  lines.push('For these, use: nodeType: "bubble", bubbleType: "service"');

  for (const bubble of context.bubbles.services) {
    lines.push(formatBubbleForAI(bubble));
  }

  // =====================================================
  // Native Bubbles - Tools (with FULL details)
  // =====================================================
  lines.push('\n\n### Native Tool Bubbles');
  lines.push('For these, use: nodeType: "bubble", bubbleType: "tool"');

  for (const bubble of context.bubbles.tools) {
    lines.push(formatBubbleForAI(bubble));
  }

  // =====================================================
  // Native Bubbles - Workflows
  // =====================================================
  if (context.bubbles.workflows.length > 0) {
    lines.push('\n\n### Nested Workflow Bubbles');
    lines.push('For these, use: nodeType: "bubble", bubbleType: "workflow"');

    for (const bubble of context.bubbles.workflows) {
      lines.push(formatBubbleForAI(bubble));
    }
  }

  // =====================================================
  // Composio Integrations
  // =====================================================
  lines.push('\n\n### Composio Integrations');
  lines.push('For these, use: nodeType: "composio" with toolkit and toolName');

  // Connected accounts
  const connectedAccounts = context.composio.connectedAccounts.filter(
    (acc) => acc.status === 'ACTIVE'
  );

  if (connectedAccounts.length > 0) {
    for (const account of connectedAccounts) {
      lines.push(`\n#### ${account.toolkit} [CONNECTED]`);
      // Show all tools - no truncation to ensure AI has full context
      for (const tool of account.tools) {
        lines.push(formatComposioToolForAI(tool));
      }
    }
  }

  // Available but not connected
  const connectedToolkits = new Set(connectedAccounts.map((acc) => acc.toolkit.toUpperCase()));
  const notConnected = context.composio.availableToolkits.filter(
    (toolkit) => !connectedToolkits.has(toolkit.toUpperCase())
  );

  if (notConnected.length > 0) {
    lines.push('\n#### Not Connected:');
    for (const toolkit of notConnected) {
      lines.push(`- ${toolkit}: User needs to connect this first`);
    }
  }

  // =====================================================
  // CRITICAL: Node and Parameter Format Reference
  // =====================================================
  lines.push('\n\n## CRITICAL: Node Format Reference\n');

  lines.push('### Parameter Value Types');
  lines.push('Every parameter value MUST be an object with "type" and "value":');
  lines.push('');
  lines.push('1. Static values (hardcoded):');
  lines.push('   { "type": "static", "value": "your value here" }');
  lines.push('   { "type": "static", "value": 10 }');
  lines.push('   { "type": "static", "value": true }');
  lines.push('');
  lines.push('2. Variable references (output from another node):');
  lines.push('   { "type": "variable", "referencedNodeId": "previous_node_id", "referencedField": "data" }');
  lines.push('');
  lines.push('3. Trigger data (webhook payload):');
  lines.push('   { "type": "variable", "referencedNodeId": "trigger", "referencedField": "payload" }');
  lines.push('   { "type": "variable", "referencedNodeId": "trigger", "referencedField": "payload.query" }');
  lines.push('   { "type": "variable", "referencedNodeId": "trigger", "referencedField": "payload.searchTerm" }');

  lines.push('\n### Complete Node Examples\n');

  lines.push('Example 1: Web Search Tool (getting query from trigger webhook payload)');
  lines.push('```json');
  lines.push(JSON.stringify({
    id: "web_search_1",
    type: "bubble",
    bubbleName: "web-search-tool",
    bubbleType: "tool",
    variableName: "searchResults",
    parameters: {
      query: { type: "variable", referencedNodeId: "trigger", referencedField: "payload.query" },
      limit: { type: "static", value: 10 }
    }
  }, null, 2));
  lines.push('```\n');

  lines.push('Example 2: AI Agent (using output from previous node)');
  lines.push('```json');
  lines.push(JSON.stringify({
    id: "summarize_ai_1",
    type: "bubble",
    bubbleName: "ai-agent",
    bubbleType: "service",
    variableName: "summary",
    parameters: {
      message: { type: "variable", referencedNodeId: "web_search_1", referencedField: "data" },
      model: { type: "static", value: { model: "openai/gpt-5-mini", temperature: 0.7 } },
      systemPrompt: { type: "static", value: "Summarize the search results concisely." }
    }
  }, null, 2));
  lines.push('```\n');

  lines.push('Example 3: Reddit Scrape Tool (with static subreddit)');
  lines.push('```json');
  lines.push(JSON.stringify({
    id: "scrape_reddit_1",
    type: "bubble",
    bubbleName: "reddit-scrape-tool",
    bubbleType: "tool",
    variableName: "redditPosts",
    parameters: {
      subreddit: { type: "static", value: "technology" },
      limit: { type: "static", value: 10 },
      sort: { type: "static", value: "hot" }
    }
  }, null, 2));
  lines.push('```\n');

  lines.push('Example 4: Slack Message (with variable content)');
  lines.push('```json');
  lines.push(JSON.stringify({
    id: "send_slack_1",
    type: "bubble",
    bubbleName: "slack",
    bubbleType: "service",
    variableName: "slackResult",
    parameters: {
      action: { type: "static", value: "sendMessage" },
      channel: { type: "static", value: "#general" },
      text: { type: "variable", referencedNodeId: "summarize_ai_1", referencedField: "data" }
    }
  }, null, 2));
  lines.push('```\n');

  lines.push('Example 5: Composio Gmail (sending email)');
  lines.push('```json');
  lines.push(JSON.stringify({
    id: "send_email_1",
    type: "composio",
    toolkit: "GMAIL",
    toolName: "GMAIL_SEND_EMAIL",
    variableName: "emailResult",
    parameters: {
      recipient_email: { type: "static", value: "user@example.com" },
      subject: { type: "static", value: "Daily Summary" },
      body: { type: "variable", referencedNodeId: "summarize_ai_1", referencedField: "data" }
    }
  }, null, 2));
  lines.push('```\n');

  lines.push('Example 6: Composio tool after cron trigger (standalone data fetching)');
  lines.push('When using Composio tools directly after a cron trigger (no AI agent before), configure parameters with static values:');
  lines.push('```json');
  lines.push(JSON.stringify({
    id: "fetch_emails_1",
    type: "composio",
    toolkit: "GMAIL",
    toolName: "GMAIL_FETCH_EMAILS",
    variableName: "inboxEmails",
    parameters: {
      max_results: { type: "static", value: 50 },
      label_ids: { type: "static", value: ["INBOX"] },
      q: { type: "static", value: "newer_than:1d" }
    }
  }, null, 2));
  lines.push('```');

  // =====================================================
  // Trigger Types
  // =====================================================
  lines.push('\n\n### Trigger Types');
  lines.push('- webhook/http: HTTP webhook trigger. Access payload with: referencedNodeId: "trigger", referencedField: "payload" or "payload.fieldName"');
  lines.push('- schedule/cron: Scheduled trigger. Config: { "cronSchedule": "0 9 * * *" } for daily at 9am');
  lines.push('- slack/bot_mentioned: Slack bot mention trigger');

  // =====================================================
  // CRITICAL: Composio Tool Patterns
  // =====================================================
  lines.push('\n\n### CRITICAL: Composio Tool Patterns');
  lines.push('');
  lines.push('**Data-Fetching Tools (FETCH, LIST, GET, SEARCH):**');
  lines.push('These tools retrieve data and MUST have parameters configured. Two patterns:');
  lines.push('');
  lines.push('Pattern A - Static parameters (for scheduled/automated fetching):');
  lines.push('  Cron Trigger → Composio FETCH tool (with static params) → AI Agent (process data)');
  lines.push('  Example: GMAIL_FETCH_EMAILS with { max_results: 50, q: "newer_than:1d" }');
  lines.push('');
  lines.push('Pattern B - Dynamic parameters (AI generates the query):');
  lines.push('  Trigger → AI Agent (generates search params) → Composio FETCH tool');
  lines.push('  The AI agent outputs JSON matching the tool\'s input schema');
  lines.push('');
  lines.push('**Action Tools (SEND, CREATE, UPDATE, DELETE):**');
  lines.push('These tools perform actions and need an AI Agent BEFORE them to generate parameters:');
  lines.push('  ... → AI Agent (generates action params as JSON) → Composio ACTION tool');
  lines.push('  Example: AI Agent outputs { recipient_email, subject, body } → GMAIL_SEND_EMAIL');
  lines.push('');
  lines.push('**NEVER do this:**');
  lines.push('  - Trigger → Composio tool (without parameters) - THIS WILL FAIL');
  lines.push('  - Composio FETCH tool → AI Agent (without configuring fetch parameters first)');

  // =====================================================
  // Important Rules
  // =====================================================
  lines.push('\n\n### Important Rules');
  lines.push('1. ALWAYS use the exact bubbleName from the list above (e.g., "web-search-tool", NOT "WebSearchTool")');
  lines.push('2. ALWAYS wrap parameter values in { "type": "...", "value": ... } format');
  lines.push('3. For webhook triggers, use referencedNodeId: "trigger" to access payload data');
  lines.push('4. Use referencedField: "data" to get the main output from a previous node');
  lines.push('5. Node IDs must be unique and use snake_case (e.g., "web_search_1", "ai_agent_2")');
  lines.push('6. Edge format: { "source": "node_id_1", "target": "node_id_2" }');
  lines.push('7. The ai-agent model parameter must be an object: { "model": "openai/gpt-5-mini" }');
  lines.push('8. Composio data-fetching tools (FETCH/LIST/GET) MUST have their parameters configured with static values or from an AI agent output');

  return lines.join('\n');
}

/**
 * Build context from bubble registry only (without Composio)
 */
export function buildBubbleOnlyContext(): string {
  const bubbleRegistry = getBubbleRegistryForAI();

  return buildContextForAI({
    bubbles: bubbleRegistry,
    composio: {
      connectedAccounts: [],
      availableToolkits: [],
    },
  });
}

/**
 * Get the list of connected toolkit names from context
 */
export function getConnectedToolkitNames(context: AIAssistantContext): string[] {
  return context.composio.connectedAccounts
    .filter((acc) => acc.status === 'ACTIVE')
    .map((acc) => acc.toolkit);
}

/**
 * Check if a specific toolkit is connected
 */
export function isToolkitConnected(
  context: AIAssistantContext,
  toolkit: string
): boolean {
  return context.composio.connectedAccounts.some(
    (acc) =>
      acc.toolkit.toUpperCase() === toolkit.toUpperCase() &&
      acc.status === 'ACTIVE'
  );
}
