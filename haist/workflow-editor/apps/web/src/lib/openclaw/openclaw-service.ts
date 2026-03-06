/**
 * OpenClaw Service
 *
 * Thin HTTP client that talks to the OpenClaw local AI gateway.
 * The gateway runs at a user-specified URL (default http://127.0.0.1:18789)
 * and exposes the user's local machine over HTTP.
 */

interface OpenClawConfig {
  url: string;
  token: string;
}

/** In-memory store (use globalThis to survive Next.js dev-mode HMR) */
const g = globalThis as unknown as { __openclawConfigs?: Map<string, OpenClawConfig> };
if (!g.__openclawConfigs) g.__openclawConfigs = new Map();

interface ChatCompletionMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface ChatCompletionResponse {
  id: string;
  choices: Array<{
    index: number;
    message: {
      role: string;
      content: string;
    };
    finish_reason: string;
  }>;
}

interface ToolInvokeResponse {
  ok: boolean;
  result?: unknown;
  error?: string;
}

class OpenClawService {
  private get configs(): Map<string, OpenClawConfig> {
    return g.__openclawConfigs!;
  }

  /**
   * Save gateway config for a user.
   */
  setConfig(userId: string, config: OpenClawConfig): void {
    this.configs.set(userId, config);
  }

  /**
   * Get the stored config for a user.
   */
  getConfig(userId: string): OpenClawConfig | null {
    return this.configs.get(userId) || null;
  }

  /**
   * Remove config for a user.
   */
  removeConfig(userId: string): void {
    this.configs.delete(userId);
  }

  /**
   * Check if a user has a config stored.
   */
  isConfigured(userId: string): boolean {
    return this.configs.has(userId);
  }

  /**
   * Send a natural language instruction to OpenClaw via the chat completions endpoint.
   * This lets the OpenClaw agent use exec, read, write, browser, etc. internally.
   */
  async chatCompletion(userId: string, instruction: string): Promise<string> {
    const config = this.configs.get(userId);
    if (!config) {
      throw new Error('OpenClaw not configured. Please connect OpenClaw in the integrations panel.');
    }

    const messages: ChatCompletionMessage[] = [
      {
        role: 'system',
        content: 'You are a local machine assistant. Execute the user\'s instruction using your available tools (exec, read, write, browser, etc.) and return the result concisely. If you run a command, include its output. If you read a file, include its contents. Be direct and factual.',
      },
      {
        role: 'user',
        content: instruction,
      },
    ];

    const response = await fetch(`${config.url}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.token}`,
      },
      body: JSON.stringify({
        model: 'default',
        messages,
      }),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(`OpenClaw request failed (${response.status}): ${text || response.statusText}`);
    }

    const data: ChatCompletionResponse = await response.json();
    const content = data.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error('OpenClaw returned an empty response');
    }

    return content;
  }

  /**
   * Invoke a specific tool on the OpenClaw gateway.
   */
  async invokeTool(userId: string, tool: string, args: Record<string, unknown> = {}): Promise<unknown> {
    const config = this.configs.get(userId);
    if (!config) {
      throw new Error('OpenClaw not configured. Please connect OpenClaw in the integrations panel.');
    }

    const response = await fetch(`${config.url}/tools/invoke`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.token}`,
      },
      body: JSON.stringify({ tool, args }),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(`OpenClaw tool invoke failed (${response.status}): ${text || response.statusText}`);
    }

    const data: ToolInvokeResponse = await response.json();
    if (!data.ok) {
      throw new Error(data.error || 'OpenClaw tool invocation failed');
    }

    return data.result;
  }

  /**
   * Test the connection to the OpenClaw gateway.
   * Uses the sessions_list tool as a lightweight health check.
   */
  async testConnection(url: string, token: string): Promise<boolean> {
    try {
      const response = await fetch(`${url}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          model: 'default',
          messages: [
            { role: 'user', content: 'Reply with exactly: OPENCLAW_OK' },
          ],
        }),
      });

      return response.ok;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const openClawService = new OpenClawService();
