/**
 * Workflow AI Service
 *
 * Core service for interacting with LLM to generate workflows.
 * Supports both OpenAI and Anthropic providers.
 */

import Anthropic from '@anthropic-ai/sdk';
import OpenAI from 'openai';
import type { AIAssistantContext, ChatMessage, AIResponse } from './types';
import { buildContextForAI } from './bubble-context-builder';
import { getSystemPromptWithContext } from './prompts';

export type AIProvider = 'openai' | 'anthropic';

/**
 * WorkflowAIService class
 *
 * Handles LLM interactions for workflow generation.
 */
export class WorkflowAIService {
  private anthropic: Anthropic | null = null;
  private openai: OpenAI | null = null;
  private provider: AIProvider = 'openai'; // Default to OpenAI

  /**
   * Set the AI provider to use
   */
  setProvider(provider: AIProvider) {
    this.provider = provider;
  }

  /**
   * Get the current provider
   */
  getProvider(): AIProvider {
    return this.provider;
  }

  /**
   * Lazily initialize the Anthropic client
   */
  private getAnthropicClient(): Anthropic | null {
    if (this.anthropic) {
      return this.anthropic;
    }

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      console.warn('ANTHROPIC_API_KEY not configured');
      return null;
    }

    try {
      this.anthropic = new Anthropic({ apiKey });
      return this.anthropic;
    } catch (error) {
      console.error('Failed to initialize Anthropic client:', error);
      return null;
    }
  }

  /**
   * Lazily initialize the OpenAI client
   */
  private getOpenAIClient(): OpenAI | null {
    if (this.openai) {
      return this.openai;
    }

    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      console.warn('OPENAI_API_KEY not configured');
      return null;
    }

    try {
      this.openai = new OpenAI({ apiKey });
      return this.openai;
    } catch (error) {
      console.error('Failed to initialize OpenAI client:', error);
      return null;
    }
  }

  /**
   * Generate AI response for a chat message
   */
  async chat(
    userMessage: string,
    conversationHistory: ChatMessage[],
    context: AIAssistantContext,
    artifactsContext?: string,
    provider?: AIProvider
  ): Promise<AIResponse> {
    const selectedProvider = provider || this.provider;

    if (selectedProvider === 'openai') {
      return this.chatWithOpenAI(userMessage, conversationHistory, context, artifactsContext);
    } else {
      return this.chatWithAnthropic(userMessage, conversationHistory, context, artifactsContext);
    }
  }

  /**
   * Chat using OpenAI GPT-5.2
   */
  private async chatWithOpenAI(
    userMessage: string,
    conversationHistory: ChatMessage[],
    context: AIAssistantContext,
    artifactsContext?: string
  ): Promise<AIResponse> {
    const client = this.getOpenAIClient();
    if (!client) {
      return {
        message: 'AI service is not configured. Please set up the OPENAI_API_KEY environment variable.',
      };
    }

    try {
      // Build the system prompt with context
      const contextString = buildContextForAI(context);
      let systemPrompt = getSystemPromptWithContext(contextString);

      // Append artifacts context if available
      if (artifactsContext) {
        systemPrompt += `\n\n# User's Relevant Context (from Artifacts)\n\nThe following contextual information has been automatically retrieved based on the user's message. Use this to provide more personalized and informed responses:\n\n${artifactsContext}`;
      }

      // Convert conversation history to OpenAI format
      const messages: OpenAI.ChatCompletionMessageParam[] = [
        { role: 'system', content: systemPrompt },
        ...conversationHistory
          .filter((msg) => msg.role !== 'system')
          .map((msg) => ({
            role: msg.role as 'user' | 'assistant',
            content: msg.content,
          })),
        { role: 'user', content: userMessage },
      ];

      // Call the OpenAI API
      const response = await client.chat.completions.create({
        model: 'gpt-5.2',
        messages,
      });

      // Extract the response text
      const responseText = response.choices[0]?.message?.content || '';

      return this.processResponse(responseText, context);
    } catch (error) {
      console.error('Error calling OpenAI API:', error);
      return {
        message: 'Sorry, I encountered an error while processing your request. Please try again.',
      };
    }
  }

  /**
   * Chat using Anthropic Claude
   */
  private async chatWithAnthropic(
    userMessage: string,
    conversationHistory: ChatMessage[],
    context: AIAssistantContext,
    artifactsContext?: string
  ): Promise<AIResponse> {
    const client = this.getAnthropicClient();
    if (!client) {
      return {
        message: 'AI service is not configured. Please set up the ANTHROPIC_API_KEY environment variable.',
      };
    }

    try {
      // Build the system prompt with context
      const contextString = buildContextForAI(context);
      let systemPrompt = getSystemPromptWithContext(contextString);

      // Append artifacts context if available
      if (artifactsContext) {
        systemPrompt += `\n\n# User's Relevant Context (from Artifacts)\n\nThe following contextual information has been automatically retrieved based on the user's message. Use this to provide more personalized and informed responses:\n\n${artifactsContext}`;
      }

      // Convert conversation history to Anthropic format
      const messages: Anthropic.MessageParam[] = conversationHistory
        .filter((msg) => msg.role !== 'system')
        .map((msg) => ({
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
        }));

      // Add the current user message
      messages.push({
        role: 'user',
        content: userMessage,
      });

      // Call the Anthropic API
      const response = await client.messages.create({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 4096,
        system: systemPrompt,
        messages,
      });

      // Extract the response text
      const responseText =
        response.content[0].type === 'text' ? response.content[0].text : '';

      return this.processResponse(responseText, context);
    } catch (error) {
      console.error('Error calling Anthropic API:', error);
      return {
        message: 'Sorry, I encountered an error while processing your request. Please try again.',
      };
    }
  }

  /**
   * Process the AI response
   */
  private processResponse(responseText: string, _context: AIAssistantContext): AIResponse {
    return {
      message: responseText,
    };
  }

  /**
   * Generate workflow suggestions based on user's connected services
   */
  async getSuggestions(context: AIAssistantContext): Promise<string[]> {
    const connectedServices = context.composio.connectedAccounts
      .filter((acc) => acc.status === 'ACTIVE')
      .map((acc) => acc.toolkit);

    const suggestions: string[] = [];

    // Add suggestions based on connected services
    if (connectedServices.includes('GMAIL')) {
      suggestions.push('Monitor Gmail for important emails and send summaries to Slack');
    }
    if (connectedServices.includes('SLACK')) {
      suggestions.push('Create a Slack notification workflow for web scraping results');
    }
    if (connectedServices.includes('GOOGLECALENDAR')) {
      suggestions.push('Send daily calendar event summaries');
    }

    // Always suggest AI-related workflows
    suggestions.push('Create an AI agent that summarizes Reddit posts');
    suggestions.push('Build a web search workflow with AI analysis');

    return suggestions.slice(0, 5);
  }
}

// Singleton instance
export const workflowAIService = new WorkflowAIService();
