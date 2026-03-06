/**
 * Composio Tools API Route
 *
 * GET /api/composio/tools?toolkits=GMAIL,SLACK
 * Returns available tools for the specified toolkits
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { composioService } from '@/lib/composio/composio-service';
import { getAllComposioToolkits, getComposioTool } from '@/lib/composio/composio-toolkits';

export async function GET(request: NextRequest) {
  try {
    const userId = DEV_USER.id;
    const { searchParams } = new URL(request.url);
    const toolkitsParam = searchParams.get('toolkits');

    const toolkits = toolkitsParam
      ? toolkitsParam.split(',').map((t) => t.trim().toUpperCase())
      : undefined;

    // If no Composio API key, return static toolkit data
    if (!process.env.COMPOSIO_API_KEY) {
      const staticToolkits = getAllComposioToolkits();
      const filteredToolkits = toolkits
        ? staticToolkits.filter((t) =>
            toolkits.includes(t.toolkit.toUpperCase())
          )
        : staticToolkits;

      return NextResponse.json({
        tools: filteredToolkits.flatMap((toolkit) =>
          toolkit.tools.map((tool) => ({
            name: tool.name,
            description: tool.description,
            toolkit: toolkit.toolkit,
            inputs: tool.inputs,
          }))
        ),
        source: 'static',
        message: 'Using static toolkit data (no COMPOSIO_API_KEY configured)',
      });
    }

    // Fetch tools from Composio (returns an array)
    const tools = await composioService.getUserTools(userId, toolkits);

    const toolList = tools.map((tool) => {
      // Extract toolkit from tool name (e.g., "GMAIL_SEND_EMAIL" -> "GMAIL")
      const toolkit = tool.name.split('_')[0]?.toUpperCase() || 'OTHER';
      // Get inputs from static data as fallback
      const staticTool = getComposioTool(tool.name);
      return {
        name: tool.name,
        description: tool.description || 'No description available',
        toolkit,
        inputs: staticTool?.inputs,
        // Include structured input schema for AI agent awareness
        inputSchema: tool.inputSchema,
      };
    });

    return NextResponse.json({
      tools: toolList,
      count: toolList.length,
      requestedToolkits: toolkits || ['all'],
      source: 'composio',
    });
  } catch (error) {
    console.error('Get tools error:', error);
    return NextResponse.json(
      { error: 'Failed to get tools' },
      { status: 500 }
    );
  }
}
