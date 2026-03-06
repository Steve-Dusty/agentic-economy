/**
 * Composio Service
 *
 * Wrapper around @composio/core SDK for workflow editor integration.
 * Handles tool fetching, OAuth authentication, and tool execution.
 */

import { Composio } from '@composio/core';
// crypto import removed — using raw user IDs for Composio entity

/**
 * Connected account from Composio
 */
export interface ConnectedAccount {
  id: string;
  appUniqueId?: string;
  appName?: string;
  status: 'ACTIVE' | 'INITIATED' | 'EXPIRED';
  createdAt?: string;
  updatedAt?: string;
}

/**
 * Tool input schema property (structured)
 */
export interface ToolInputSchemaProperty {
  type: string;
  description?: string;
  required?: boolean;
  enum?: string[];
  default?: unknown;
  properties?: Record<string, ToolInputSchemaProperty>;
  items?: ToolInputSchemaProperty;
}

/**
 * Structured tool input schema
 */
export interface ToolInputSchema {
  properties: Record<string, ToolInputSchemaProperty>;
  required?: string[];
}

/**
 * Composio tool definition
 */
export interface ComposioTool {
  id: string;
  name: string;
  description: string;
  inputSchema?: ToolInputSchema;
  outputSchema?: unknown;
}

/**
 * Auth request response from Composio
 */
export interface AuthRequest {
  redirectUrl?: string;
  authorizationUrl?: string;
  connectionStatus?: string;
  connectedAccountId?: string;
  message?: string;
}

/**
 * Tool execution result
 */
export interface ToolExecutionResult {
  successful: boolean;
  data?: unknown;
  error?: string;
}

/**
 * Trigger type from Composio
 */
export interface TriggerType {
  slug: string;
  name: string;
  description: string;
  instructions?: string;
  toolkit: {
    slug: string;
    name: string;
    logo?: string;
  };
  config: Record<string, unknown>; // JSON Schema for trigger config
  payload: Record<string, unknown>; // Schema of event payload
  version?: string;
}

/**
 * Active trigger instance
 */
export interface TriggerInstance {
  id: string;
  triggerName: string;
  triggerConfig: Record<string, unknown>;
  connectedAccountId: string;
  state: Record<string, unknown>;
  disabledAt: string | null;
  updatedAt: string;
  triggerData?: string;
  uuid?: string;
}

/**
 * ComposioService class
 *
 * Singleton service for interacting with Composio SDK
 */
export class ComposioService {
  private composio: Composio | null = null;
  private initialized = false;

  /**
   * Returns the entity ID for Composio (uses raw user ID)
   */
  private generateSafeEntityId(userId: string): string {
    return userId;
  }

  /**
   * Lazily initialize the Composio SDK
   * This prevents errors at build time when API key is not available
   */
  private getComposio(): Composio | null {
    if (this.initialized) {
      return this.composio;
    }

    this.initialized = true;

    if (!process.env.COMPOSIO_API_KEY) {
      console.warn('COMPOSIO_API_KEY not configured, Composio features disabled');
      return null;
    }

    try {
      this.composio = new Composio({
        apiKey: process.env.COMPOSIO_API_KEY,
        toolkitVersions: {
          github: '20251222_00',
          gmail: '20260108_00',
          googlecalendar: '20251222_00',
          googledrive: '20251222_00',
          googledocs: '20251222_00',
          googlesheets: '20251222_00',
          slack: '20251222_00',
          notion: '20251027_00',
          outlook: '20251230_00',
          linear: '20251027_00',
          canva: '20251027_00',
          exa: '20251222_00',
        },
      });
    } catch (error) {
      console.error('Failed to initialize Composio:', error);
      this.composio = null;
    }

    return this.composio;
  }

  /**
   * Get tools for a specific user and toolkits
   */
  async getUserTools(
    userId: string,
    toolkits?: string[]
  ): Promise<ComposioTool[]> {
    const composio = this.getComposio();
    if (!composio) {
      return [];
    }

    try {
      const entityId = this.generateSafeEntityId(userId);
      // Dynamic toolkit discovery: fetch all connected toolkits if none specified
      const requestedToolkits = toolkits || await this.getAvailableToolkits(userId);
      if (requestedToolkits.length === 0) {
        return []; // No connected toolkits
      }

      const allTools: ComposioTool[] = [];

      // Fetch tools from each toolkit in parallel
      const toolkitPromises = requestedToolkits.map(async (toolkit) => {
        try {
          const toolkitTools = await composio.tools.get(entityId, {
            toolkits: [toolkit],
            limit: 200, // Increase limit to get all tools
          });
          // toolkitTools is an array of tool objects
          return { toolkit, tools: Array.isArray(toolkitTools) ? toolkitTools : [] };
        } catch (error) {
          console.error(`Failed to get tools for ${toolkit}:`, error);
          return { toolkit, tools: [] };
        }
      });

      const results = await Promise.all(toolkitPromises);

      // Merge all tools
      for (const { tools } of results) {
        for (const tool of tools) {
          // Extract tool info from the SDK response
          const toolObj = tool as unknown as {
            name?: string;
            description?: string;
            function?: {
              name?: string;
              description?: string;
              parameters?: {
                type?: string;
                properties?: Record<string, unknown>;
                required?: string[];
              };
            };
          };

          // Extract and transform input schema
          let inputSchema: ToolInputSchema | undefined;
          const params = toolObj.function?.parameters;
          if (params?.properties) {
            inputSchema = this.transformToToolInputSchema(params);
          }

          allTools.push({
            id: toolObj.name || toolObj.function?.name || 'unknown',
            name: toolObj.name || toolObj.function?.name || 'unknown',
            description: toolObj.description || toolObj.function?.description || '',
            inputSchema,
          });
        }
      }

      return allTools;
    } catch (error) {
      console.error('Failed to get user tools:', error);
      return [];
    }
  }

  /**
   * Get user's connected accounts
   */
  async getUserConnectedAccounts(userId: string): Promise<ConnectedAccount[]> {
    const composio = this.getComposio();
    if (!composio) {
      return [];
    }

    try {
      const entityId = this.generateSafeEntityId(userId);
      // Fetch with higher limit to ensure we get all accounts
      const connectedAccounts = await composio.connectedAccounts.list({
        userIds: [entityId],
        limit: 100, // Increase from default to get all accounts
      });

      // Debug: log raw response
      console.log(`[Composio] Raw response for user ${userId}:`, JSON.stringify({
        totalItems: connectedAccounts.items?.length || 0,
        page: (connectedAccounts as Record<string, unknown>).page,
        totalPages: (connectedAccounts as Record<string, unknown>).totalPages,
      }));

      return (connectedAccounts.items || []).map((account: unknown) => {
        const acc = account as Record<string, unknown>;
        return {
          id: acc.id as string,
          appUniqueId: acc.appUniqueId as string | undefined,
          appName:
            (acc.appName as string) ||
            ((acc.toolkit as Record<string, unknown>)?.slug as string) ||
            'unknown',
          status: acc.status as 'ACTIVE' | 'INITIATED' | 'EXPIRED',
          createdAt: acc.createdAt as string | undefined,
          updatedAt: acc.updatedAt as string | undefined,
        };
      });
    } catch (error) {
      console.error('Failed to get connected accounts:', error);
      return [];
    }
  }

  /**
   * Get available toolkits for a user (based on ACTIVE connections)
   */
  async getAvailableToolkits(userId: string): Promise<string[]> {
    const composio = this.getComposio();
    if (!composio) {
      return [];
    }

    try {
      const entityId = this.generateSafeEntityId(userId);
      const connectedAccounts = await composio.connectedAccounts.list({
        userIds: [entityId],
      });

      // Filter for only ACTIVE connections
      const activeAccounts = (connectedAccounts.items || []).filter(
        (account: unknown) =>
          (account as Record<string, unknown>).status === 'ACTIVE'
      );

      // Extract unique app names
      const toolkits = [
        ...new Set(
          activeAccounts
            .map((account: unknown) => {
              const acc = account as Record<string, unknown>;
              return (
                (acc.appUniqueId as string) ||
                (acc.appName as string) ||
                ((acc.toolkit as Record<string, unknown>)?.slug as string)
              );
            })
            .filter(Boolean)
        ),
      ];

      return toolkits as string[];
    } catch (error) {
      console.error('Failed to get available toolkits:', error);
      return [];
    }
  }

  /**
   * Initiate authentication for a specific app
   */
  async initiateAuthentication(
    userId: string,
    appName: string,
    authConfigId: string,
    redirectUrl?: string
  ): Promise<AuthRequest> {
    const composio = this.getComposio();
    if (!composio) {
      throw new Error('Composio SDK not available - API key not configured');
    }

    try {
      const entityId = this.generateSafeEntityId(userId);
      // Check if an ACTIVE connection already exists
      const existingAccounts = await composio.connectedAccounts.list({
        userIds: [entityId],
        authConfigIds: [authConfigId],
      });

      const activeAccount = (existingAccounts.items || []).find(
        (account: unknown) =>
          (account as Record<string, unknown>).status === 'ACTIVE'
      );

      if (activeAccount) {
        return {
          connectionStatus: 'ACTIVE',
          connectedAccountId: (activeAccount as Record<string, unknown>)
            .id as string,
          message: 'Connection already active',
        };
      }

      // Delete any INITIATED accounts to allow retry
      const initiatedAccounts = (existingAccounts.items || []).filter(
        (account: unknown) =>
          (account as Record<string, unknown>).status === 'INITIATED'
      );

      for (const account of initiatedAccounts) {
        try {
          await composio.connectedAccounts.delete(
            (account as Record<string, unknown>).id as string
          );
        } catch {
          // Ignore delete errors
        }
      }

      // Use hosted authentication (Connect Link) - handles OAuth, API keys, and custom fields
      const connectionRequest = await composio.connectedAccounts.link(
        entityId,
        authConfigId,
        {
          callbackUrl: redirectUrl,
        }
      );

      return connectionRequest as AuthRequest;
    } catch (error) {
      console.error('Failed to initiate authentication:', error);
      throw error;
    }
  }

  /**
   * Execute a Composio tool
   */
  async executeTool(
    toolName: string,
    userId: string,
    args: Record<string, unknown>
  ): Promise<ToolExecutionResult> {
    const composio = this.getComposio();
    if (!composio) {
      return {
        successful: false,
        error: 'Composio SDK not available - API key not configured',
      };
    }

    try {
      const entityId = this.generateSafeEntityId(userId);
      const result = await composio.tools.execute(toolName, {
        userId: entityId,
        arguments: args,
      });

      return result as ToolExecutionResult;
    } catch (error) {
      console.error(`Failed to execute tool ${toolName}:`, error);
      return {
        successful: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Transform raw SDK parameters to structured ToolInputSchema
   */
  private transformToToolInputSchema(params: {
    type?: string;
    properties?: Record<string, unknown>;
    required?: string[];
  }): ToolInputSchema {
    const properties: Record<string, ToolInputSchemaProperty> = {};

    if (params.properties) {
      for (const [name, prop] of Object.entries(params.properties)) {
        const propObj = prop as Record<string, unknown>;
        properties[name] = this.transformSchemaProperty(propObj);
      }
    }

    return {
      properties,
      required: params.required,
    };
  }

  /**
   * Transform a single schema property recursively
   */
  private transformSchemaProperty(prop: Record<string, unknown>): ToolInputSchemaProperty {
    const result: ToolInputSchemaProperty = {
      type: (prop.type as string) || 'string',
    };

    if (prop.description) {
      result.description = prop.description as string;
    }

    if (prop.enum) {
      result.enum = prop.enum as string[];
    }

    if (prop.default !== undefined) {
      result.default = prop.default;
    }

    // Handle nested object properties
    if (prop.properties) {
      result.properties = {};
      const nested = prop.properties as Record<string, unknown>;
      for (const [name, nestedProp] of Object.entries(nested)) {
        result.properties[name] = this.transformSchemaProperty(
          nestedProp as Record<string, unknown>
        );
      }
    }

    // Handle array items
    if (prop.items) {
      result.items = this.transformSchemaProperty(
        prop.items as Record<string, unknown>
      );
    }

    return result;
  }

  /**
   * Get a specific tool's details with full schema
   */
  async getToolDetails(
    userId: string,
    toolkit: string,
    toolName: string
  ): Promise<ComposioTool | null> {
    const tools = await this.getUserTools(userId, [toolkit]);
    return tools.find((t) => t.name === toolName) || null;
  }

  /**
   * Get predefined list of available apps
   */
  getAvailableApps() {
    return [
      // Google Services
      { appId: 'GMAIL', name: 'Gmail', description: 'Email management' },
      { appId: 'GOOGLECALENDAR', name: 'Google Calendar', description: 'Calendar management' },
      { appId: 'GOOGLEDRIVE', name: 'Google Drive', description: 'File storage' },
      { appId: 'GOOGLEDOCS', name: 'Google Docs', description: 'Document editing' },
      { appId: 'GOOGLESHEETS', name: 'Google Sheets', description: 'Spreadsheets' },
      { appId: 'GOOGLETASKS', name: 'Google Tasks', description: 'Task management' },
      { appId: 'GOOGLE_MAPS', name: 'Google Maps', description: 'Maps and locations' },
      { appId: 'GOOGLEMEET', name: 'Google Meet', description: 'Video meetings' },
      { appId: 'YOUTUBE', name: 'YouTube', description: 'Video platform' },

      // Microsoft Services
      { appId: 'OUTLOOK', name: 'Outlook', description: 'Microsoft email and calendar' },
      { appId: 'ONE_DRIVE', name: 'OneDrive', description: 'Microsoft cloud storage' },
      { appId: 'MICROSOFT_TEAMS', name: 'Microsoft Teams', description: 'Team collaboration' },

      // Communication
      { appId: 'SLACK', name: 'Slack', description: 'Team communication' },
      { appId: 'DISCORD', name: 'Discord', description: 'Community chat' },

      // Productivity
      { appId: 'NOTION', name: 'Notion', description: 'Notes and productivity' },
      { appId: 'LINEAR', name: 'Linear', description: 'Issue tracking' },
      { appId: 'JIRA', name: 'Jira', description: 'Project management' },
      { appId: 'ASANA', name: 'Asana', description: 'Work management' },
      { appId: 'CALENDLY', name: 'Calendly', description: 'Scheduling' },
      { appId: 'CANVAS', name: 'Canvas', description: 'Learning management' },

      // Development
      { appId: 'GITHUB', name: 'GitHub', description: 'Code repositories' },
      { appId: 'FIGMA', name: 'Figma', description: 'Design collaboration' },

      // Social
      { appId: 'TWITTER', name: 'X (Twitter)', description: 'Social media' },
      { appId: 'LINKEDIN', name: 'LinkedIn', description: 'Professional network' },
      { appId: 'REDDIT', name: 'Reddit', description: 'Community forums' },

      // Design & Creative
      { appId: 'CANVA', name: 'Canva', description: 'Graphic design' },

      // Sales & CRM
      { appId: 'SALESFORCE', name: 'Salesforce', description: 'CRM platform' },
      { appId: 'APOLLO', name: 'Apollo', description: 'Sales intelligence' },

      // Search & Tools
      { appId: 'EXA', name: 'Exa', description: 'AI search' },
      { appId: 'BROWSERBASE_TOOL', name: 'Browserbase', description: 'Browser automation' },
      { appId: 'FIRECRAWL', name: 'Firecrawl', description: 'Web scraping' },
    ];
  }

  // ============================================================
  // TRIGGER MANAGEMENT METHODS
  // ============================================================

  /**
   * Get available trigger types for toolkits
   */
  async getAvailableTriggerTypes(
    toolkitSlugs?: string[]
  ): Promise<TriggerType[]> {
    const composio = this.getComposio();
    if (!composio) {
      return [];
    }

    try {
      const response = await composio.triggers.listTypes({
        toolkits: toolkitSlugs,
        limit: 100,
      });

      return (response.items || []).map((item: unknown) => {
        const t = item as Record<string, unknown>;
        const toolkit = t.toolkit as Record<string, unknown> | undefined;
        return {
          slug: t.slug as string,
          name: t.name as string,
          description: t.description as string,
          instructions: t.instructions as string | undefined,
          toolkit: {
            slug: (toolkit?.slug as string) || '',
            name: (toolkit?.name as string) || '',
            logo: toolkit?.logo as string | undefined,
          },
          config: (t.config as Record<string, unknown>) || {},
          payload: (t.payload as Record<string, unknown>) || {},
          version: t.version as string | undefined,
        };
      });
    } catch (error) {
      console.error('Failed to get trigger types:', error);
      return [];
    }
  }

  /**
   * Get user's active triggers
   */
  async getUserTriggers(
    connectedAccountIds?: string[],
    options?: {
      showDisabled?: boolean;
      triggerNames?: string[];
    }
  ): Promise<TriggerInstance[]> {
    const composio = this.getComposio();
    if (!composio) {
      return [];
    }

    try {
      const response = await composio.triggers.listActive({
        connectedAccountIds,
        showDisabled: options?.showDisabled,
        triggerNames: options?.triggerNames,
      });

      return (response.items || []).map((item: unknown) => {
        const t = item as Record<string, unknown>;
        return {
          id: t.id as string,
          triggerName: t.triggerName as string,
          triggerConfig: (t.triggerConfig as Record<string, unknown>) || {},
          connectedAccountId: t.connectedAccountId as string,
          state: (t.state as Record<string, unknown>) || {},
          disabledAt: t.disabledAt as string | null,
          updatedAt: t.updatedAt as string,
          triggerData: t.triggerData as string | undefined,
          uuid: t.uuid as string | undefined,
        };
      });
    } catch (error) {
      console.error('Failed to get user triggers:', error);
      return [];
    }
  }

  /**
   * Create a new trigger
   */
  async createTrigger(
    userId: string,
    triggerSlug: string,
    connectedAccountId?: string,
    triggerConfig?: Record<string, unknown>
  ): Promise<{ triggerId: string }> {
    const composio = this.getComposio();
    if (!composio) {
      throw new Error('Composio SDK not available - API key not configured');
    }

    try {
      const entityId = this.generateSafeEntityId(userId);
      const result = await composio.triggers.create(entityId, triggerSlug, {
        connectedAccountId,
        triggerConfig,
      });

      return { triggerId: result.triggerId };
    } catch (error) {
      console.error('Failed to create trigger:', error);
      throw error;
    }
  }

  /**
   * Delete a trigger
   */
  async deleteTrigger(triggerId: string): Promise<{ triggerId: string }> {
    const composio = this.getComposio();
    if (!composio) {
      throw new Error('Composio SDK not available - API key not configured');
    }

    try {
      const result = await composio.triggers.delete(triggerId);
      return { triggerId: result.triggerId };
    } catch (error) {
      console.error('Failed to delete trigger:', error);
      throw error;
    }
  }

  /**
   * Enable a trigger
   */
  async enableTrigger(triggerId: string): Promise<{ status: string }> {
    const composio = this.getComposio();
    if (!composio) {
      throw new Error('Composio SDK not available - API key not configured');
    }

    try {
      const result = await composio.triggers.enable(triggerId);
      return { status: (result as { status?: string })?.status || 'success' };
    } catch (error) {
      console.error('Failed to enable trigger:', error);
      throw error;
    }
  }

  /**
   * Disable a trigger
   */
  async disableTrigger(triggerId: string): Promise<{ status: string }> {
    const composio = this.getComposio();
    if (!composio) {
      throw new Error('Composio SDK not available - API key not configured');
    }

    try {
      const result = await composio.triggers.disable(triggerId);
      return { status: (result as { status?: string })?.status || 'success' };
    } catch (error) {
      console.error('Failed to disable trigger:', error);
      throw error;
    }
  }

  /**
   * Get a specific trigger type by slug
   */
  async getTriggerType(slug: string): Promise<TriggerType | null> {
    const composio = this.getComposio();
    if (!composio) {
      return null;
    }

    try {
      const t = (await composio.triggers.getType(slug)) as Record<
        string,
        unknown
      >;
      const toolkit = t.toolkit as Record<string, unknown> | undefined;

      return {
        slug: t.slug as string,
        name: t.name as string,
        description: t.description as string,
        instructions: t.instructions as string | undefined,
        toolkit: {
          slug: (toolkit?.slug as string) || '',
          name: (toolkit?.name as string) || '',
          logo: toolkit?.logo as string | undefined,
        },
        config: (t.config as Record<string, unknown>) || {},
        payload: (t.payload as Record<string, unknown>) || {},
        version: t.version as string | undefined,
      };
    } catch (error) {
      console.error('Failed to get trigger type:', error);
      return null;
    }
  }
}

// Singleton instance
export const composioService = new ComposioService();
