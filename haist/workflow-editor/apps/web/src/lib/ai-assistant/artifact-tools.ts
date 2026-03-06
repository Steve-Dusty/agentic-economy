/**
 * Artifact Tools for the AI Assistant
 *
 * Custom tools that allow the AI to create artifacts and search existing ones.
 */

import { tool } from '@openai/agents';
import { artifactService } from '@/lib/artifacts';
import { findArtifactsForMessage, formatArtifactsForContext } from '@/lib/artifacts/smart-artifact-matcher';

/**
 * Creates artifact tools bound to a specific userId.
 */
export function createArtifactTools(userId: string) {
  const saveToArtifacts = tool({
    name: 'save_to_artifacts',
    description: `Save important information to the user's artifacts for future reference. Use this when the user asks you to remember something, when you produce valuable research/analysis, or when the user explicitly asks to save something. Creates a new artifact with a title, content, and optional tags.`,
    parameters: {
      type: 'object' as const,
      properties: {
        title: {
          type: 'string',
          description: 'Short descriptive title for the artifact, e.g. "Meeting Notes - Q1 Planning"',
        },
        content: {
          type: 'string',
          description: 'The content to save as the first entry of this artifact',
        },
        summary: {
          type: 'string',
          description: 'Optional brief summary of the artifact',
        },
        tags: {
          type: 'array',
          items: { type: 'string' },
          description: 'Tags for categorization, e.g. ["meeting", "planning", "q1"]',
        },
      },
      required: ['title', 'content'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as {
          title: string;
          content: string;
          summary?: string;
          tags?: string[];
        };

        const artifact = await artifactService.create({
          userId,
          title: input.title.trim(),
          summary: input.summary?.trim(),
          tags: input.tags || [],
          firstEntry: {
            content: input.content.trim(),
            source: 'manual',
          },
        });

        return JSON.stringify({
          success: true,
          artifact_id: artifact.id,
          title: artifact.title,
          message: `Saved to artifacts: "${artifact.title}"`,
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to save artifact',
        });
      }
    },
  });

  const searchArtifacts = tool({
    name: 'search_artifacts',
    description: `Search the user's saved artifacts for information. Use this when the user asks about something they previously saved, or when you need context from past conversations/research.`,
    parameters: {
      type: 'object' as const,
      properties: {
        query: {
          type: 'string',
          description: 'Search query to find relevant artifacts',
        },
        max_results: {
          type: 'number',
          description: 'Maximum number of results to return (default: 3)',
        },
      },
      required: ['query'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as { query: string; max_results?: number };

        const artifacts = await findArtifactsForMessage({
          userId,
          message: input.query,
          maxArtifacts: input.max_results || 3,
          minConfidence: 0.5, // Lower threshold for explicit search
        });

        if (artifacts.length === 0) {
          return JSON.stringify({
            success: true,
            count: 0,
            message: 'No matching artifacts found.',
            artifacts: [],
          });
        }

        const results = artifacts.map((a) => ({
          id: a.id,
          title: a.title,
          summary: a.summary,
          tags: a.tags,
          entries: a.entries.slice(0, 3).map((e) => ({
            content: e.content.slice(0, 500),
            source: e.source,
            date: e.createdAt,
          })),
        }));

        return JSON.stringify({
          success: true,
          count: results.length,
          artifacts: results,
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to search artifacts',
        });
      }
    },
  });

  const mergeArtifacts = tool({
    name: 'merge_artifacts',
    description: `Merge two related artifacts into one. Moves all entries from the source artifact into the target artifact, then deletes the source. Use when you find duplicate or closely related artifacts that should be combined.`,
    parameters: {
      type: 'object' as const,
      properties: {
        target_artifact_id: {
          type: 'string',
          description: 'The artifact ID to keep (entries will be merged into this one)',
        },
        source_artifact_id: {
          type: 'string',
          description: 'The artifact ID to merge from and then delete',
        },
      },
      required: ['target_artifact_id', 'source_artifact_id'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as { target_artifact_id: string; source_artifact_id: string };

        // Verify both artifacts exist and belong to the user
        const target = await artifactService.getWithEntries(input.target_artifact_id);
        const source = await artifactService.getWithEntries(input.source_artifact_id);

        if (!target || target.userId !== userId) {
          return JSON.stringify({ success: false, error: 'Target artifact not found' });
        }
        if (!source || source.userId !== userId) {
          return JSON.stringify({ success: false, error: 'Source artifact not found' });
        }

        // Move all entries from source to target
        for (const entry of source.entries) {
          await artifactService.addEntry(target.id, {
            content: entry.content,
            source: entry.source,
            workflowId: entry.workflowId || undefined,
            workflowName: entry.workflowName || undefined,
          });
        }

        // Merge tags
        const mergedTags = [...new Set([...(target.tags || []), ...(source.tags || [])])];
        await artifactService.update(target.id, { tags: mergedTags });

        // Delete source
        await artifactService.delete(source.id);

        return JSON.stringify({
          success: true,
          message: `Merged "${source.title}" into "${target.title}" (${source.entries.length} entries moved)`,
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to merge artifacts',
        });
      }
    },
  });

  const addToArtifact = tool({
    name: 'add_to_artifact',
    description: `Add a new entry to an existing artifact. Use this when the user wants to add information to a specific artifact they already have (e.g., "add this to my scheduling artifact"). You can specify the artifact by ID or search by title. If searching by title, the closest matching artifact will be used.`,
    parameters: {
      type: 'object' as const,
      properties: {
        artifact_id: {
          type: 'string',
          description: 'The artifact ID to add to (if known). Either artifact_id or artifact_title is required.',
        },
        artifact_title: {
          type: 'string',
          description: 'Search for an artifact by title (if ID is not known). The closest match will be used.',
        },
        content: {
          type: 'string',
          description: 'The content to add as a new entry to the artifact',
        },
      },
      required: ['content'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as {
          artifact_id?: string;
          artifact_title?: string;
          content: string;
        };

        let artifactId = input.artifact_id;

        // If no ID, search by title
        if (!artifactId && input.artifact_title) {
          const matches = await findArtifactsForMessage({
            userId,
            message: input.artifact_title,
            maxArtifacts: 1,
            minConfidence: 0.3,
          });
          if (matches.length > 0) {
            artifactId = matches[0].id;
          } else {
            return JSON.stringify({
              success: false,
              error: `No artifact found matching "${input.artifact_title}". Use save_to_artifacts to create a new one.`,
            });
          }
        }

        if (!artifactId) {
          return JSON.stringify({
            success: false,
            error: 'Either artifact_id or artifact_title is required.',
          });
        }

        // Verify artifact exists and belongs to user
        const artifact = await artifactService.getWithEntries(artifactId);
        if (!artifact || artifact.userId !== userId) {
          return JSON.stringify({ success: false, error: 'Artifact not found' });
        }

        const entry = await artifactService.addEntry(artifactId, {
          content: input.content.trim(),
          source: 'manual',
        });

        return JSON.stringify({
          success: true,
          artifact_id: artifactId,
          artifact_title: artifact.title,
          entry_id: entry.id,
          message: `Added entry to "${artifact.title}"`,
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to add to artifact',
        });
      }
    },
  });

  return [saveToArtifacts, searchArtifacts, mergeArtifacts, addToArtifact];
}
