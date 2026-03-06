/**
 * Artifact Service
 *
 * In-memory CRUD operations for artifacts and artifact entries.
 * Data resets on server restart.
 */

import type {
  Artifact,
  ArtifactWithEntries,
  ArtifactEntry,
  ArtifactEntrySource,
  CreateArtifactParams,
  UpdateArtifactParams,
  AddEntryParams,
  FindSimilarOptions,
  ArtifactSearchResult,
} from './types';

/** In-memory stores (use globalThis to survive Next.js dev-mode HMR) */
const g = globalThis as unknown as {
  __artifacts?: Map<string, Artifact & { embedding?: number[] }>;
  __artifactEntries?: Map<string, ArtifactEntry>;
};
if (!g.__artifacts) g.__artifacts = new Map();
if (!g.__artifactEntries) g.__artifactEntries = new Map();
const artifacts = g.__artifacts;
const entries = g.__artifactEntries;

/**
 * Generate unique ID
 */
function generateId(prefix: string = ''): string {
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).substring(2, 15);
  return prefix ? `${prefix}_${timestamp}${randomPart}` : `c${timestamp}${randomPart}`;
}

/**
 * Artifact storage operations
 */
export const artifactService = {
  /**
   * Get all artifacts for a user
   */
  async getByUserId(userId: string): Promise<Artifact[]> {
    return Array.from(artifacts.values())
      .filter((a) => a.userId === userId)
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      .map(({ embedding, ...rest }) => rest);
  },

  /**
   * Get a single artifact by ID
   */
  async get(id: string): Promise<Artifact | undefined> {
    const artifact = artifacts.get(id);
    if (!artifact) return undefined;
    const { embedding, ...rest } = artifact;
    return rest;
  },

  /**
   * Get artifact with all its entries
   */
  async getWithEntries(id: string): Promise<ArtifactWithEntries | undefined> {
    const artifact = await this.get(id);
    if (!artifact) return undefined;

    const artifactEntries = Array.from(entries.values())
      .filter((e) => e.artifactId === id)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return {
      ...artifact,
      entries: artifactEntries,
    };
  },

  /**
   * Create a new artifact
   */
  async create(params: CreateArtifactParams): Promise<Artifact> {
    const id = generateId('art');
    const now = new Date().toISOString();

    const artifact: Artifact & { embedding?: number[] } = {
      id,
      userId: params.userId,
      title: params.title,
      summary: params.summary || null,
      tags: params.tags || [],
      createdAt: now,
      updatedAt: now,
      embedding: params.embedding,
    };

    artifacts.set(id, artifact);

    // Add first entry if provided
    if (params.firstEntry) {
      await this.addEntry(id, {
        workflowId: params.firstEntry.workflowId,
        workflowName: params.firstEntry.workflowName,
        content: params.firstEntry.content,
        source: params.firstEntry.source || 'workflow_output',
      });
    }

    const { embedding, ...rest } = artifact;
    return rest;
  },

  /**
   * Update an artifact
   */
  async update(id: string, params: UpdateArtifactParams): Promise<Artifact | undefined> {
    const artifact = artifacts.get(id);
    if (!artifact) return undefined;

    if (params.title !== undefined) artifact.title = params.title;
    if (params.summary !== undefined) artifact.summary = params.summary;
    if (params.tags !== undefined) artifact.tags = params.tags;
    if (params.embedding !== undefined) artifact.embedding = params.embedding;

    artifact.updatedAt = new Date().toISOString();

    const { embedding, ...rest } = artifact;
    return rest;
  },

  /**
   * Delete an artifact and all its entries
   */
  async delete(id: string): Promise<boolean> {
    // Delete entries first
    for (const [entryId, entry] of entries) {
      if (entry.artifactId === id) {
        entries.delete(entryId);
      }
    }

    return artifacts.delete(id);
  },

  /**
   * Add an entry to an artifact
   */
  async addEntry(artifactId: string, params: AddEntryParams): Promise<ArtifactEntry> {
    const id = generateId('ent');
    const now = new Date().toISOString();

    const entry: ArtifactEntry = {
      id,
      artifactId,
      workflowId: params.workflowId || null,
      workflowName: params.workflowName || null,
      content: params.content,
      source: params.source || 'workflow_output',
      createdAt: now,
    };

    entries.set(id, entry);

    // Update artifact's updatedAt timestamp
    const artifact = artifacts.get(artifactId);
    if (artifact) {
      artifact.updatedAt = now;
    }

    return entry;
  },

  /**
   * Get entries for an artifact
   */
  async getEntries(artifactId: string, limit?: number): Promise<ArtifactEntry[]> {
    const filtered = Array.from(entries.values())
      .filter((e) => e.artifactId === artifactId)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return limit ? filtered.slice(0, limit) : filtered;
  },

  /**
   * Delete an entry
   */
  async deleteEntry(entryId: string): Promise<boolean> {
    return entries.delete(entryId);
  },

  /**
   * Find similar artifacts using vector similarity search
   * In-memory version returns empty array (no vector search support)
   */
  async findSimilar(options: FindSimilarOptions): Promise<ArtifactSearchResult[]> {
    // No vector search in-memory -- return empty
    return [];
  },

  /**
   * Search artifacts by text (fallback when vectors not available)
   */
  async searchByText(userId: string, query: string, limit = 5): Promise<Artifact[]> {
    const lowerQuery = query.toLowerCase();
    return Array.from(artifacts.values())
      .filter(
        (a) =>
          a.userId === userId &&
          (a.title.toLowerCase().includes(lowerQuery) ||
            (a.summary && a.summary.toLowerCase().includes(lowerQuery)))
      )
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      .slice(0, limit)
      .map(({ embedding, ...rest }) => rest);
  },

  /**
   * Update an entry's content
   */
  async updateEntry(entryId: string, content: string): Promise<ArtifactEntry> {
    const entry = entries.get(entryId);
    if (!entry) {
      throw new Error('Entry not found');
    }
    entry.content = content;
    return entry;
  },

  /**
   * Update artifact embedding
   */
  async updateEmbedding(id: string, embedding: number[]): Promise<void> {
    const artifact = artifacts.get(id);
    if (artifact) {
      artifact.embedding = embedding;
      artifact.updatedAt = new Date().toISOString();
    }
  },
};
