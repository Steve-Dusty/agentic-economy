import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { findRelevantArtifacts } from '@/lib/artifacts';

/**
 * POST /api/artifacts/search - Search artifacts semantically
 */
export async function POST(request: NextRequest) {
  try {
    const userId = DEV_USER.id;

    const body = await request.json();
    const { query, limit = 5, includeIds = [], excludeIds = [] } = body;

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    const artifacts = await findRelevantArtifacts({
      userId,
      query: query.trim(),
      limit,
      includeIds,
      excludeIds,
    });

    return NextResponse.json({ artifacts });
  } catch (error) {
    console.error('Error searching artifacts:', error);
    return NextResponse.json(
      { error: 'Failed to search artifacts' },
      { status: 500 }
    );
  }
}
