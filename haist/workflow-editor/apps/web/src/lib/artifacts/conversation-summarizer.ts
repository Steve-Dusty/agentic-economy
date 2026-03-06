/**
 * Conversation Summarizer
 *
 * Agent that summarizes inactive conversations and stores
 * the summaries in the appropriate artifact.
 */

import OpenAI from 'openai';
import { conversationsStorage } from '@/lib/ai-assistant/conversation-storage';
import { artifactService } from './artifact-service';
import { findMostSimilarArtifact, generateEmbedding } from './artifact-matcher';
import type { Conversation } from '@/lib/ai-assistant/types';

// Lazy-initialized OpenAI client
let openaiClient: OpenAI | null = null;

function getOpenAIClient(): OpenAI | null {
  if (openaiClient) return openaiClient;

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.warn('OPENAI_API_KEY not configured for conversation summarizer');
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
 * Result from summarizing a conversation
 */
export interface SummarizeResult {
  conversationId: string;
  summary: string;
  artifactId: string | null;
  action: 'added_to_existing' | 'created_new' | 'skipped';
  reason?: string;
}

/**
 * Summarize inactive conversations and store in artifacts
 */
export async function summarizeInactiveConversations(): Promise<SummarizeResult[]> {
  const INACTIVITY_THRESHOLD_MS = 2 * 60 * 60 * 1000; // 2 hours
  const results: SummarizeResult[] = [];

  try {
    // Find inactive conversations
    const inactiveConversations = await conversationsStorage.findInactiveConversations(
      INACTIVITY_THRESHOLD_MS
    );

    console.log(`[summarizer] Found ${inactiveConversations.length} inactive conversations`);

    for (const conversation of inactiveConversations) {
      try {
        const result = await summarizeAndStore(conversation);
        results.push(result);

        // Mark as summarized if we actually processed it
        if (result.action !== 'skipped') {
          await conversationsStorage.markAsSummarized(conversation.id);
        }
      } catch (error) {
        console.error(`[summarizer] Failed to summarize conversation ${conversation.id}:`, error);
        results.push({
          conversationId: conversation.id,
          summary: '',
          artifactId: null,
          action: 'skipped',
          reason: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }
  } catch (error) {
    console.error('[summarizer] Failed to find inactive conversations:', error);
  }

  return results;
}

/**
 * Summarize a single conversation and store in appropriate artifact
 */
async function summarizeAndStore(conversation: Conversation): Promise<SummarizeResult> {
  // Get message count
  const messageCount =
    conversation.messages.length + conversation.toolRouterMessages.length;

  // Skip if too few messages — need substantial conversation to be worth saving
  if (messageCount < 8) {
    return {
      conversationId: conversation.id,
      summary: '',
      artifactId: null,
      action: 'skipped',
      reason: 'Too few messages (< 8)',
    };
  }

  const client = getOpenAIClient();
  if (!client) {
    return {
      conversationId: conversation.id,
      summary: '',
      artifactId: null,
      action: 'skipped',
      reason: 'OpenAI client not available',
    };
  }

  // Build conversation text
  const messages =
    conversation.mode === 'tool-router'
      ? conversation.toolRouterMessages
      : conversation.messages;

  const conversationText = messages
    .map((m) => `${m.role.toUpperCase()}: ${m.content}`)
    .join('\n\n');

  // Generate summary
  const response = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      {
        role: 'system',
        content: `You are a knowledge extraction agent. Summarize this conversation into a concise knowledge artifact entry.

Extract and include:
- Main topics discussed
- Key decisions or outcomes
- Important entities (people, projects, companies, products)
- Action items or next steps if any
- Relevant technical details or specifications

Format as 2-3 paragraphs of factual, searchable information.
Focus on information that would be useful to reference later.

If the conversation contains no meaningful content to remember (just greetings, small talk, or incomplete exchanges), respond with exactly: NO_MEANINGFUL_CONTENT`,
      },
      {
        role: 'user',
        content: conversationText,
      },
    ],
    max_tokens: 500,
    temperature: 0.3,
  });

  const summary = response.choices[0]?.message?.content?.trim() || '';

  if (!summary || summary === 'NO_MEANINGFUL_CONTENT') {
    return {
      conversationId: conversation.id,
      summary: '',
      artifactId: null,
      action: 'skipped',
      reason: 'No meaningful content to summarize',
    };
  }

  // Get user ID for this conversation
  const userId = await conversationsStorage.getUserId(conversation.id);
  if (!userId) {
    return {
      conversationId: conversation.id,
      summary,
      artifactId: null,
      action: 'skipped',
      reason: 'Could not determine user ID',
    };
  }

  // Find best matching artifact
  const matchingArtifact = await findMostSimilarArtifact(userId, summary, 0.75);

  if (matchingArtifact && matchingArtifact.similarity >= 0.75) {
    // Add to existing artifact
    await artifactService.addEntry(matchingArtifact.artifact.id, {
      content: summary,
      source: 'ai_summary',
    });

    console.log(
      `[summarizer] Added summary to existing artifact: ${matchingArtifact.artifact.title}`
    );

    return {
      conversationId: conversation.id,
      summary,
      artifactId: matchingArtifact.artifact.id,
      action: 'added_to_existing',
    };
  } else {
    // Create new artifact
    const title = await generateArtifactTitle(summary);
    const embedding = await generateEmbedding(summary);

    const artifact = await artifactService.create({
      userId,
      title,
      summary: summary.substring(0, 500),
      embedding: embedding || undefined,
      firstEntry: {
        content: summary,
        source: 'ai_summary',
      },
    });

    console.log(`[summarizer] Created new artifact: ${title}`);

    return {
      conversationId: conversation.id,
      summary,
      artifactId: artifact.id,
      action: 'created_new',
    };
  }
}

/**
 * Generate a title for a new artifact based on content
 */
async function generateArtifactTitle(content: string): Promise<string> {
  const client = getOpenAIClient();
  if (!client) {
    // Fallback: extract first meaningful phrase
    const firstLine = content.split('\n')[0] || content;
    return firstLine.substring(0, 50).trim() || 'Conversation Summary';
  }

  try {
    const response = await client.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'system',
          content:
            'Generate a short, descriptive title (max 5 words) for this knowledge artifact. The title should capture the main topic. Respond with just the title, no quotes or punctuation.',
        },
        {
          role: 'user',
          content,
        },
      ],
      max_tokens: 20,
      temperature: 0.3,
    });

    const title = response.choices[0]?.message?.content?.trim() || '';
    return title || 'Conversation Summary';
  } catch (error) {
    console.error('[summarizer] Failed to generate title:', error);
    return 'Conversation Summary';
  }
}
