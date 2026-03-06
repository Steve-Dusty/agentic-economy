/**
 * Bubble Details Service
 *
 * Provides rich schema information and usage examples for native bubbles.
 * Used by the AI assistant to understand exact parameter requirements
 * and output schemas for each bubble.
 */

import {
  getBubble,
  BUBBLE_REGISTRY,
  type BubbleDefinition,
} from '@workflow-editor/core';
import type {
  ParameterDefinition,
  SchemaDefinition,
  SchemaProperty,
} from '@workflow-editor/core';

/**
 * Detailed bubble information including usage examples and schemas
 */
export interface BubbleDetails {
  success: boolean;
  data?: {
    name: string;
    className: string;
    type: string;
    description: string;
    usageExample: string;
    inputSchema: Record<string, ParameterDefinition>;
    outputSchema: SchemaDefinition;
  };
  error?: string;
}

/**
 * Get detailed information about a native bubble
 */
export function getBubbleDetails(bubbleName: string): BubbleDetails {
  const bubble = getBubble(bubbleName);
  if (!bubble) {
    return { success: false, error: `Bubble '${bubbleName}' not found` };
  }

  return {
    success: true,
    data: {
      name: bubble.name,
      className: bubble.className,
      type: bubble.type,
      description: bubble.longDescription || bubble.shortDescription,
      usageExample: buildUsageExample(bubble),
      inputSchema: bubble.schema,
      outputSchema: bubble.resultSchema,
    },
  };
}

/**
 * Get all available bubble names
 */
export function getAllBubbleNames(): string[] {
  return Object.keys(BUBBLE_REGISTRY);
}

/**
 * Get details for multiple bubbles at once
 */
export function getMultipleBubbleDetails(
  bubbleNames: string[]
): Map<string, BubbleDetails> {
  const results = new Map<string, BubbleDetails>();
  for (const name of bubbleNames) {
    results.set(name, getBubbleDetails(name));
  }
  return results;
}

/**
 * Build a comprehensive usage example for a bubble
 */
function buildUsageExample(bubble: BubbleDefinition): string {
  const lines: string[] = [];
  const varName = toVariableName(bubble.name);

  // Header comment
  lines.push(`// ${bubble.shortDescription}`);
  lines.push(`// Type: ${bubble.type}`);
  if (bubble.authType && bubble.authType !== 'none') {
    lines.push(`// Auth: ${bubble.authType}${bubble.credentialType ? ` (${bubble.credentialType})` : ''}`);
  }
  lines.push('');

  // Build constructor example
  lines.push(`const ${varName} = new ${bubble.className}({`);

  for (const [paramName, param] of Object.entries(bubble.schema)) {
    const exampleValue = getExampleValue(param);
    const reqMarker = param.required ? ' // REQUIRED' : '';
    const desc = param.description ? ` - ${truncateDescription(param.description)}` : '';
    lines.push(`  ${paramName}: ${exampleValue},${reqMarker}${desc}`);
  }

  lines.push(`});`);
  lines.push('');

  // Execution
  lines.push(`const result = await ${varName}.action();`);
  lines.push('');

  // Output schema documentation
  lines.push(`// Output schema (result.data):`);
  lines.push(`// {`);

  if (bubble.resultSchema?.properties) {
    for (const [propName, prop] of Object.entries(bubble.resultSchema.properties)) {
      const typeStr = formatSchemaPropertyType(prop);
      const desc = prop.description ? ` // ${truncateDescription(prop.description)}` : '';
      lines.push(`//   ${propName}: ${typeStr},${desc}`);
    }
  }

  lines.push(`// }`);
  lines.push('');

  // Add success check example
  lines.push(`// Always check success before using data:`);
  lines.push(`if (!result.success) {`);
  lines.push(`  throw new Error(\`${bubble.name} failed: \${result.error}\`);`);
  lines.push(`}`);

  return lines.join('\n');
}

/**
 * Generate an example value for a parameter
 */
function getExampleValue(param: ParameterDefinition): string {
  // Use enum first value if available
  if (param.enumValues?.length) {
    return `"${param.enumValues[0]}"`;
  }

  // Use default if available
  if (param.default !== undefined) {
    return JSON.stringify(param.default);
  }

  // Generate based on type
  switch (param.type) {
    case 'string':
      return `"example ${param.name}"`;
    case 'number':
      return '0';
    case 'boolean':
      return 'false';
    case 'array':
      if (param.arrayItemType) {
        const itemExample = getExampleValue(param.arrayItemType);
        return `[${itemExample}]`;
      }
      return '[]';
    case 'object':
      if (param.objectSchema) {
        return formatObjectSchemaExample(param.objectSchema);
      }
      return '{}';
    case 'enum':
      if (param.enumValues?.length) {
        return `"${param.enumValues[0]}"`;
      }
      return `"<${param.name}>"`;
    default:
      return `"<${param.name}>"`;
  }
}

/**
 * Format an object schema as an inline example
 */
function formatObjectSchemaExample(
  schema: Record<string, ParameterDefinition>
): string {
  const entries: string[] = [];
  for (const [key, prop] of Object.entries(schema)) {
    const value = getExampleValue(prop);
    entries.push(`${key}: ${value}`);
  }
  return `{ ${entries.join(', ')} }`;
}

/**
 * Format a schema property type for display
 */
function formatSchemaPropertyType(prop: SchemaProperty): string {
  if (prop.enum?.length) {
    return `"${prop.enum.join('" | "')}"`;
  }

  if (prop.type === 'object' && prop.properties) {
    const nested = Object.entries(prop.properties)
      .map(([k, v]) => `${k}: ${formatSchemaPropertyType(v)}`)
      .join(', ');
    return `{ ${nested} }`;
  }

  if (prop.type === 'array' && prop.items) {
    return `${formatSchemaPropertyType(prop.items)}[]`;
  }

  return prop.type;
}

/**
 * Convert bubble name to valid variable name
 */
function toVariableName(name: string): string {
  return name.replace(/-/g, '_');
}

/**
 * Truncate long descriptions for readability
 */
function truncateDescription(desc: string, maxLength: number = 60): string {
  if (desc.length <= maxLength) return desc;
  return desc.substring(0, maxLength - 3) + '...';
}

/**
 * Build a context string with all bubble details for the AI
 */
export function buildBubbleDetailsContext(bubbleNames: string[]): string {
  const lines: string[] = [];
  lines.push('## DETAILED BUBBLE SCHEMAS');
  lines.push('Use these exact schemas when creating workflow nodes:\n');

  for (const name of bubbleNames) {
    const details = getBubbleDetails(name);
    if (details.success && details.data) {
      lines.push(`### ${name}`);
      lines.push('```typescript');
      lines.push(details.data.usageExample);
      lines.push('```\n');
    }
  }

  return lines.join('\n');
}
