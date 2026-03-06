/**
 * Composio Auth API Route
 *
 * POST /api/composio/auth/[appName]
 * Initiates OAuth flow for the specified app
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { composioService } from '@/lib/composio/composio-service';
import { getAuthConfigId } from '@/lib/composio/composio-toolkits';

interface RouteParams {
  params: Promise<{ appName: string }>;
}

/**
 * Validates that a redirect URL is safe (same origin or whitelisted)
 */
function isValidRedirectUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    const allowedOrigins = [
      process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
      'https://app.composio.dev', // Composio's official callback URL
    ];
    
    // Check if the origin is in our allowlist
    return allowedOrigins.some(origin => {
      const allowedOrigin = new URL(origin);
      return parsed.origin === allowedOrigin.origin;
    });
  } catch {
    // Invalid URL
    return false;
  }
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;
    const { appName } = await params;
    const body = await request.json();
    const { redirectUrl } = body;

    // Validate redirect URL to prevent open redirects
    if (redirectUrl && !isValidRedirectUrl(redirectUrl)) {
      return NextResponse.json(
        { error: 'Invalid redirect URL' },
        { status: 400 }
      );
    }

    // Get auth config ID for the app
    const authConfigId = getAuthConfigId(appName);

    if (!authConfigId) {
      return NextResponse.json(
        {
          error: `No auth config found for ${appName}. Please configure ${appName.toUpperCase()}_AUTH_CONFIG_ID in environment.`,
        },
        { status: 400 }
      );
    }

    // Check if Composio API key is configured
    if (!process.env.COMPOSIO_API_KEY) {
      return NextResponse.json(
        {
          error: 'COMPOSIO_API_KEY is not configured',
        },
        { status: 500 }
      );
    }

    // Initiate authentication
    const authRequest = await composioService.initiateAuthentication(
      userId,
      appName.toUpperCase(),
      authConfigId,
      redirectUrl || `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/api/composio/callback`
    );

    // Log authentication initiation without sensitive data
    console.log(`[Auth] ${appName.toUpperCase()} auth initiated for user ${userId}`);

    return NextResponse.json({
      appName: appName.toUpperCase(),
      authRequest,
      message: `Authentication initiated for ${appName}`,
    });
  } catch (error) {
    console.error('Initiate authentication error:', error);
    return NextResponse.json(
      { error: 'Failed to initiate authentication' },
      { status: 500 }
    );
  }
}
