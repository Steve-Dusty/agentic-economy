/**
 * Rule Matcher Agent
 *
 * Uses OpenAI GPT to evaluate trigger content against topic conditions
 * and determine which rule should handle the trigger.
 */

import OpenAI from 'openai';
import type { ExecutionRule, TriggerPayload, RuleMatchResult } from './types';
import { RULE_MATCHER_SYSTEM_PROMPT, buildRuleMatcherPrompt } from './prompts';

interface MatcherResponse {
  matchedRuleId: string | null;
  confidence: number;
  reasoning: string;
}

/**
 * Rule Matcher Agent class
 */
class RuleMatcherAgent {
  private openai: OpenAI | null = null;

  /**
   * Lazily initialize the OpenAI client
   */
  private getClient(): OpenAI | null {
    if (this.openai) return this.openai;

    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      console.warn('[RuleMatcherAgent] OPENAI_API_KEY not configured');
      return null;
    }

    try {
      this.openai = new OpenAI({ apiKey });
      return this.openai;
    } catch (error) {
      console.error('[RuleMatcherAgent] Failed to initialize OpenAI client:', error);
      return null;
    }
  }

  /**
   * Match a trigger payload against a list of rules
   * Returns the highest priority rule that matches, or null if no match
   */
  async match(
    payload: TriggerPayload,
    rules: ExecutionRule[]
  ): Promise<RuleMatchResult> {
    if (rules.length === 0) {
      return { matched: false, reasoning: 'No rules to match against' };
    }

    const client = this.getClient();
    if (!client) {
      console.error('[RuleMatcherAgent] No OpenAI client available');
      return { matched: false, reasoning: 'AI service not configured' };
    }

    // Build the prompt with trigger and rules context
    const userPrompt = buildRuleMatcherPrompt(
      payload.triggerSlug,
      payload.toolkitSlug,
      payload.payload || payload.originalPayload || {},
      rules.map((r) => ({
        id: r.id,
        name: r.name,
        topicCondition: r.topicCondition,
      }))
    );

    try {
      const response = await client.chat.completions.create({
        model: 'gpt-5-nano-2025-08-07',
        messages: [
          { role: 'system', content: RULE_MATCHER_SYSTEM_PROMPT },
          { role: 'user', content: userPrompt },
        ],
      });

      // Extract text content from response
      const textContent = response.choices[0]?.message?.content;
      if (!textContent) {
        console.error('[RuleMatcherAgent] No content in response');
        return { matched: false, reasoning: 'Invalid AI response' };
      }

      // Parse JSON response
      const matcherResponse = this.parseResponse(textContent);

      if (!matcherResponse) {
        console.error('[RuleMatcherAgent] Failed to parse response:', textContent);
        return { matched: false, reasoning: 'Failed to parse AI response' };
      }

      // Find the matched rule
      if (matcherResponse.matchedRuleId) {
        const matchedRule = rules.find((r) => r.id === matcherResponse.matchedRuleId);
        if (matchedRule) {
          return {
            matched: true,
            rule: matchedRule,
            confidence: matcherResponse.confidence,
            reasoning: matcherResponse.reasoning,
          };
        }
      }

      return {
        matched: false,
        confidence: matcherResponse.confidence,
        reasoning: matcherResponse.reasoning,
      };
    } catch (error) {
      console.error('[RuleMatcherAgent] Error matching rules:', error);
      return {
        matched: false,
        reasoning: `Error during matching: ${error instanceof Error ? error.message : 'Unknown error'}`,
      };
    }
  }

  /**
   * Parse the JSON response from GPT
   */
  private parseResponse(text: string): MatcherResponse | null {
    try {
      // Try direct JSON parse
      return JSON.parse(text) as MatcherResponse;
    } catch {
      // Try to extract JSON from markdown code block
      const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
      if (jsonMatch) {
        try {
          return JSON.parse(jsonMatch[1].trim()) as MatcherResponse;
        } catch {
          // Continue to other strategies
        }
      }

      // Try to find JSON object in text
      const objectMatch = text.match(/\{[\s\S]*?"matchedRuleId"[\s\S]*?\}/);
      if (objectMatch) {
        try {
          return JSON.parse(objectMatch[0]) as MatcherResponse;
        } catch {
          // Continue
        }
      }

      return null;
    }
  }
}

// Export singleton instance
export const ruleMatcherAgent = new RuleMatcherAgent();
