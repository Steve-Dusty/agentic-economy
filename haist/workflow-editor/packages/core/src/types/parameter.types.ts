/**
 * Parameter types for BubbleLab workflow nodes
 */

/**
 * Supported parameter value types
 */
export enum ParameterType {
  STRING = 'string',
  NUMBER = 'number',
  BOOLEAN = 'boolean',
  OBJECT = 'object',
  ARRAY = 'array',
  ENV = 'env',
  VARIABLE = 'variable',
  EXPRESSION = 'expression',
}

/**
 * A parameter value with type information
 */
export interface ParameterValue {
  /** The type of the parameter */
  type: ParameterType;
  /** The actual value */
  value: string | number | boolean | object | unknown[];
  /** Variable ID if type is VARIABLE */
  variableId?: number;
  /** Referenced node ID for variable references */
  referencedNodeId?: string;
  /** Referenced output field name */
  referencedField?: string;
}

/**
 * Schema definition for a parameter
 */
export interface ParameterDefinition {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array' | 'enum';
  required: boolean;
  default?: unknown;
  description: string;
  enumValues?: string[];
  objectSchema?: Record<string, ParameterDefinition>;
  arrayItemType?: ParameterDefinition;
}

/**
 * Schema property for display purposes
 */
export interface SchemaProperty {
  type: string;
  description?: string;
  required?: boolean;
  properties?: Record<string, SchemaProperty>;
  items?: SchemaProperty;
  enum?: string[];
}

/**
 * Full schema definition
 */
export interface SchemaDefinition {
  type: string;
  properties?: Record<string, SchemaProperty>;
  required?: string[];
}

/**
 * Create a string parameter value
 */
export function createStringParam(value: string): ParameterValue {
  return { type: ParameterType.STRING, value };
}

/**
 * Create a number parameter value
 */
export function createNumberParam(value: number): ParameterValue {
  return { type: ParameterType.NUMBER, value };
}

/**
 * Create a boolean parameter value
 */
export function createBooleanParam(value: boolean): ParameterValue {
  return { type: ParameterType.BOOLEAN, value };
}

/**
 * Create an environment variable reference
 */
export function createEnvParam(envName: string): ParameterValue {
  return { type: ParameterType.ENV, value: envName };
}

/**
 * Create a variable reference to another node's output
 */
export function createVariableParam(
  referencedNodeId: string,
  referencedField?: string
): ParameterValue {
  return {
    type: ParameterType.VARIABLE,
    value: referencedField ? `${referencedNodeId}.${referencedField}` : referencedNodeId,
    referencedNodeId,
    referencedField,
  };
}

/**
 * Create an expression parameter (raw JavaScript)
 */
export function createExpressionParam(expression: string): ParameterValue {
  return { type: ParameterType.EXPRESSION, value: expression };
}
