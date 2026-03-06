/**
 * Artifact Types
 *
 * Type definitions for the artifact system that stores topic-based
 * context that accumulates knowledge over time.
 */

/**
 * An artifact is a topic-based knowledge unit that accumulates
 * context from multiple workflow runs.
 */
export interface Artifact {
  id: string;
  userId: string;
  title: string;
  summary: string | null;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

/**
 * Artifact with its entries included
 */
export interface ArtifactWithEntries extends Artifact {
  entries: ArtifactEntry[];
}

/**
 * Individual entry within an artifact
 */
export interface ArtifactEntry {
  id: string;
  artifactId: string;
  workflowId: string | null;
  workflowName: string | null;
  content: string;
  source: ArtifactEntrySource;
  createdAt: string;
}

/**
 * Source of an artifact entry
 */
export type ArtifactEntrySource = 'workflow_output' | 'manual' | 'ai_summary';

/**
 * Result from semantic search
 */
export interface ArtifactSearchResult {
  artifact: Artifact;
  similarity: number;
  matchedEntries?: ArtifactEntry[];
}

/**
 * Options for finding similar artifacts
 */
export interface FindSimilarOptions {
  userId: string;
  embedding: number[];
  threshold?: number;
  limit?: number;
}

/**
 * Options for finding relevant artifacts by query
 */
export interface FindRelevantOptions {
  userId: string;
  query: string;
  limit?: number;
  includeIds?: string[];
  excludeIds?: string[];
}

/**
 * Result from artifact agent processing
 */
export interface ArtifactUpdateResult {
  action: 'created' | 'updated';
  artifactId: string;
  artifactTitle: string;
  entryId: string;
}

/**
 * Parameters for creating a new artifact
 */
export interface CreateArtifactParams {
  userId: string;
  title: string;
  summary?: string;
  tags?: string[];
  embedding?: number[];
  firstEntry?: {
    workflowId?: string;
    workflowName?: string;
    content: string;
    source?: ArtifactEntrySource;
  };
}

/**
 * Parameters for updating an artifact
 */
export interface UpdateArtifactParams {
  title?: string;
  summary?: string;
  tags?: string[];
  embedding?: number[];
}

/**
 * Parameters for adding an entry to an artifact
 */
export interface AddEntryParams {
  workflowId?: string;
  workflowName?: string;
  content: string;
  source?: ArtifactEntrySource;
}

/**
 * Workflow output structure for artifact processing
 */
export interface WorkflowOutput {
  result: unknown;
  success: boolean;
  nodeOutputs?: Record<string, {
    data: unknown;
    success: boolean;
    label?: string;
  }>;
}

/**
 * Configuration for artifact retrieval on AI agent nodes
 */
export interface ArtifactConfig {
  /** Enable automatic artifact injection (default: true) */
  autoInject: boolean;
  /** Maximum number of artifacts to inject (default: 3) */
  maxArtifacts: number;
  /** Explicit artifact IDs to always include */
  includeArtifacts?: string[];
  /** Artifact IDs to exclude from injection */
  excludeArtifacts?: string[];
}

/**
 * Default artifact configuration
 */
export const DEFAULT_ARTIFACT_CONFIG: ArtifactConfig = {
  autoInject: true,
  maxArtifacts: 3,
};
