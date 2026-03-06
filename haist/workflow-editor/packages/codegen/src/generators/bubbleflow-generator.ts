/**
 * BubbleFlow code generator
 */

import type {
  WorkflowNode,
  WorkflowEdge,
  TriggerConfig,
  BubbleNodeData,
  TriggerNodeData,
  ComposioNodeData,
  ToolInputSchema,
  ToolInputSchemaProperty,
  ArtifactConfig,
} from '@workflow-editor/core';
import { topologicalSort, getBubble, DEFAULT_ARTIFACT_CONFIG } from '@workflow-editor/core';

/**
 * Enriched schema information from details services
 */
export interface EnrichedSchemaInfo {
  toolName: string;
  toolkit?: string;
  type: 'composio' | 'bubble';
  usageExample: string;
  inputSchema: ToolInputSchema | null;
}

/**
 * Generator input
 */
export interface GeneratorInput {
  /** Workflow name */
  name: string;
  /** Class name for the flow */
  className: string;
  /** Trigger configuration */
  trigger: TriggerConfig;
  /** Workflow nodes */
  nodes: WorkflowNode[];
  /** Workflow edges */
  edges: WorkflowEdge[];
  /** Enriched schemas from details services (optional) */
  enrichedSchemas?: Map<string, EnrichedSchemaInfo>;
}

/**
 * Generator output
 */
export interface GeneratorOutput {
  /** Generated TypeScript code */
  code: string;
  /** Warnings during generation */
  warnings: string[];
}

/**
 * Convert name to valid class name
 */
function toClassName(name: string): string {
  return name
    .replace(/[^a-zA-Z0-9]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join('') + 'Flow';
}

/**
 * Generate import statements
 */
function generateImports(nodes: WorkflowNode[]): string[] {
  const imports = new Set<string>();
  imports.add('BubbleFlow');

  // Add WebhookEvent for payload typing
  imports.add('type WebhookEvent');

  // Add bubble imports
  for (const node of nodes) {
    if ('bubbleName' in node.data && node.data.nodeType === 'bubble') {
      const data = node.data as BubbleNodeData;
      const bubble = getBubble(data.bubbleName);
      if (bubble) {
        imports.add(bubble.className);
      }
    }
  }

  return [`import {\n  ${Array.from(imports).join(',\n  ')},\n} from '@bubblelab/bubble-core';`];
}

/**
 * Parameter value with metadata
 */
interface ParameterValueWithMeta {
  type: string;
  value: unknown;
  referencedNodeId?: string;
  referencedField?: string;
}

/**
 * Map of node IDs to their variable names (for variable references)
 */
type NodeVariableMap = Map<string, string>;

/**
 * Convert a JavaScript object to a JS object literal string (not JSON)
 * This produces unquoted keys for valid identifiers
 */
function toJSObjectLiteral(obj: unknown, indent: number = 0): string {
  const spaces = '  '.repeat(indent);
  const innerSpaces = '  '.repeat(indent + 1);

  if (obj === null) return 'null';
  if (obj === undefined) return 'undefined';
  if (typeof obj === 'string') return `'${obj.replace(/'/g, "\\'")}'`;
  if (typeof obj === 'number' || typeof obj === 'boolean') return String(obj);

  if (Array.isArray(obj)) {
    if (obj.length === 0) return '[]';
    const items = obj.map(item => toJSObjectLiteral(item, indent + 1));
    return `[\n${innerSpaces}${items.join(`,\n${innerSpaces}`)}\n${spaces}]`;
  }

  if (typeof obj === 'object') {
    const entries = Object.entries(obj);
    if (entries.length === 0) return '{}';

    const props = entries.map(([key, val]) => {
      // Check if key is a valid JS identifier (doesn't need quotes)
      const isValidIdentifier = /^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(key);
      const keyStr = isValidIdentifier ? key : `'${key}'`;
      return `${innerSpaces}${keyStr}: ${toJSObjectLiteral(val, indent + 1)}`;
    });

    return `{\n${props.join(',\n')}\n${spaces}}`;
  }

  return String(obj);
}

/**
 * Generate parameter value code
 */
function generateParamValue(
  value: unknown,
  type: string,
  paramMeta?: ParameterValueWithMeta,
  nodeVariableMap?: NodeVariableMap,
  targetType?: string
): string {
  // Handle variable references (dynamic inputs)
  if (type === 'variable' && paramMeta?.referencedNodeId) {
    // Special handling for trigger references
    if (paramMeta.referencedNodeId === 'trigger') {
      const field = paramMeta.referencedField || 'payload';
      // Convert "payload" or "payload.fieldName" to actual reference
      let ref: string;
      if (field === 'payload') {
        ref = 'payload';
      } else if (field.startsWith('payload.')) {
        ref = field; // Already includes "payload."
      } else {
        ref = `payload.${field}`;
      }

      // If target parameter expects a string, stringify the data
      if (targetType === 'string') {
        return `typeof ${ref} === 'string' ? ${ref} : JSON.stringify(${ref})`;
      }
      return ref;
    }

    // Handle node references
    if (nodeVariableMap) {
      const sourceVarName = nodeVariableMap.get(paramMeta.referencedNodeId);
      if (sourceVarName) {
        // Reference the output data from the source node
        const field = paramMeta.referencedField || 'data';
        const ref = `${sourceVarName}.${field}`;

        // If target parameter expects a string, stringify the data
        if (targetType === 'string') {
          return `typeof ${ref} === 'string' ? ${ref} : JSON.stringify(${ref})`;
        }

        return ref;
      }
    }
    // Fallback if source node not found
    return `/* Unknown source: ${paramMeta.referencedNodeId} */ undefined`;
  }

  if (type === 'string' || type === 'enum') {
    // Enum values are strings that should be quoted
    return `'${String(value).replace(/'/g, "\\'")}'`;
  }
  if (type === 'number' || type === 'boolean') {
    return String(value);
  }
  if (type === 'env') {
    return `process.env.${value}`;
  }
  if (type === 'variable') {
    return String(value);
  }
  if (type === 'expression') {
    return String(value);
  }
  if (type === 'object' || type === 'array') {
    // If value is already an object/array, convert to JS object literal
    if (typeof value === 'object' && value !== null) {
      return toJSObjectLiteral(value);
    }
    // If value is a string, try to parse it as JSON
    if (typeof value === 'string' && value.trim()) {
      // Check if it looks like JSON (starts with { or [)
      const trimmed = value.trim();
      if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        try {
          const parsed = JSON.parse(value);
          return toJSObjectLiteral(parsed);
        } catch {
          // Invalid JSON - return empty object/array
          return type === 'array' ? '[]' : '{}';
        }
      }
      // Not JSON-like string - return empty object/array
      return type === 'array' ? '[]' : '{}';
    }
    return type === 'array' ? '[]' : '{}';
  }
  if (typeof value === 'object' && value !== null) {
    return toJSObjectLiteral(value);
  }
  return String(value);
}

/**
 * Connected downstream node info
 */
interface ConnectedNode {
  type: 'composio' | 'bubble';
  data: ComposioNodeData | BubbleNodeData;
  bubbleSchema?: Record<string, { type: string; required: boolean; description: string; enumValues?: string[]; default?: unknown }>;
}

/**
 * Find all downstream nodes connected to a given node via edges
 */
function findConnectedDownstreamNodes(
  nodeId: string,
  allNodes: WorkflowNode[],
  edges: WorkflowEdge[]
): ConnectedNode[] {
  const connectedNodes: ConnectedNode[] = [];

  // Find edges where this node is the source (outgoing connections)
  const outgoingEdges = edges.filter((e) => e.source === nodeId);

  for (const edge of outgoingEdges) {
    const targetNode = allNodes.find((n) => n.id === edge.target);
    if (!targetNode) continue;

    if (targetNode.data?.nodeType === 'composio') {
      const composioData = targetNode.data as ComposioNodeData;
      if (composioData.toolName) {
        connectedNodes.push({ type: 'composio', data: composioData });
      }
    } else if (targetNode.data?.nodeType === 'bubble') {
      const bubbleData = targetNode.data as BubbleNodeData;
      const bubbleDef = getBubble(bubbleData.bubbleName);
      if (bubbleDef) {
        connectedNodes.push({
          type: 'bubble',
          data: bubbleData,
          bubbleSchema: bubbleDef.schema,
        });
      }
    }
  }

  return connectedNodes;
}

/**
 * Find Composio nodes connected to a given node via edges
 */
function findConnectedComposioTools(
  nodeId: string,
  allNodes: WorkflowNode[],
  edges: WorkflowEdge[]
): ComposioNodeData[] {
  const connectedNodes = findConnectedDownstreamNodes(nodeId, allNodes, edges);
  return connectedNodes
    .filter((n) => n.type === 'composio')
    .map((n) => n.data as ComposioNodeData);
}

/**
 * Build an example value from a schema property
 */
function buildExampleValue(prop: ToolInputSchemaProperty, name: string): unknown {
  if (prop.enum && prop.enum.length > 0) {
    return prop.enum[0];
  }
  if (prop.default !== undefined) {
    return prop.default;
  }

  switch (prop.type) {
    case 'string':
      return `<${name}>`;
    case 'number':
    case 'integer':
      return 0;
    case 'boolean':
      return false;
    case 'array':
      return [];
    case 'object':
      if (prop.properties) {
        const obj: Record<string, unknown> = {};
        for (const [key, nestedProp] of Object.entries(prop.properties)) {
          obj[key] = buildExampleValue(nestedProp, key);
        }
        return obj;
      }
      return {};
    default:
      return `<${name}>`;
  }
}

/**
 * Build an example JSON object from a tool input schema
 */
function buildExampleFromSchema(schema: ToolInputSchema): Record<string, unknown> {
  const example: Record<string, unknown> = {};
  const requiredParams = schema.required || [];

  for (const [name, prop] of Object.entries(schema.properties)) {
    // Include required params and some optional ones
    if (requiredParams.includes(name) || Object.keys(example).length < 5) {
      example[name] = buildExampleValue(prop, name);
    }
  }

  return example;
}

/**
 * Build tool instructions from structured schema
 */
/**
 * Escape a string for safe inclusion in a template literal
 * Escapes backticks, ${, and other problematic characters
 */
function escapeForTemplateLiteral(str: string): string {
  return str
    .replace(/\\/g, '\\\\')      // Escape backslashes first
    .replace(/`/g, '\\`')        // Escape backticks
    .replace(/\$\{/g, '\\${')    // Escape template expressions
    .replace(/\n/g, ' ')         // Replace newlines with spaces
    .replace(/\r/g, '');         // Remove carriage returns
}

function buildToolInstructionsFromSchema(
  tool: ComposioNodeData,
  enrichedInfo?: EnrichedSchemaInfo
): string {
  // Use enriched schema if available, otherwise fall back to node data
  const schema = enrichedInfo?.inputSchema || tool.toolInputSchema;

  // Fallback to legacy string format if no structured schema
  if (!schema) {
    return `Tool: ${tool.toolName}\\nDescription: ${escapeForTemplateLiteral(tool.toolDescription || 'Execute ' + tool.toolName)}\\nRequired Parameters: ${escapeForTemplateLiteral(tool.toolInputs || 'See documentation')}`;
  }

  const requiredParams = schema.required || [];

  // Build parameter descriptions - escape descriptions for template literal safety
  const paramDescriptions = Object.entries(schema.properties)
    .map(([name, prop]) => {
      const isRequired = requiredParams.includes(name);
      const reqMarker = isRequired ? ' (REQUIRED)' : ' (optional)';
      const enumVals = prop.enum ? ` [${prop.enum.slice(0, 5).join('|')}${prop.enum.length > 5 ? '...' : ''}]` : '';
      const desc = prop.description ? ` - ${escapeForTemplateLiteral(prop.description)}` : '';
      return `  "${name}": ${prop.type}${reqMarker}${enumVals}${desc}`;
    })
    .join('\\n');

  // Build example from schema
  const example = buildExampleFromSchema(schema);
  const exampleJson = JSON.stringify(example, null, 2).replace(/\n/g, '\\n').replace(/"/g, '\\"');

  // Include usage example from enriched data if available
  const toolDesc = escapeForTemplateLiteral(tool.toolDescription || 'Execute ' + tool.toolName);
  let instructions = `TOOL: ${tool.toolName}\\nDescription: ${toolDesc}\\n\\nPARAMETERS (use these EXACT field names):\\n${paramDescriptions}\\n\\nEXAMPLE JSON OUTPUT:\\n${exampleJson}`;

  if (enrichedInfo?.usageExample) {
    // Extract just the parameter hints from usage example (not full code)
    const usageLines = enrichedInfo.usageExample.split('\n')
      .filter(line => line.includes('REQUIRED') || line.includes('Parameters:'))
      .slice(0, 10)
      .map(line => escapeForTemplateLiteral(line))
      .join('\\n');
    if (usageLines) {
      instructions += `\\n\\nADDITIONAL NOTES:\\n${usageLines}`;
    }
  }

  return instructions;
}

/**
 * Build instructions from bubble schema (for downstream bubble nodes)
 */
function buildBubbleInstructionsFromSchema(
  node: ConnectedNode,
  enrichedInfo?: EnrichedSchemaInfo
): string {
  if (node.type !== 'bubble' || !node.bubbleSchema) return '';

  const bubbleData = node.data as BubbleNodeData;
  const schema = node.bubbleSchema;

  // Build parameter descriptions
  const paramDescriptions = Object.entries(schema)
    .map(([name, prop]) => {
      const reqMarker = prop.required ? ' (REQUIRED)' : ' (optional)';
      const enumVals = prop.enumValues ? ` [${prop.enumValues.join('|')}]` : '';
      const desc = prop.description ? ` - ${prop.description}` : '';
      return `  "${name}": ${prop.type}${reqMarker}${enumVals}${desc}`;
    })
    .join('\\n');

  // Build example from schema
  const example: Record<string, unknown> = {};
  for (const [name, prop] of Object.entries(schema)) {
    if (prop.required || Object.keys(example).length < 5) {
      if (prop.enumValues && prop.enumValues.length > 0) {
        example[name] = prop.enumValues[0];
      } else if (prop.default !== undefined) {
        example[name] = prop.default;
      } else if (prop.type === 'string') {
        example[name] = `<${name}>`;
      } else if (prop.type === 'number') {
        example[name] = 0;
      } else if (prop.type === 'boolean') {
        example[name] = false;
      } else if (prop.type === 'object') {
        example[name] = {};
      } else if (prop.type === 'array') {
        example[name] = [];
      } else {
        example[name] = `<${name}>`;
      }
    }
  }
  const exampleJson = JSON.stringify(example, null, 2).replace(/\n/g, '\\n').replace(/"/g, '\\"');

  let instructions = `BUBBLE: ${bubbleData.bubbleName}\\nDescription: ${bubbleData.description || bubbleData.label || 'Execute ' + bubbleData.bubbleName}\\n\\nPARAMETERS (use these EXACT field names):\\n${paramDescriptions}\\n\\nEXAMPLE JSON OUTPUT:\\n${exampleJson}`;

  // Include usage example from enriched data if available
  if (enrichedInfo?.usageExample) {
    const usageLines = enrichedInfo.usageExample.split('\n')
      .filter(line => line.includes('REQUIRED') || line.includes('Parameters:'))
      .slice(0, 10)
      .join('\\n');
    if (usageLines) {
      instructions += `\\n\\nADDITIONAL NOTES:\\n${usageLines}`;
    }
  }

  return instructions;
}

/**
 * Build artifact context instructions for AI agent system prompt
 * When artifacts are enabled, this creates a placeholder for runtime artifact injection
 */
function buildArtifactContextInstructions(artifactConfig: ArtifactConfig): string {
  if (!artifactConfig.autoInject) {
    return '';
  }

  // This creates a template that will be populated at runtime with actual artifact content
  // The payload.artifactContext will be populated by the workflow executor before calling the AI agent
  return `---RELEVANT CONTEXT FROM YOUR KNOWLEDGE BASE---\\n\${payload.artifactContext || 'No relevant artifacts found.'}\\n---END KNOWLEDGE BASE CONTEXT---\\n\\nUse the above context when relevant to the user's request. If the context contains information about the topic being discussed, incorporate it into your response.\\n\\n`;
}

/**
 * Generate bubble instantiation code
 */
function generateBubbleCode(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  edges: WorkflowEdge[],
  nodeVariableMap: NodeVariableMap,
  enrichedSchemas?: Map<string, EnrichedSchemaInfo>
): string {
  const data = node.data as BubbleNodeData;
  const bubble = getBubble(data.bubbleName);
  if (!bubble) return '';

  // For AI agent bubbles, check for connected downstream nodes and build schema-aware instructions
  let hasDownstreamNodes = false;
  let downstreamInstructions = '';
  let artifactInstructions = '';

  if (data.bubbleName === 'ai-agent') {
    // Handle artifact context injection
    const artifactConfig = data.artifactConfig || DEFAULT_ARTIFACT_CONFIG;
    if (artifactConfig.autoInject) {
      artifactInstructions = buildArtifactContextInstructions(artifactConfig);
    }
    const connectedNodes = findConnectedDownstreamNodes(node.id, allNodes, edges);
    if (connectedNodes.length > 0) {
      hasDownstreamNodes = true;

      // Build instructions from all connected nodes (Composio tools and Bubble nodes)
      const allInstructions: string[] = [];

      for (const connectedNode of connectedNodes) {
        if (connectedNode.type === 'composio') {
          const composioData = connectedNode.data as ComposioNodeData;
          // Look up enriched schema if available
          const enrichedKey = `composio/${composioData.toolkit}/${composioData.toolName}`;
          const enrichedInfo = enrichedSchemas?.get(enrichedKey);
          allInstructions.push(buildToolInstructionsFromSchema(composioData, enrichedInfo));
        } else if (connectedNode.type === 'bubble') {
          const bubbleData = connectedNode.data as BubbleNodeData;
          // Look up enriched schema if available
          const enrichedKey = `bubble/${bubbleData.bubbleName}`;
          const enrichedInfo = enrichedSchemas?.get(enrichedKey);
          const bubbleInstruction = buildBubbleInstructionsFromSchema(connectedNode, enrichedInfo);
          if (bubbleInstruction) {
            allInstructions.push(bubbleInstruction);
          }
        }
      }

      if (allInstructions.length > 0) {
        const toolInstructions = allInstructions.join('\\n\\n---\\n\\n');

        // Strengthened JSON enforcement prompt with clear role explanation
        downstreamInstructions = `---CRITICAL: YOUR ROLE IS TO OUTPUT DATA FOR A DOWNSTREAM TOOL---\\n\\nIMPORTANT: You are NOT sending emails, creating events, or performing actions directly.\\nYour job is to OUTPUT a JSON object that will be passed to a downstream tool which will perform the action.\\n\\nIf the user asks you to "send an email to X" or "email X", you must OUTPUT JSON with recipient_email set to X.\\nIf the user asks you to "create an event", you must OUTPUT JSON with the event parameters.\\nDO NOT say "I can't send emails" - instead, OUTPUT the JSON parameters for the tool that will send it.\\n\\nCurrent date/time: \${payload.currentDateTime}\\nUser timezone: \${payload.userTimezone}\\n\\nOUTPUT REQUIREMENTS:\\n1. Respond with ONLY a single JSON object - NO text before or after\\n2. NO markdown code blocks (no \\\`\\\`\\\`json)\\n3. NO explanations, comments, or prose\\n4. The JSON will be parsed and passed to the downstream tool\\n\\nPARAMETER RULES:\\n1. Use EXACT parameter names from schema below\\n2. For "timezone" fields, use: \${payload.userTimezone}\\n3. Calculate dates relative to current date/time\\n4. Include ALL mentioned recipients, subjects, bodies, etc. in the JSON\\n\\nDOWNSTREAM TOOL SCHEMA:\\n${toolInstructions}\\n\\nEXAMPLE - If user says "send a summary to john@example.com":\\n{\\n  "recipient_email": "john@example.com",\\n  "subject": "Summary",\\n  "body": "Here is the summary..."\\n}\\n\\nINCORRECT (DO NOT DO):\\n- "I can't send emails directly..."\\n- "Here is the JSON: {...}"\\n- Any text outside the JSON object\\n\\nOUTPUT ONLY THE JSON OBJECT:`;
      }
    }
  }

  const params: string[] = [];
  for (const [paramName, paramValue] of Object.entries(data.parameters)) {
    // ALWAYS prefer schema type to ensure proper type handling (e.g., arrays stay as arrays)
    const schemaType = bubble.schema[paramName]?.type;
    const storedType = paramValue.type;

    // Cast paramValue to include metadata for variable references
    const paramMeta = paramValue as ParameterValueWithMeta;

    // For variable references, use the stored type; otherwise prefer schema type
    const effectiveType = paramMeta.type === 'variable' ? 'variable' : (schemaType || storedType);

    // Generate the value, handling variable references
    // Pass schemaType as targetType so we can properly convert data for string parameters
    let value = generateParamValue(paramValue.value, effectiveType, paramMeta, nodeVariableMap, schemaType);

    // Append artifact and downstream node instructions to systemPrompt using template literal
    if (paramName === 'systemPrompt') {
      const hasInstructions = artifactInstructions || (hasDownstreamNodes && downstreamInstructions);
      if (hasInstructions) {
        // Extract the user's system prompt content and combine with instructions
        if (value.startsWith("'") && value.endsWith("'")) {
          const userPrompt = value.slice(1, -1); // Remove quotes
          // Use template literal for runtime interpolation
          let combinedInstructions = '';
          if (artifactInstructions) {
            combinedInstructions += artifactInstructions;
          }
          if (hasDownstreamNodes && downstreamInstructions) {
            combinedInstructions += downstreamInstructions;
          }
          value = '`' + userPrompt + '\\n\\n' + combinedInstructions + '`';
        }
      }
    }

    params.push(`      ${paramName}: ${value},`);
  }

  // If no systemPrompt was set but we have instructions, add one
  const hasAnyInstructions = artifactInstructions || (hasDownstreamNodes && downstreamInstructions);
  if (hasAnyInstructions && !data.parameters.systemPrompt) {
    let combinedInstructions = '';
    if (artifactInstructions) {
      combinedInstructions += artifactInstructions;
    }
    if (hasDownstreamNodes && downstreamInstructions) {
      combinedInstructions += downstreamInstructions;
    }
    const systemPromptValue = '`You are a helpful assistant.\\n\\n' + combinedInstructions + '`';
    params.push(`      systemPrompt: ${systemPromptValue},`);
  }

  const paramsStr = params.length > 0 ? `{\n${params.join('\n')}\n    }` : '{}';

  return `    const ${data.variableName} = await new ${bubble.className}(${paramsStr}).action();`;
}

/**
 * Generate the handle method body
 */
function generateHandleBody(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  enrichedSchemas?: Map<string, EnrichedSchemaInfo>
): string {
  const sortedNodes = topologicalSort(nodes, edges);
  const lines: string[] = [];

  // Build a map of node IDs to their variable names for reference resolution
  const nodeVariableMap: NodeVariableMap = new Map();

  // Filter to only bubble nodes
  const bubbleNodes = sortedNodes.filter(
    (n) => 'nodeType' in n.data && n.data.nodeType === 'bubble'
  );

  // Pre-populate the variable map with all bubble nodes
  for (const node of bubbleNodes) {
    const data = node.data as BubbleNodeData;
    nodeVariableMap.set(node.id, data.variableName);
  }

  for (const node of bubbleNodes) {
    const code = generateBubbleCode(node, nodes, edges, nodeVariableMap, enrichedSchemas);
    if (code) {
      lines.push('');
      lines.push(code);
    }
  }

  // Add return statement with all node outputs
  if (bubbleNodes.length > 0) {
    const lastNode = bubbleNodes[bubbleNodes.length - 1];
    const lastData = lastNode.data as BubbleNodeData;
    lines.push('');
    lines.push(`    // Collect all node outputs`);
    lines.push(`    const nodeOutputs: Record<string, { data: unknown; success: boolean; label: string }> = {};`);

    // Add each node's output to the collection
    for (const node of bubbleNodes) {
      const nodeData = node.data as BubbleNodeData;
      const label = nodeData.label || nodeData.bubbleName;
      lines.push(`    nodeOutputs['${node.id}'] = { data: ${nodeData.variableName}.data, success: ${nodeData.variableName}.success, label: '${label.replace(/'/g, "\\'")}' };`);
    }

    lines.push('');
    lines.push(`    return {`);
    lines.push(`      result: ${lastData.variableName}.data,`);
    lines.push(`      success: ${lastData.variableName}.success,`);
    lines.push(`      nodeOutputs,`);
    lines.push(`    };`);
  } else {
    lines.push('    return { success: true, nodeOutputs: {} };');
  }

  return lines.join('\n');
}

/**
 * Generate BubbleFlow TypeScript code
 */
export function generateBubbleFlowCode(input: GeneratorInput): GeneratorOutput {
  const warnings: string[] = [];
  const className = input.className || toClassName(input.name);

  // Generate imports
  const imports = generateImports(input.nodes);

  // Get trigger type
  const triggerType = input.trigger.type;

  // Build class
  const classCode = `
/**
 * ${input.name}
 *
 * Auto-generated by BubbleLab Workflow Editor
 */
${imports.join('\n')}

export class ${className} extends BubbleFlow<'${triggerType}'> {
${triggerType === 'schedule/cron' && input.trigger.cronSchedule ? `  readonly cronSchedule = '${input.trigger.cronSchedule}';\n` : ''}
  async handle(payload: WebhookEvent) {
${generateHandleBody(input.nodes, input.edges, input.enrichedSchemas)}
  }
}
`.trim();

  return {
    code: classCode,
    warnings,
  };
}

/**
 * Quick helper to generate code from workflow store state
 */
export function generateFromWorkflow(
  name: string,
  trigger: TriggerConfig,
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  enrichedSchemas?: Map<string, EnrichedSchemaInfo>
): string {
  const result = generateBubbleFlowCode({
    name,
    className: toClassName(name),
    trigger,
    nodes,
    edges,
    enrichedSchemas,
  });
  return result.code;
}
