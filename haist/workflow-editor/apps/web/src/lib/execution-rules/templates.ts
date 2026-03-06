/**
 * Automation Rule Templates
 * 
 * Pre-built templates for common automation patterns.
 * Users can pick one and customize it.
 */

import type { ExecutionRuleInput, ActivationMode, ScheduleInterval, ExecutionStep } from './types';

export interface RuleTemplate {
  id: string;
  name: string;
  description: string;
  category: TemplateCategory;
  icon: string; // emoji
  template: ExecutionRuleInput;
}

export type TemplateCategory = 'email' | 'social' | 'productivity' | 'monitoring' | 'data';

export const TEMPLATE_CATEGORIES: Record<TemplateCategory, { label: string; icon: string }> = {
  email: { label: 'Email', icon: '📧' },
  social: { label: 'Social Media', icon: '📱' },
  productivity: { label: 'Productivity', icon: '⚡' },
  monitoring: { label: 'Monitoring', icon: '👀' },
  data: { label: 'Data & Reports', icon: '📊' },
};

export const RULE_TEMPLATES: RuleTemplate[] = [
  // --- Email ---
  {
    id: 'daily-email-digest',
    name: 'Daily Email Digest',
    description: 'Summarize all unread emails every morning and send a digest.',
    category: 'email',
    icon: '📬',
    template: {
      name: 'Daily Email Digest',
      description: 'Summarizes unread emails every morning',
      activationMode: 'scheduled',
      scheduleEnabled: true,
      scheduleInterval: 'daily',
      topicCondition: 'Daily email summary',
      executionSteps: [
        { type: 'instruction', content: 'Fetch all unread emails from Gmail' },
        { type: 'instruction', content: 'Summarize each email in 1-2 sentences, grouped by sender' },
        { type: 'instruction', content: 'Flag any emails that look urgent or time-sensitive' },
      ],
      outputConfig: { platform: 'none', format: 'summary' },
    },
  },
  {
    id: 'auto-reply-clients',
    name: 'Auto-Reply to Clients',
    description: 'When a client emails, acknowledge receipt and notify your team.',
    category: 'email',
    icon: '✉️',
    template: {
      name: 'Auto-Reply to Clients',
      description: 'Acknowledges client emails and notifies the team',
      activationMode: 'trigger',
      scheduleEnabled: false,
      acceptedTriggers: ['GMAIL_NEW_GMAIL_MESSAGE'],
      topicCondition: 'New email from a client or customer',
      executionSteps: [
        { type: 'instruction', content: 'Check if the sender is a client (not internal, not spam/newsletter)' },
        { type: 'instruction', content: 'Reply to the email thread acknowledging receipt: "Thanks for your email, we\'ll get back to you shortly."' },
        { type: 'instruction', content: 'Send a Slack message to #team with a summary of the client email' },
      ],
      outputConfig: { platform: 'slack', destination: '#team', format: 'summary' },
    },
  },
  {
    id: 'email-label-organizer',
    name: 'Email Auto-Organizer',
    description: 'Automatically categorize and label incoming emails.',
    category: 'email',
    icon: '🏷️',
    template: {
      name: 'Email Auto-Organizer',
      description: 'Labels and categorizes incoming emails automatically',
      activationMode: 'trigger',
      scheduleEnabled: false,
      acceptedTriggers: ['GMAIL_NEW_GMAIL_MESSAGE'],
      topicCondition: 'Any new email received',
      executionSteps: [
        { type: 'instruction', content: 'Analyze the email content and determine category: work, personal, newsletter, billing, or spam' },
        { type: 'instruction', content: 'Apply the appropriate Gmail label based on category' },
        { type: 'instruction', content: 'If the email is urgent or from a VIP sender, star it' },
      ],
      outputConfig: { platform: 'none', format: 'summary' },
    },
  },

  // --- Social Media ---
  {
    id: 'social-mention-monitor',
    name: 'Social Mention Monitor',
    description: 'Track mentions of your brand or keywords across social media.',
    category: 'social',
    icon: '🔔',
    template: {
      name: 'Social Mention Monitor',
      description: 'Monitors social media for brand mentions',
      activationMode: 'scheduled',
      scheduleEnabled: true,
      scheduleInterval: 'hourly',
      topicCondition: 'Social media mention monitoring',
      executionSteps: [
        { type: 'instruction', content: 'Search Twitter/X for mentions of [YOUR BRAND] or [YOUR KEYWORDS]' },
        { type: 'instruction', content: 'Filter out spam and irrelevant results' },
        { type: 'instruction', content: 'Summarize new mentions with sentiment (positive/negative/neutral) and send to Slack' },
      ],
      outputConfig: { platform: 'slack', destination: '#social', format: 'summary' },
    },
  },
  {
    id: 'content-repurposer',
    name: 'Content Repurposer',
    description: 'Turn a blog post or article into social media posts.',
    category: 'social',
    icon: '♻️',
    template: {
      name: 'Content Repurposer',
      description: 'Converts long-form content into social media posts',
      activationMode: 'manual',
      scheduleEnabled: false,
      topicCondition: 'Content repurposing request',
      executionSteps: [
        { type: 'instruction', content: 'Read the provided article/blog post content' },
        { type: 'instruction', content: 'Create 3 Twitter/X posts (under 280 chars each) highlighting key points' },
        { type: 'instruction', content: 'Create 1 LinkedIn post (professional tone, 150-300 words)' },
        { type: 'instruction', content: 'Suggest 5 relevant hashtags for each platform' },
      ],
      outputConfig: { platform: 'none', format: 'detailed' },
    },
  },

  // --- Productivity ---
  {
    id: 'morning-briefing',
    name: 'Morning Briefing',
    description: 'Daily summary of calendar, emails, and tasks to start your day.',
    category: 'productivity',
    icon: '☀️',
    template: {
      name: 'Morning Briefing',
      description: 'Daily morning summary of calendar, emails, and priorities',
      activationMode: 'scheduled',
      scheduleEnabled: true,
      scheduleInterval: 'daily',
      topicCondition: 'Morning briefing',
      executionSteps: [
        { type: 'instruction', content: 'Fetch today\'s calendar events and list them with times' },
        { type: 'instruction', content: 'Summarize unread emails (top 5 most important)' },
        { type: 'instruction', content: 'Check for any upcoming deadlines this week' },
        { type: 'instruction', content: 'Compile everything into a brief morning report' },
      ],
      outputConfig: { platform: 'none', format: 'summary' },
    },
  },
  {
    id: 'meeting-prep',
    name: 'Meeting Prep Assistant',
    description: 'Before each meeting, gather context and prepare notes.',
    category: 'productivity',
    icon: '📋',
    template: {
      name: 'Meeting Prep Assistant',
      description: 'Prepares context and notes before scheduled meetings',
      activationMode: 'scheduled',
      scheduleEnabled: true,
      scheduleInterval: 'hourly',
      topicCondition: 'Upcoming meeting preparation',
      executionSteps: [
        { type: 'instruction', content: 'Check calendar for meetings in the next 2 hours' },
        { type: 'instruction', content: 'For each upcoming meeting, find related emails and previous notes' },
        { type: 'instruction', content: 'Summarize key context: who\'s attending, what was discussed last time, any open action items' },
        { type: 'instruction', content: 'Create a brief prep doc with talking points' },
      ],
      outputConfig: { platform: 'none', format: 'detailed' },
    },
  },
  {
    id: 'weekly-review',
    name: 'Weekly Review',
    description: 'End-of-week summary of what happened and what\'s coming up.',
    category: 'productivity',
    icon: '📅',
    template: {
      name: 'Weekly Review',
      description: 'Compiles a weekly summary every Friday',
      activationMode: 'scheduled',
      scheduleEnabled: true,
      scheduleInterval: 'weekly',
      topicCondition: 'Weekly review summary',
      executionSteps: [
        { type: 'instruction', content: 'Summarize all automation executions from this week (successes, failures, patterns)' },
        { type: 'instruction', content: 'List key emails sent and received' },
        { type: 'instruction', content: 'Review calendar for next week\'s important events' },
        { type: 'instruction', content: 'Suggest priorities for next week based on patterns' },
      ],
      outputConfig: { platform: 'none', format: 'detailed' },
    },
  },

  // --- Monitoring ---
  {
    id: 'github-issue-notifier',
    name: 'GitHub Issue Notifier',
    description: 'Get notified when new issues are created in your repos.',
    category: 'monitoring',
    icon: '🐛',
    template: {
      name: 'GitHub Issue Notifier',
      description: 'Monitors GitHub repos for new issues and notifies on Slack',
      activationMode: 'trigger',
      scheduleEnabled: false,
      acceptedTriggers: ['GITHUB_ISSUE_ADDED_EVENT'],
      topicCondition: 'New GitHub issue created',
      executionSteps: [
        { type: 'instruction', content: 'Extract the issue title, description, labels, and author' },
        { type: 'instruction', content: 'Classify priority based on labels and content (critical/high/medium/low)' },
        { type: 'instruction', content: 'Send a formatted notification to Slack with issue details and priority' },
      ],
      outputConfig: { platform: 'slack', destination: '#dev', format: 'summary' },
    },
  },
  {
    id: 'competitor-tracker',
    name: 'Competitor Tracker',
    description: 'Monitor competitor activity and get weekly summaries.',
    category: 'monitoring',
    icon: '🕵️',
    template: {
      name: 'Competitor Tracker',
      description: 'Tracks competitor news and product updates',
      activationMode: 'scheduled',
      scheduleEnabled: true,
      scheduleInterval: 'daily',
      topicCondition: 'Competitor monitoring',
      executionSteps: [
        { type: 'instruction', content: 'Search for recent news about [COMPETITOR 1], [COMPETITOR 2], [COMPETITOR 3]' },
        { type: 'instruction', content: 'Check their social media for product announcements or updates' },
        { type: 'instruction', content: 'Summarize any notable changes, launches, or moves' },
        { type: 'instruction', content: 'If anything significant, flag it as high priority' },
      ],
      outputConfig: { platform: 'none', format: 'detailed' },
    },
  },

  // --- Data & Reports ---
  {
    id: 'lead-enrichment',
    name: 'Lead Enrichment',
    description: 'Enrich new leads with company info and add to your CRM.',
    category: 'data',
    icon: '🎯',
    template: {
      name: 'Lead Enrichment',
      description: 'Enriches new leads with company data and adds to CRM',
      activationMode: 'manual',
      scheduleEnabled: false,
      topicCondition: 'New lead to enrich',
      executionSteps: [
        { type: 'instruction', content: 'Look up the company from the lead\'s email domain' },
        { type: 'instruction', content: 'Find company size, industry, location, and recent news' },
        { type: 'instruction', content: 'Score the lead based on company fit (1-10)' },
        { type: 'instruction', content: 'Create a summary card with all enriched data' },
      ],
      outputConfig: { platform: 'none', format: 'detailed' },
    },
  },
  {
    id: 'data-collector',
    name: 'Scheduled Data Collector',
    description: 'Collect data from APIs or websites on a schedule.',
    category: 'data',
    icon: '📥',
    template: {
      name: 'Scheduled Data Collector',
      description: 'Periodically collects and stores data from configured sources',
      activationMode: 'scheduled',
      scheduleEnabled: true,
      scheduleInterval: 'daily',
      topicCondition: 'Scheduled data collection',
      executionSteps: [
        { type: 'instruction', content: 'Fetch data from [YOUR DATA SOURCE / API / WEBSITE]' },
        { type: 'instruction', content: 'Parse and extract the relevant fields' },
        { type: 'instruction', content: 'Compare with previous data to identify changes or trends' },
        { type: 'instruction', content: 'Save results to a Google Sheet or Notion database' },
      ],
      outputConfig: { platform: 'none', format: 'raw' },
    },
  },
];

/**
 * Get templates by category
 */
export function getTemplatesByCategory(): Record<TemplateCategory, RuleTemplate[]> {
  const result: Record<TemplateCategory, RuleTemplate[]> = {
    email: [],
    social: [],
    productivity: [],
    monitoring: [],
    data: [],
  };

  for (const template of RULE_TEMPLATES) {
    result[template.category].push(template);
  }

  return result;
}
