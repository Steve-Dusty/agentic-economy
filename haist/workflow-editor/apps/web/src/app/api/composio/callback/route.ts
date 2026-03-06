/**
 * Composio OAuth Callback Route
 *
 * GET /api/composio/callback
 * Handles OAuth callback from Composio and closes the popup window
 */

import { NextRequest, NextResponse } from 'next/server';

/**
 * HTML escapes a string to prevent XSS
 */
function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Escapes a string for safe use in JavaScript
 */
function escapeJs(unsafe: string): string {
  return JSON.stringify(unsafe);
}

/**
 * Returns HTML that closes the popup window and notifies the parent
 */
function createCloseWindowResponse(success: boolean, appName: string, error?: string) {
  // Sanitize inputs
  const safeAppName = escapeHtml(appName);
  const safeError = error ? escapeHtml(error) : '';
  
  const html = `
<!DOCTYPE html>
<html>
<head>
  <title>${success ? 'Connected' : 'Connection Failed'}</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      background: #0a0a0a;
      color: #fafafa;
    }
    .container {
      text-align: center;
      padding: 2rem;
    }
    .icon {
      font-size: 3rem;
      margin-bottom: 1rem;
    }
    h1 {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }
    p {
      color: #a1a1aa;
      margin-bottom: 1rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">${success ? '✓' : '✗'}</div>
    <h1>${success ? `${safeAppName} Connected!` : 'Connection Failed'}</h1>
    <p>${success ? 'This window will close automatically...' : (safeError || 'Please try again.')}</p>
  </div>
  <script>
    // Notify parent window and close
    if (window.opener) {
      window.opener.postMessage({
        type: 'composio-auth-complete',
        success: ${success},
        app: ${escapeJs(appName)},
        error: ${error ? escapeJs(error) : 'null'}
      }, '*');
    }
    // Close the window after a brief delay
    setTimeout(() => window.close(), 1500);
  </script>
</body>
</html>
  `.trim();

  return new NextResponse(html, {
    headers: { 'Content-Type': 'text/html' },
  });
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Composio typically returns these parameters after OAuth
    const status = searchParams.get('status');
    const appName = searchParams.get('app') || searchParams.get('appName') || 'Service';

    if (status === 'success') {
      return createCloseWindowResponse(true, appName);
    } else {
      const error = searchParams.get('error') || 'Authentication failed';
      return createCloseWindowResponse(false, appName, error);
    }
  } catch (error) {
    console.error('OAuth callback error:', error);
    return createCloseWindowResponse(false, 'Service', 'Callback failed');
  }
}
