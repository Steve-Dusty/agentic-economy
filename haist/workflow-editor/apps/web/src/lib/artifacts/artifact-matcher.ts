/**
 * Artifact Matcher
 *
 * Handles semantic matching for artifacts using embeddings.
 * Uses OpenAI's text-embedding-3-small model for generating embeddings.
 */

import OpenAI from 'openai';
import { artifactService } from './artifact-service';
import type {
  Artifact,
  ArtifactWithEntries,
  ArtifactSearchResult,
  FindRelevantOptions,
} from './types';

// Lazy-initialized OpenAI client
let openaiClient: OpenAI | null = null;

/**
 * Get the OpenAI client (lazy initialization)
 */
function getOpenAIClient(): OpenAI | null {
  if (openaiClient) {
    return openaiClient;
  }

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.warn('OPENAI_API_KEY not configured for embeddings');
    return null;
  }

  try {
    openaiClient = new OpenAI({ apiKey });
    return openaiClient;
  } catch (error) {
    console.error('Failed to initialize OpenAI client:', error);
    return null;
  }
}

/**
 * Generate embedding for text using OpenAI
 */
export async function generateEmbedding(text: string): Promise<number[] | null> {
  const client = getOpenAIClient();
  if (!client) {
    console.warn('OpenAI client not available for embedding generation');
    return null;
  }

  try {
    // Truncate text if too long (max ~8000 tokens for embedding model)
    const truncatedText = text.slice(0, 30000);

    const response = await client.embeddings.create({
      model: 'text-embedding-3-small',
      input: truncatedText,
      dimensions: 1536, // Standard dimension for compatibility
    });

    return response.data[0].embedding;
  } catch (error) {
    console.error('Failed to generate embedding:', error);
    return null;
  }
}

/**
 * Calculate cosine similarity between two embeddings
 */
export function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error('Embeddings must have same dimensions');
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }

  const magnitude = Math.sqrt(normA) * Math.sqrt(normB);
  if (magnitude === 0) return 0;

  return dotProduct / magnitude;
}

/**
 * Find relevant artifacts for a query
 * First tries vector search, falls back to text search
 */
export async function findRelevantArtifacts(
  options: FindRelevantOptions
): Promise<ArtifactWithEntries[]> {
  const { userId, query, limit = 3, includeIds = [], excludeIds = [] } = options;

  // First, try to get explicitly included artifacts
  const includedArtifacts: ArtifactWithEntries[] = [];
  for (const id of includeIds) {
    const artifact = await artifactService.getWithEntries(id);
    if (artifact && artifact.userId === userId) {
      includedArtifacts.push(artifact);
    }
  }

  // Calculate how many more we need to find
  const remainingLimit = Math.max(0, limit - includedArtifacts.length);

  if (remainingLimit === 0) {
    return includedArtifacts;
  }

  // Try vector search first
  const embedding = await generateEmbedding(query);
  let matchedArtifacts: ArtifactSearchResult[] = [];

  if (embedding) {
    matchedArtifacts = await artifactService.findSimilar({
      userId,
      embedding,
      threshold: 0.7, // Lower threshold for retrieval (we want more matches)
      limit: remainingLimit + excludeIds.length, // Fetch extra to account for exclusions
    });
  }

  // Fall back to text search if no vector results
  if (matchedArtifacts.length === 0) {
    const textMatches = await artifactService.searchByText(userId, query, remainingLimit + excludeIds.length);
    matchedArtifacts = textMatches.map((a) => ({ artifact: a, similarity: 0.5 }));
  }

  // Filter out excluded and already included artifacts
  const excludeSet = new Set([...excludeIds, ...includeIds]);
  const filteredMatches = matchedArtifacts
    .filter((m) => !excludeSet.has(m.artifact.id))
    .slice(0, remainingLimit);

  // Fetch full artifacts with entries
  const matchedWithEntries: ArtifactWithEntries[] = [];
  for (const match of filteredMatches) {
    const withEntries = await artifactService.getWithEntries(match.artifact.id);
    if (withEntries) {
      matchedWithEntries.push(withEntries);
    }
  }

  // Combine: included first, then matched
  return [...includedArtifacts, ...matchedWithEntries];
}

/**
 * Find the most similar existing artifact for content
 * Used by artifact agent to decide whether to create or update
 */
export async function findMostSimilarArtifact(
  userId: string,
  content: string,
  threshold = 0.85
): Promise<{ artifact: Artifact; similarity: number } | null> {
  const embedding = await generateEmbedding(content);
  if (!embedding) {
    return null;
  }

  const results = await artifactService.findSimilar({
    userId,
    embedding,
    threshold,
    limit: 1,
  });

  if (results.length === 0) {
    return null;
  }

  return results[0];
}

/**
 * Format artifacts for injection into AI agent context
 */
export function formatArtifactsForContext(artifacts: ArtifactWithEntries[]): string {
  if (artifacts.length === 0) {
    return '';
  }

  const sections: string[] = [];

  for (const artifact of artifacts) {
    const lines: string[] = [];
    lines.push(`## ${artifact.title}`);

    if (artifact.summary) {
      lines.push(artifact.summary);
    }

    // Include recent entries (last 3)
    const recentEntries = artifact.entries.slice(0, 3);
    if (recentEntries.length > 0) {
      lines.push('\n### Recent Context:');
      for (const entry of recentEntries) {
        const source = entry.workflowName
          ? `From: ${entry.workflowName}`
          : `Source: ${entry.source}`;
        lines.push(`\n**${source}** (${new Date(entry.createdAt).toLocaleDateString()})`);
        lines.push(entry.content);
      }
    }

    sections.push(lines.join('\n'));
  }

  return sections.join('\n\n---\n\n');
}

/**
 * Update artifact's embedding based on its content
 */
export async function updateArtifactEmbedding(artifactId: string): Promise<void> {
  const artifact = await artifactService.getWithEntries(artifactId);
  if (!artifact) {
    throw new Error('Artifact not found');
  }

  // Combine title, summary, and recent entries for embedding
  const textParts: string[] = [artifact.title];

  if (artifact.summary) {
    textParts.push(artifact.summary);
  }

  // Include content from recent entries
  const recentEntries = artifact.entries.slice(0, 5);
  for (const entry of recentEntries) {
    textParts.push(entry.content);
  }

  const combinedText = textParts.join('\n\n');
  const embedding = await generateEmbedding(combinedText);

  if (embedding) {
    await artifactService.updateEmbedding(artifactId, embedding);
  }
}
