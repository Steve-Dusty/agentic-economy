import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { artifactService } from '@/lib/artifacts';

/**
 * GET /api/artifacts - List all artifacts for the authenticated user
 */
export async function GET() {
  try {
    const userId = DEV_USER.id;

    const allArtifacts = await artifactService.getByUserId(userId);

    // Hide system artifacts (e.g., __user_profile__)
    const artifacts = allArtifacts.filter((a) => !a.title.startsWith('__'));

    // Enrich with entry count and latest entry snippet
    const enrichedArtifacts = await Promise.all(
      artifacts.map(async (artifact) => {
        try {
          const full = await artifactService.getWithEntries(artifact.id);
          const entries = full?.entries || [];
          return {
            ...artifact,
            entryCount: entries.length,
            latestEntrySnippet: entries.length > 0
              ? entries[0].content.slice(0, 120) + (entries[0].content.length > 120 ? '…' : '')
              : null,
          };
        } catch {
          return { ...artifact, entryCount: 0, latestEntrySnippet: null };
        }
      })
    );

    return NextResponse.json({ artifacts: enrichedArtifacts });
  } catch (error) {
    console.error('Error listing artifacts:', error);
    return NextResponse.json(
      { error: 'Failed to list artifacts' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/artifacts - Create a new artifact
 */
export async function POST(request: NextRequest) {
  try {
    const userId = DEV_USER.id;

    const body = await request.json();
    const { title, summary, tags, content } = body;

    if (!title || typeof title !== 'string') {
      return NextResponse.json(
        { error: 'Title is required' },
        { status: 400 }
      );
    }

    const artifact = await artifactService.create({
      userId,
      title: title.trim(),
      summary: summary?.trim(),
      tags: tags || [],
      firstEntry: content ? {
        content: content.trim(),
        source: 'manual',
      } : undefined,
    });

    return NextResponse.json({ artifact, success: true });
  } catch (error) {
    console.error('Error creating artifact:', error);
    return NextResponse.json(
      { error: 'Failed to create artifact' },
      { status: 500 }
    );
  }
}
