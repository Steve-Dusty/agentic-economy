/**
 * Tag Management Tools (ORG-001: Agent Systems & Tags)
 *
 * MCP tools for managing agent tags - lightweight organizational grouping.
 * Tags enable agents to belong to multiple systems without adding security complexity.
 */

import { z } from "zod";
import { TrinityClient } from "../client.js";
import type { McpAuthContext } from "../types.js";

/**
 * Create tag management tools with the given client
 * @param client - Base Trinity client (provides base URL)
 * @param requireApiKey - Whether API key authentication is enabled
 */
export function createTagTools(
  client: TrinityClient,
  requireApiKey: boolean
) {
  /**
   * Get Trinity client with appropriate authentication
   */
  const getClient = (authContext?: McpAuthContext): TrinityClient => {
    if (requireApiKey) {
      if (!authContext?.mcpApiKey) {
        throw new Error("MCP API key authentication required but no API key found in request context");
      }
      const userClient = new TrinityClient(client.getBaseUrl());
      userClient.setToken(authContext.mcpApiKey);
      return userClient;
    }
    return client;
  };

  return {
    // ========================================================================
    // list_tags - List all unique tags with agent counts
    // ========================================================================
    listTags: {
      name: "list_tags",
      description:
        "List all unique tags in the Trinity platform with their agent counts. " +
        "Returns tags sorted by count (most used first), then alphabetically. " +
        "Tags are lowercase identifiers used for organizing agents into logical groups. " +
        "Use this to discover available tags before filtering or tagging agents.",
      parameters: z.object({}),
      execute: async (_params: unknown, context?: { session?: McpAuthContext }) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const result = await apiClient.listAllTags();
        return JSON.stringify(result, null, 2);
      },
    },

    // ========================================================================
    // get_agent_tags - Get tags for a specific agent
    // ========================================================================
    getAgentTags: {
      name: "get_agent_tags",
      description:
        "Get all tags for a specific agent. " +
        "Returns the agent's tags sorted alphabetically. " +
        "Tags are organization labels - they don't affect permissions or capabilities.",
      parameters: z.object({
        agent_name: z.string().describe("The name of the agent to get tags for"),
      }),
      execute: async (
        { agent_name }: { agent_name: string },
        context?: { session?: McpAuthContext }
      ) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);
        const result = await apiClient.getAgentTags(agent_name);
        return JSON.stringify(result, null, 2);
      },
    },

    // ========================================================================
    // tag_agent - Add a tag to an agent
    // ========================================================================
    tagAgent: {
      name: "tag_agent",
      description:
        "Add a tag to an agent. " +
        "Tags are lowercase alphanumeric strings with hyphens (e.g., 'due-diligence', 'content-ops'). " +
        "An agent can have multiple tags, enabling it to appear in multiple system views. " +
        "Only the agent owner or admin can add tags.",
      parameters: z.object({
        agent_name: z.string().describe("The name of the agent to tag"),
        tag: z.string().describe(
          "The tag to add. Must be lowercase alphanumeric with hyphens only (e.g., 'content-ops', 'shared'). Max 50 characters."
        ),
      }),
      execute: async (
        { agent_name, tag }: { agent_name: string; tag: string },
        context?: { session?: McpAuthContext }
      ) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);

        // Validate tag format
        const normalized = tag.toLowerCase().trim();
        if (!normalized) {
          return JSON.stringify({ error: "Tag cannot be empty" }, null, 2);
        }
        if (normalized.length > 50) {
          return JSON.stringify({ error: "Tag too long (max 50 characters)" }, null, 2);
        }
        if (!/^[a-z0-9-]+$/.test(normalized)) {
          return JSON.stringify({ error: "Tags can only contain lowercase letters, numbers, and hyphens" }, null, 2);
        }

        console.log(`[tag_agent] Adding tag '${normalized}' to agent '${agent_name}'`);
        const result = await apiClient.addAgentTag(agent_name, normalized);
        return JSON.stringify(result, null, 2);
      },
    },

    // ========================================================================
    // untag_agent - Remove a tag from an agent
    // ========================================================================
    untagAgent: {
      name: "untag_agent",
      description:
        "Remove a tag from an agent. " +
        "The agent will no longer appear in system views filtered by this tag. " +
        "Only the agent owner or admin can remove tags.",
      parameters: z.object({
        agent_name: z.string().describe("The name of the agent to untag"),
        tag: z.string().describe("The tag to remove"),
      }),
      execute: async (
        { agent_name, tag }: { agent_name: string; tag: string },
        context?: { session?: McpAuthContext }
      ) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);

        const normalized = tag.toLowerCase().trim();
        console.log(`[untag_agent] Removing tag '${normalized}' from agent '${agent_name}'`);
        const result = await apiClient.removeAgentTag(agent_name, normalized);
        return JSON.stringify(result, null, 2);
      },
    },

    // ========================================================================
    // set_agent_tags - Replace all tags for an agent
    // ========================================================================
    setAgentTags: {
      name: "set_agent_tags",
      description:
        "Replace all tags for an agent with a new set of tags. " +
        "This removes any existing tags and sets exactly the tags provided. " +
        "Use this for bulk tag updates instead of multiple tag/untag calls. " +
        "Only the agent owner or admin can modify tags.",
      parameters: z.object({
        agent_name: z.string().describe("The name of the agent"),
        tags: z.array(z.string()).describe(
          "Array of tags to set. Example: ['due-diligence', 'content-ops', 'shared']"
        ),
      }),
      execute: async (
        { agent_name, tags }: { agent_name: string; tags: string[] },
        context?: { session?: McpAuthContext }
      ) => {
        const authContext = context?.session;
        const apiClient = getClient(authContext);

        // Validate and normalize tags
        const normalized = tags
          .map(t => t.toLowerCase().trim())
          .filter(t => t && t.length <= 50 && /^[a-z0-9-]+$/.test(t));

        const invalid = tags.filter(t => {
          const n = t.toLowerCase().trim();
          return !n || n.length > 50 || !/^[a-z0-9-]+$/.test(n);
        });

        if (invalid.length > 0) {
          console.log(`[set_agent_tags] Warning: Invalid tags ignored: ${invalid.join(', ')}`);
        }

        console.log(`[set_agent_tags] Setting ${normalized.length} tags for agent '${agent_name}'`);
        const result = await apiClient.setAgentTags(agent_name, normalized);
        return JSON.stringify(result, null, 2);
      },
    },
  };
}
