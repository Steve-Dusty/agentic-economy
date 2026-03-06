/**
 * ID generation utilities
 */

/**
 * Generate a unique ID for nodes
 */
export function generateNodeId(prefix = 'node'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Generate a unique ID for edges
 */
export function generateEdgeId(source: string, target: string): string {
  return `edge_${source}_${target}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Generate a variable name from a bubble name
 */
export function generateVariableName(bubbleName: string, existingNames: string[] = []): string {
  // Convert kebab-case to camelCase
  const baseName = bubbleName
    .split('-')
    .map((part, index) =>
      index === 0 ? part : part.charAt(0).toUpperCase() + part.slice(1)
    )
    .join('') + 'Result';

  // Ensure uniqueness
  let name = baseName;
  let counter = 1;
  while (existingNames.includes(name)) {
    name = `${baseName}${counter}`;
    counter++;
  }

  return name;
}

/**
 * Generate a unique workflow ID
 */
export function generateWorkflowId(): string {
  return `workflow_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Generate a short unique ID (8 characters)
 */
export function generateShortId(): string {
  return Math.random().toString(36).substring(2, 10);
}

/**
 * Create a deterministic ID from inputs (for testing)
 */
export function createDeterministicId(...inputs: string[]): string {
  const combined = inputs.join('_');
  let hash = 0;
  for (let i = 0; i < combined.length; i++) {
    const char = combined.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return `id_${Math.abs(hash).toString(36)}`;
}
