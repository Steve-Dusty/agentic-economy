import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { openClawService } from '@/lib/openclaw/openclaw-service';
import { toolRouterService } from '@/lib/ai-assistant/tool-router-service';

/**
 * GET /api/openclaw/config - Check OpenClaw connection status
 */
export async function GET() {
  try {
    const userId = DEV_USER.id;
    const config = openClawService.getConfig(userId);

    if (!config) {
      return NextResponse.json({
        connected: false,
        configured: false,
      });
    }

    // Test the actual connection
    const isAlive = await openClawService.testConnection(config.url, config.token);

    return NextResponse.json({
      connected: isAlive,
      configured: true,
      url: config.url,
    });
  } catch (error) {
    console.error('Error checking OpenClaw status:', error);
    return NextResponse.json(
      { error: 'Failed to check OpenClaw status' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/openclaw/config - Save OpenClaw config and test connection
 */
export async function POST(request: NextRequest) {
  try {
    const userId = DEV_USER.id;
    const body = await request.json();
    const { url, token } = body;

    if (!url || typeof url !== 'string') {
      return NextResponse.json(
        { error: 'Gateway URL is required' },
        { status: 400 }
      );
    }

    if (!token || typeof token !== 'string') {
      return NextResponse.json(
        { error: 'Auth token is required' },
        { status: 400 }
      );
    }

    // Normalize URL (remove trailing slash)
    const normalizedUrl = url.replace(/\/+$/, '');

    // Test connection before saving
    const isAlive = await openClawService.testConnection(normalizedUrl, token);

    if (!isAlive) {
      return NextResponse.json(
        {
          error: 'Could not connect to OpenClaw gateway. Make sure the gateway is running and the URL/token are correct.',
          connected: false,
        },
        { status: 400 }
      );
    }

    // Save the config
    openClawService.setConfig(userId, { url: normalizedUrl, token });

    // Clear the tool router session so the system prompt rebuilds with OpenClaw status
    toolRouterService.clearSession(userId);

    return NextResponse.json({
      success: true,
      connected: true,
      url: normalizedUrl,
    });
  } catch (error) {
    console.error('Error saving OpenClaw config:', error);
    return NextResponse.json(
      { error: 'Failed to save OpenClaw config' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/openclaw/config - Disconnect OpenClaw
 */
export async function DELETE() {
  try {
    const userId = DEV_USER.id;
    openClawService.removeConfig(userId);

    // Clear the tool router session so the system prompt rebuilds
    toolRouterService.clearSession(userId);

    return NextResponse.json({ success: true, connected: false });
  } catch (error) {
    console.error('Error removing OpenClaw config:', error);
    return NextResponse.json(
      { error: 'Failed to disconnect OpenClaw' },
      { status: 500 }
    );
  }
}
