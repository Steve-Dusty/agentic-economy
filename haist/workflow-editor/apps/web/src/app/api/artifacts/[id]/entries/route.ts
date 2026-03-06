import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { artifactService, updateArtifactEmbedding } from '@/lib/artifacts';

interface RouteParams {
  params: Promise<{ id: string }>;
}

/**
 * GET /api/artifacts/[id]/entries - Get entries for an artifact
 */
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    const { id } = await params;
    const artifact = await artifactService.get(id);

    if (!artifact) {
      return NextResponse.json(
        { error: 'Artifact not found' },
        { status: 404 }
      );
    }

    // Check ownership
    if (artifact.userId !== userId) {
      return NextResponse.json(
        { error: 'Forbidden' },
        { status: 403 }
      );
    }

    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit');

    const entries = await artifactService.getEntries(
      id,
      limit ? parseInt(limit, 10) : undefined
    );

    return NextResponse.json({ entries });
  } catch (error) {
    console.error('Error fetching entries:', error);
    return NextResponse.json(
      { error: 'Failed to fetch entries' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/artifacts/[id]/entries - Add an entry to an artifact
 */
export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    const { id } = await params;
    const artifact = await artifactService.get(id);

    if (!artifact) {
      return NextResponse.json(
        { error: 'Artifact not found' },
        { status: 404 }
      );
    }

    // Check ownership
    if (artifact.userId !== userId) {
      return NextResponse.json(
        { error: 'Forbidden' },
        { status: 403 }
      );
    }

    const body = await request.json();
    const { content, workflowId, workflowName, source = 'manual' } = body;

    if (!content || typeof content !== 'string') {
      return NextResponse.json(
        { error: 'Content is required' },
        { status: 400 }
      );
    }

    const entry = await artifactService.addEntry(id, {
      content: content.trim(),
      workflowId,
      workflowName,
      source,
    });

    // Update artifact embedding in the background
    updateArtifactEmbedding(id).catch((err) =>
      console.error('Failed to update artifact embedding:', err)
    );

    return NextResponse.json({ entry, success: true });
  } catch (error) {
    console.error('Error adding entry:', error);
    return NextResponse.json(
      { error: 'Failed to add entry' },
      { status: 500 }
    );
  }
}
