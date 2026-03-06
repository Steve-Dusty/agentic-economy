/**
 * User Profile Tools for the AI Assistant
 *
 * Manages a persistent "User Profile" artifact that accumulates
 * context about the user over time (preferences, courses, projects, etc.)
 * The AI reads this on every conversation and updates it as it learns more.
 */

import { tool } from '@openai/agents';
import { artifactService } from '@/lib/artifacts';
import type { ArtifactWithEntries } from '@/lib/artifacts/types';

const PROFILE_TITLE = '__user_profile__';

/**
 * Get or create the user profile artifact
 */
async function getOrCreateProfile(userId: string): Promise<ArtifactWithEntries> {
  // Search for existing profile artifact
  const artifacts = await artifactService.getByUserId(userId);
  const existing = artifacts.find((a) => a.title === PROFILE_TITLE);

  if (existing) {
    const withEntries = await artifactService.getWithEntries(existing.id);
    if (withEntries) return withEntries;
  }

  // Create new profile
  const artifact = await artifactService.create({
    userId,
    title: PROFILE_TITLE,
    summary: 'Persistent user profile and preferences',
    tags: ['system', 'profile'],
    firstEntry: {
      content: 'Profile created. No information yet.',
      source: 'manual',
    },
  });

  const withEntries = await artifactService.getWithEntries(artifact.id);
  return withEntries!;
}

/**
 * Format the user profile as context for the AI
 */
export async function getUserProfileContext(userId: string): Promise<string> {
  try {
    const profile = await getOrCreateProfile(userId);
    const entries = profile.entries
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 10); // Latest 10 entries

    if (entries.length <= 1 && entries[0]?.content === 'Profile created. No information yet.') {
      return '';
    }

    const content = entries.map((e) => e.content).join('\n\n');
    return `USER PROFILE (things you know about this user):\n${content}`;
  } catch (error) {
    console.error('Error loading user profile:', error);
    return '';
  }
}

/**
 * Create tools for managing the user profile
 */
export function createUserProfileTools(userId: string) {
  const updateProfile = tool({
    name: 'update_user_profile',
    description: `Update the user's persistent profile with new information you've learned about them. Use this when you discover:
- Their name, role, school, or workplace
- Courses they're taking, projects they're working on
- Preferences (communication style, tools they use, schedule)
- Important contacts, deadlines, or recurring tasks
- Any context that would be useful to remember across conversations

This information persists across all future conversations. Only store factual, useful information — not conversation details.`,
    parameters: {
      type: 'object' as const,
      properties: {
        info: {
          type: 'string',
          description: 'The information to add to the user profile. Be concise and factual. E.g., "Takes CS 3240 (Human-Computer Interaction) at BGSU, Spring 2026. Professor focuses on user research methods."',
        },
      },
      required: ['info'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as { info: string };
        const profile = await getOrCreateProfile(userId);

        await artifactService.addEntry(profile.id, {
          content: input.info.trim(),
          source: 'manual',
        });

        return JSON.stringify({
          success: true,
          message: 'Profile updated.',
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update profile',
        });
      }
    },
  });

  return [updateProfile];
}
