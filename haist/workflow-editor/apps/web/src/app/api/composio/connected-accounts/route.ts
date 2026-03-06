/**
 * Composio Connected Accounts API Route
 *
 * GET /api/composio/connected-accounts
 * Returns user's connected accounts
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { composioService } from '@/lib/composio/composio-service';

export async function GET(request: NextRequest) {
  try {
    const userId = DEV_USER.id;

    // Check if Composio API key is configured
    if (!process.env.COMPOSIO_API_KEY) {
      return NextResponse.json({
        accounts: [],
        total: 0,
        message: 'COMPOSIO_API_KEY is not configured',
      });
    }

    const connectedAccounts =
      await composioService.getUserConnectedAccounts(userId);

    // Debug logging
    console.log('Connected accounts for user:', userId);
    connectedAccounts.forEach((acc) => {
      console.log(`  - ${acc.appName || acc.appUniqueId}: status=${acc.status}`);
    });

    return NextResponse.json({
      accounts: connectedAccounts.map((account) => ({
        id: account.id,
        appName: account.appName || account.appUniqueId || 'unknown',
        status: account.status,
        connectedAt: account.createdAt,
        lastAccessedAt: account.updatedAt,
      })),
      total: connectedAccounts.length,
    });
  } catch (error) {
    console.error('Get connected accounts error:', error);
    return NextResponse.json(
      { error: 'Failed to get connected accounts' },
      { status: 500 }
    );
  }
}
