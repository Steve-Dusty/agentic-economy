/**
 * Composio Details Service
 *
 * Provides rich schema information and usage examples for Composio tools.
 * Used by the AI assistant to understand exact parameter requirements
 * for external integrations like Gmail, Slack, etc.
 */

import { composioService } from '@/lib/composio/composio-service';
import type {
  ComposioTool,
  ToolInputSchema,
  ToolInputSchemaProperty,
} from '@/lib/composio/composio-service';

/**
 * Reference to a Composio tool
 */
export interface ComposioToolRef {
  toolkit: string;
  toolName: string;
}

/**
 * Detailed Composio tool information
 */
export interface ComposioToolDetails {
  success: boolean;
  data?: {
    toolkit: string;
    toolName: string;
    description: string;
    usageExample: string;
    inputSchema: ToolInputSchema | null;
    outputSchema: string;
  };
  error?: string;
}

/**
 * Get detailed information about a Composio tool
 */
export async function getComposioToolDetails(
  userId: string,
  toolkit: string,
  toolName: string
): Promise<ComposioToolDetails> {
  try {
    const tools = await composioService.getUserTools(userId, [toolkit]);
    const tool = tools.find((t) => t.name === toolName);

    if (!tool) {
      return {
        success: false,
        error: `Tool '${toolName}' not found in toolkit '${toolkit}'`,
      };
    }

    return {
      success: true,
      data: {
        toolkit,
        toolName: tool.name,
        description: tool.description,
        usageExample: buildComposioUsageExample(toolkit, tool),
        inputSchema: tool.inputSchema || null,
        outputSchema: `{ data: object, successful: boolean, error?: string }`,
      },
    };
  } catch (error) {
    return {
      success: false,
      error: `Failed to fetch tool details: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

/**
 * Get details for multiple Composio tools at once
 */
export async function getMultipleComposioToolDetails(
  userId: string,
  toolRefs: ComposioToolRef[]
): Promise<Map<string, ComposioToolDetails>> {
  const results = new Map<string, ComposioToolDetails>();

  // Group by toolkit for efficient fetching
  const byToolkit = new Map<string, string[]>();
  for (const ref of toolRefs) {
    const existing = byToolkit.get(ref.toolkit) || [];
    existing.push(ref.toolName);
    byToolkit.set(ref.toolkit, existing);
  }

  // Fetch tools for each toolkit
  for (const [toolkit, toolNames] of byToolkit) {
    try {
      const tools = await composioService.getUserTools(userId, [toolkit]);

      for (const toolName of toolNames) {
        const key = `${toolkit}/${toolName}`;
        const tool = tools.find((t) => t.name === toolName);

        if (tool) {
          results.set(key, {
            success: true,
            data: {
              toolkit,
              toolName: tool.name,
              description: tool.description,
              usageExample: buildComposioUsageExample(toolkit, tool),
              inputSchema: tool.inputSchema || null,
              outputSchema: `{ data: object, successful: boolean, error?: string }`,
            },
          });
        } else {
          results.set(key, {
            success: false,
            error: `Tool '${toolName}' not found in toolkit '${toolkit}'`,
          });
        }
      }
    } catch (error) {
      // Mark all tools in this toolkit as failed
      for (const toolName of toolNames) {
        const key = `${toolkit}/${toolName}`;
        results.set(key, {
          success: false,
          error: `Failed to fetch toolkit '${toolkit}': ${error instanceof Error ? error.message : String(error)}`,
        });
      }
    }
  }

  return results;
}

/**
 * Build a comprehensive usage example for a Composio tool
 */
function buildComposioUsageExample(toolkit: string, tool: ComposioTool): string {
  const lines: string[] = [];

  // Header
  lines.push(`// Composio Integration: ${toolkit}`);
  lines.push(`// Tool: ${tool.name}`);
  lines.push(`// ${tool.description}`);
  lines.push('');

  // Node configuration for workflow
  lines.push('// Workflow Node Configuration:');
  lines.push(`// {`);
  lines.push(`//   type: "composio",`);
  lines.push(`//   toolkit: "${toolkit}",`);
  lines.push(`//   toolName: "${tool.name}",`);
  lines.push(`//   parameters: { ... }`);
  lines.push(`// }`);
  lines.push('');

  // Input parameters
  lines.push('// Input Parameters:');

  if (tool.inputSchema?.properties) {
    const required = tool.inputSchema.required || [];

    for (const [name, prop] of Object.entries(tool.inputSchema.properties)) {
      const isRequired = required.includes(name);
      const reqMarker = isRequired ? ' (REQUIRED)' : '';
      const typeStr = formatPropertyType(prop);
      const desc = prop.description
        ? ` - ${truncateDescription(prop.description)}`
        : '';
      lines.push(`//   ${name}: ${typeStr}${reqMarker}${desc}`);
    }
  } else {
    lines.push('//   (No schema available - check Composio documentation)');
  }

  lines.push('');

  // Output schema
  lines.push('// Output Schema:');
  lines.push('// {');
  lines.push('//   data: <response object>,  // Tool-specific response data');
  lines.push('//   successful: boolean,       // Whether the operation succeeded');
  lines.push('//   error?: string            // Error message if failed');
  lines.push('// }');
  lines.push('');

  // Usage example
  lines.push('// Example parameter values:');
  lines.push('// parameters: {');

  if (tool.inputSchema?.properties) {
    const required = tool.inputSchema.required || [];

    for (const [name, prop] of Object.entries(tool.inputSchema.properties)) {
      const isRequired = required.includes(name);
      if (isRequired) {
        const exampleValue = getExampleValue(name, prop);
        lines.push(`//   ${name}: { type: "static", value: ${exampleValue} },`);
      }
    }
  }

  lines.push('// }');

  return lines.join('\n');
}

/**
 * Format a property type for display
 */
function formatPropertyType(prop: ToolInputSchemaProperty): string {
  if (prop.enum?.length) {
    if (prop.enum.length <= 3) {
      return `"${prop.enum.join('" | "')}"`;
    }
    return `enum[${prop.enum.length} values]`;
  }

  if (prop.type === 'object' && prop.properties) {
    return 'object';
  }

  if (prop.type === 'array' && prop.items) {
    return `${prop.items.type}[]`;
  }

  return prop.type;
}

/**
 * Generate an example value for a parameter
 */
function getExampleValue(name: string, prop: ToolInputSchemaProperty): string {
  // Use default if available
  if (prop.default !== undefined) {
    return JSON.stringify(prop.default);
  }

  // Use first enum value if available
  if (prop.enum?.length) {
    return `"${prop.enum[0]}"`;
  }

  // Generate based on type and common naming patterns
  switch (prop.type) {
    case 'string':
      // Common field name patterns
      if (name.includes('email')) return '"user@example.com"';
      if (name.includes('channel')) return '"#general"';
      if (name.includes('url')) return '"https://example.com"';
      if (name.includes('id')) return '"<id>"';
      return `"example_${name}"`;
    case 'number':
    case 'integer':
      return '0';
    case 'boolean':
      return 'false';
    case 'array':
      return '[]';
    case 'object':
      return '{}';
    default:
      return `"<${name}>"`;
  }
}

/**
 * Truncate long descriptions for readability
 */
function truncateDescription(desc: string, maxLength: number = 80): string {
  if (desc.length <= maxLength) return desc;
  return desc.substring(0, maxLength - 3) + '...';
}

/**
 * Build a context string with all Composio tool details for the AI
 */
export function buildComposioDetailsContext(
  toolDetails: Map<string, ComposioToolDetails>
): string {
  const lines: string[] = [];
  lines.push('## DETAILED COMPOSIO TOOL SCHEMAS');
  lines.push('Use these exact schemas when creating Composio nodes:\n');

  for (const [key, details] of toolDetails) {
    if (details.success && details.data) {
      lines.push(`### ${key}`);
      lines.push('```typescript');
      lines.push(details.data.usageExample);
      lines.push('```\n');
    }
  }

  return lines.join('\n');
}
