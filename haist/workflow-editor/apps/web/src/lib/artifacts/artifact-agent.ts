/**
 * Artifact Agent
 *
 * Analyzes workflow output after execution and creates/updates artifacts.
 * Uses AI to extract key context and semantically match existing artifacts.
 */

import OpenAI from 'openai';
import { artifactService } from './artifact-service';
import {
  generateEmbedding,
  findMostSimilarArtifact,
  updateArtifactEmbedding,
} from './artifact-matcher';
import type {
  WorkflowOutput,
  ArtifactUpdateResult,
  Artifact,
} from './types';

// Lazy-initialized OpenAI client
let openaiClient: OpenAI | null = null;

function getOpenAIClient(): OpenAI | null {
  if (openaiClient) return openaiClient;

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.warn('OPENAI_API_KEY not configured for artifact agent');
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
 * Extract key context from workflow output using AI
 */
async function extractContext(output: WorkflowOutput): Promise<string | null> {
  const client = getOpenAIClient();
  if (!client) {
    // Fallback: just stringify the output
    return JSON.stringify(output.result, null, 2).slice(0, 2000);
  }

  try {
    // Build a summary of the workflow output
    const outputSummary = buildOutputSummary(output);

    const response = await client.chat.completions.create({
      model: 'gpt-5-nano-2025-08-07',
      messages: [
        {
          role: 'system',
          content: `You are a detailed context extraction assistant. Your job is to extract and preserve ALL MEANINGFUL CONTENT from workflow execution data that would be useful to remember for future reference.

IMPORTANT - Be THOROUGH and DETAILED. Focus on extracting the ACTUAL DATA and CONTENT, including:
- AI agent responses and generated text (capture the FULL content, not just a summary)
- Data fetched from external services (emails, calendar events, documents, profiles)
- Key entities mentioned (people names, company names, project names, topics, email addresses, phone numbers)
- Important decisions, outcomes, or action items
- Dates, deadlines, and scheduled items
- Relationships between entities
- Specific details, numbers, statistics, or data points
- Any structured information (lists, tables, key-value pairs)

IGNORE and DO NOT include:
- Success/failure status messages
- Technical workflow metadata (node IDs, execution timestamps)
- Generic messages like "workflow completed successfully"
- Empty or null results

If the output contains meaningful content (AI responses, fetched data, etc.), extract and document it COMPREHENSIVELY.
If the output is just success/failure metadata with no real content, respond with "NO_MEANINGFUL_CONTENT".

OUTPUT FORMAT:
- Provide a DETAILED extraction that preserves the important information
- Use clear sections and formatting
- Include specific details, not just high-level summaries
- Aim for 4-8 paragraphs of detailed content when the data warrants it
- Preserve important quotes, data points, and specific information verbatim when relevant`,
        },
        {
          role: 'user',
          content: `Extract the meaningful content from this workflow execution:\n\n${outputSummary}`,
        },
      ],
      max_tokens: 1500,
    });

    return response.choices[0]?.message?.content || null;
  } catch (error) {
    console.error('Failed to extract context:', error);
    // Fallback to raw output
    return JSON.stringify(output.result, null, 2).slice(0, 2000);
  }
}

/**
 * Build a readable summary of workflow output
 */
function buildOutputSummary(output: WorkflowOutput): string {
  const parts: string[] = [];

  // Add main result
  if (output.result !== undefined) {
    parts.push('## Main Result');
    parts.push(typeof output.result === 'string'
      ? output.result
      : JSON.stringify(output.result, null, 2));
  }

  // Add node outputs - include more content per node
  if (output.nodeOutputs) {
    parts.push('\n## Node Outputs');
    for (const [nodeId, nodeOutput] of Object.entries(output.nodeOutputs)) {
      if (nodeOutput.success && nodeOutput.data) {
        const label = nodeOutput.label || nodeId;
        parts.push(`\n### ${label}`);
        // Increased from 500 to 2000 characters per node to capture more detail
        parts.push(typeof nodeOutput.data === 'string'
          ? nodeOutput.data
          : JSON.stringify(nodeOutput.data, null, 2).slice(0, 2000));
      }
    }
  }

  // Increased total limit from 8000 to 12000 to allow more comprehensive context
  return parts.join('\n').slice(0, 12000);
}

/**
 * Generate a title for a new artifact using AI
 */
async function generateTitle(content: string): Promise<string> {
  const client = getOpenAIClient();
  if (!client) {
    // Fallback: use first few words
    return content.split(/\s+/).slice(0, 5).join(' ') + '...';
  }

  try {
    const response = await client.chat.completions.create({
      model: 'gpt-5-nano-2025-08-07',
      messages: [
        {
          role: 'system',
          content: `Generate a descriptive title (5-12 words) that captures the main topic, subject, or theme of the content.

The title should:
- Be specific and informative (not generic like "Research Results" or "Data Summary")
- Include key identifiers like names, topics, or subjects when present
- Be suitable for a knowledge artifact that will accumulate related information over time

Examples of GOOD titles:
- "Interview Research: Sarah Chen - Senior Engineer Candidate"
- "Q4 2024 Marketing Campaign Performance Analysis"
- "Project Apollo Technical Requirements and Timeline"

Examples of BAD titles:
- "Research Summary"
- "Meeting Notes"
- "Data Output"

Return only the title, nothing else.`,
        },
        {
          role: 'user',
          content: content.slice(0, 3000),
        },
      ],
      max_tokens: 50,
    });

    const title = response.choices[0]?.message?.content?.trim();
    return title || 'Untitled Artifact';
  } catch (error) {
    console.error('Failed to generate title:', error);
    return 'Untitled Artifact';
  }
}

/**
 * Generate or update artifact summary using AI
 */
async function generateSummary(
  existingArtifact: Artifact | null,
  newContent: string
): Promise<string | null> {
  const client = getOpenAIClient();
  if (!client) return null;

  try {
    const prompt = existingArtifact
      ? `Update this artifact summary with new information:

Current Summary: ${existingArtifact.summary || 'No existing summary'}

New Information:
${newContent}

Provide a COMPREHENSIVE updated summary (1-2 paragraphs, 4-8 sentences) that:
- Incorporates all key details from the new information
- Preserves important specifics from the existing summary
- Includes relevant names, dates, data points, and actionable items
- Maintains context for future reference`
      : `Create a DETAILED summary for this knowledge artifact:

${newContent}

Provide a comprehensive summary (1-2 paragraphs, 4-8 sentences) that:
- Captures all the key information and details
- Includes specific names, dates, numbers, and data points
- Provides enough context that someone reading just the summary understands the content
- Highlights actionable items or important takeaways`;

    const response = await client.chat.completions.create({
      model: 'gpt-5-nano-2025-08-07',
      messages: [
        {
          role: 'system',
          content: 'You are a detailed summarization assistant. Create comprehensive, informative summaries that preserve important details and context. Never sacrifice important information for brevity.',
        },
        {
          role: 'user',
          content: prompt,
        },
      ],
      max_tokens: 500,
    });

    return response.choices[0]?.message?.content?.trim() || null;
  } catch (error) {
    console.error('Failed to generate summary:', error);
    return null;
  }
}

/**
 * Process workflow output and create/update artifacts
 */
export async function processWorkflowOutput(params: {
  userId: string;
  workflowId: string;
  workflowName: string;
  output: WorkflowOutput;
}): Promise<ArtifactUpdateResult | null> {
  const { userId, workflowId, workflowName, output } = params;

  console.log('[artifact-agent] Processing workflow output:', {
    workflowId,
    workflowName,
    success: output.success,
  });

  // Skip failed workflows
  if (!output.success) {
    console.log('[artifact-agent] Skipping failed workflow');
    return null;
  }

  // Extract key context from the output
  const extractedContent = await extractContext(output);
  if (!extractedContent || extractedContent.length < 50 || extractedContent.includes('NO_MEANINGFUL_CONTENT')) {
    console.log('[artifact-agent] No meaningful content extracted, skipping');
    return null;
  }

  console.log('[artifact-agent] Extracted content length:', extractedContent.length);

  // Find similar existing artifact
  const similarResult = await findMostSimilarArtifact(userId, extractedContent, 0.75);

  if (similarResult && similarResult.similarity > 0.75) {
    // Update existing artifact
    console.log('[artifact-agent] Found similar artifact:', {
      id: similarResult.artifact.id,
      title: similarResult.artifact.title,
      similarity: similarResult.similarity,
    });

    // Add new entry
    const entry = await artifactService.addEntry(similarResult.artifact.id, {
      workflowId,
      workflowName,
      content: extractedContent,
      source: 'workflow_output',
    });

    // Update summary
    const newSummary = await generateSummary(similarResult.artifact, extractedContent);
    if (newSummary) {
      await artifactService.update(similarResult.artifact.id, { summary: newSummary });
    }

    // Update embedding
    await updateArtifactEmbedding(similarResult.artifact.id);

    return {
      action: 'updated',
      artifactId: similarResult.artifact.id,
      artifactTitle: similarResult.artifact.title,
      entryId: entry.id,
    };
  } else {
    // Create new artifact
    console.log('[artifact-agent] Creating new artifact');

    // Generate title
    const title = await generateTitle(extractedContent);

    // Generate embedding
    const embedding = await generateEmbedding(extractedContent);

    // Generate summary
    const summary = await generateSummary(null, extractedContent);

    // Create artifact with first entry
    const artifact = await artifactService.create({
      userId,
      title,
      summary: summary || undefined,
      embedding: embedding || undefined,
      firstEntry: {
        workflowId,
        workflowName,
        content: extractedContent,
        source: 'workflow_output',
      },
    });

    console.log('[artifact-agent] Created new artifact:', {
      id: artifact.id,
      title: artifact.title,
    });

    // Get the entry ID (first entry)
    const entries = await artifactService.getEntries(artifact.id, 1);
    const entryId = entries[0]?.id || '';

    return {
      action: 'created',
      artifactId: artifact.id,
      artifactTitle: artifact.title,
      entryId,
    };
  }
}

/**
 * Artifact Agent class for more structured access
 */
export class ArtifactAgent {
  /**
   * Process workflow output after execution
   */
  async processWorkflowOutput(params: {
    userId: string;
    workflowId: string;
    workflowName: string;
    output: WorkflowOutput;
  }): Promise<ArtifactUpdateResult | null> {
    return processWorkflowOutput(params);
  }
}

// Export singleton instance
export const artifactAgent = new ArtifactAgent();
