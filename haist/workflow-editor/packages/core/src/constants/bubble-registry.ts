/**
 * Bubble registry - definitions of all available bubbles
 */

import type { BubbleType } from '../types/node.types';
import type { ParameterDefinition, SchemaDefinition } from '../types/parameter.types';

/**
 * Bubble definition for the registry
 */
export interface BubbleDefinition {
  /** Bubble name (kebab-case identifier) */
  name: string;
  /** Class name for code generation */
  className: string;
  /** Bubble type category */
  type: BubbleType;
  /** Short description */
  shortDescription: string;
  /** Detailed description */
  longDescription: string;
  /** Icon name */
  icon: string;
  /** Theme color (hex) */
  color: string;
  /** Input parameter schema */
  schema: Record<string, ParameterDefinition>;
  /** Output result schema */
  resultSchema: SchemaDefinition;
  /** Authentication type */
  authType?: 'oauth' | 'apikey' | 'none' | 'connection-string';
  /** Required credential type */
  credentialType?: string;
}

/**
 * All available bubbles
 */
export const BUBBLE_REGISTRY: Record<string, BubbleDefinition> = {
  // ============================================
  // SERVICE BUBBLES
  // ============================================

  'ai-agent': {
    name: 'ai-agent',
    className: 'AIAgentBubble',
    type: 'service',
    shortDescription: 'AI agent with LLM capabilities',
    longDescription: 'AI agent powered by LangGraph for tool-enabled conversations with various LLM providers',
    icon: 'brain',
    color: '#8B5CF6',
    schema: {
      message: {
        name: 'message',
        type: 'string',
        required: true,
        description: 'The message to send to the AI agent',
      },
      model: {
        name: 'model',
        type: 'object',
        required: true,
        description: 'Model configuration',
        objectSchema: {
          model: {
            name: 'model',
            type: 'enum',
            required: true,
            enumValues: [
              // OpenAI models
              'openai/gpt-5.2',
              'openai/gpt-5-mini',
              'openai/gpt-5-nano',
              'openai/gpt-5',
              // Google models
              'google/gemini-3-pro-preview',
              'google/gemini-3-flash-preview',
              'google/gemini-2.5-flash',
            ],
            description: 'AI model to use',
          },
          temperature: {
            name: 'temperature',
            type: 'number',
            required: false,
            default: 0.7,
            description: 'Temperature for generation (0-2)',
          },
          maxTokens: {
            name: 'maxTokens',
            type: 'number',
            required: false,
            description: 'Maximum tokens to generate',
          },
          reasoningEffort: {
            name: 'reasoningEffort',
            type: 'enum',
            required: false,
            enumValues: ['none', 'low', 'medium', 'high'],
            description:
              'Reasoning effort level for chain-of-thought. "none" only available for gpt-5.2.',
          },
        },
      },
      systemPrompt: {
        name: 'systemPrompt',
        type: 'string',
        required: false,
        description: 'System prompt for the agent',
      },
      tools: {
        name: 'tools',
        type: 'array',
        required: false,
        default: [],
        description: 'Tools available to the agent',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        response: { type: 'string', description: 'AI response text' },
        toolCalls: { type: 'array', description: 'Tool calls made' },
        iterations: { type: 'number', description: 'Number of iterations' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'GOOGLE_GEMINI_CRED',
  },

  'http': {
    name: 'http',
    className: 'HttpBubble',
    type: 'service',
    shortDescription: 'Make HTTP requests',
    longDescription: 'Make HTTP requests to external APIs and services',
    icon: 'globe',
    color: '#3B82F6',
    schema: {
      url: {
        name: 'url',
        type: 'string',
        required: true,
        description: 'The URL to request',
      },
      method: {
        name: 'method',
        type: 'enum',
        required: false,
        default: 'GET',
        enumValues: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'],
        description: 'HTTP method',
      },
      headers: {
        name: 'headers',
        type: 'object',
        required: false,
        description: 'Request headers',
      },
      body: {
        name: 'body',
        type: 'object',
        required: false,
        description: 'Request body',
      },
      timeout: {
        name: 'timeout',
        type: 'number',
        required: false,
        default: 30000,
        description: 'Timeout in milliseconds',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        status: { type: 'number', description: 'HTTP status code' },
        statusText: { type: 'string' },
        headers: { type: 'object' },
        body: { type: 'string' },
        json: { type: 'object' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'none',
  },

  'slack': {
    name: 'slack',
    className: 'SlackBubble',
    type: 'service',
    shortDescription: 'Send Slack messages',
    longDescription: 'Send messages to Slack channels or users',
    icon: 'slack',
    color: '#4A154B',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['sendMessage', 'replyToThread', 'updateMessage', 'deleteMessage'],
        description: 'Slack action to perform',
      },
      channel: {
        name: 'channel',
        type: 'string',
        required: true,
        description: 'Channel ID or name',
      },
      text: {
        name: 'text',
        type: 'string',
        required: false,
        description: 'Message text',
      },
      blocks: {
        name: 'blocks',
        type: 'array',
        required: false,
        description: 'Slack Block Kit blocks',
      },
      threadTs: {
        name: 'threadTs',
        type: 'string',
        required: false,
        description: 'Thread timestamp for replies',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        ts: { type: 'string', description: 'Message timestamp' },
        channel: { type: 'string' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'oauth',
    credentialType: 'SLACK_CRED',
  },

  'postgresql': {
    name: 'postgresql',
    className: 'PostgreSQLBubble',
    type: 'service',
    shortDescription: 'Query PostgreSQL database',
    longDescription: 'Execute SQL queries against a PostgreSQL database',
    icon: 'database',
    color: '#336791',
    schema: {
      query: {
        name: 'query',
        type: 'string',
        required: true,
        description: 'SQL query to execute',
      },
      params: {
        name: 'params',
        type: 'array',
        required: false,
        description: 'Query parameters',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        rows: { type: 'array', description: 'Query results' },
        rowCount: { type: 'number' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'connection-string',
    credentialType: 'DATABASE_CRED',
  },

  'gmail': {
    name: 'gmail',
    className: 'GmailBubble',
    type: 'service',
    shortDescription: 'Send emails via Gmail',
    longDescription: 'Send and manage emails through Gmail API',
    icon: 'mail',
    color: '#EA4335',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['sendEmail', 'getEmails', 'getEmail', 'searchEmails'],
        description: 'Gmail action',
      },
      to: {
        name: 'to',
        type: 'string',
        required: false,
        description: 'Recipient email address',
      },
      subject: {
        name: 'subject',
        type: 'string',
        required: false,
        description: 'Email subject',
      },
      body: {
        name: 'body',
        type: 'string',
        required: false,
        description: 'Email body',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        messageId: { type: 'string' },
        emails: { type: 'array' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'oauth',
    credentialType: 'GMAIL_CRED',
  },

  'google-sheets': {
    name: 'google-sheets',
    className: 'GoogleSheetsBubble',
    type: 'service',
    shortDescription: 'Read/write Google Sheets',
    longDescription: 'Read and write data to Google Sheets',
    icon: 'table',
    color: '#0F9D58',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['getRows', 'appendRow', 'updateRow', 'deleteRow', 'getSheet'],
        description: 'Sheets action',
      },
      spreadsheetId: {
        name: 'spreadsheetId',
        type: 'string',
        required: true,
        description: 'Google Sheets spreadsheet ID',
      },
      range: {
        name: 'range',
        type: 'string',
        required: false,
        description: 'Cell range (e.g., "Sheet1!A1:D10")',
      },
      values: {
        name: 'values',
        type: 'array',
        required: false,
        description: 'Values to write',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        values: { type: 'array' },
        updatedCells: { type: 'number' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'oauth',
    credentialType: 'GOOGLE_SHEETS_CRED',
  },

  'notion': {
    name: 'notion',
    className: 'NotionBubble',
    type: 'service',
    shortDescription: 'Interact with Notion',
    longDescription: 'Create, read, and update Notion pages and databases',
    icon: 'notion',
    color: '#000000',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['createPage', 'updatePage', 'getPage', 'queryDatabase', 'createDatabase'],
        description: 'Notion action',
      },
      databaseId: {
        name: 'databaseId',
        type: 'string',
        required: false,
        description: 'Notion database ID',
      },
      pageId: {
        name: 'pageId',
        type: 'string',
        required: false,
        description: 'Notion page ID',
      },
      properties: {
        name: 'properties',
        type: 'object',
        required: false,
        description: 'Page properties',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        page: { type: 'object' },
        results: { type: 'array' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'oauth',
    credentialType: 'NOTION_OAUTH_TOKEN',
  },

  'telegram': {
    name: 'telegram',
    className: 'TelegramBubble',
    type: 'service',
    shortDescription: 'Send Telegram messages',
    longDescription: 'Send messages via Telegram Bot API',
    icon: 'send',
    color: '#0088CC',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['sendMessage', 'sendPhoto', 'sendDocument'],
        description: 'Telegram action',
      },
      chatId: {
        name: 'chatId',
        type: 'string',
        required: true,
        description: 'Telegram chat ID',
      },
      text: {
        name: 'text',
        type: 'string',
        required: false,
        description: 'Message text',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        messageId: { type: 'number' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'TELEGRAM_BOT_TOKEN',
  },

  'resend': {
    name: 'resend',
    className: 'ResendBubble',
    type: 'service',
    shortDescription: 'Send emails via Resend',
    longDescription: 'Send transactional emails through Resend API',
    icon: 'mail',
    color: '#000000',
    schema: {
      from: {
        name: 'from',
        type: 'string',
        required: true,
        description: 'Sender email address',
      },
      to: {
        name: 'to',
        type: 'string',
        required: true,
        description: 'Recipient email address',
      },
      subject: {
        name: 'subject',
        type: 'string',
        required: true,
        description: 'Email subject',
      },
      html: {
        name: 'html',
        type: 'string',
        required: false,
        description: 'HTML email body',
      },
      text: {
        name: 'text',
        type: 'string',
        required: false,
        description: 'Plain text email body',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        id: { type: 'string' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'RESEND_CRED',
  },

  'github': {
    name: 'github',
    className: 'GithubBubble',
    type: 'service',
    shortDescription: 'Interact with GitHub',
    longDescription: 'Interact with GitHub repositories, issues, and PRs',
    icon: 'github',
    color: '#181717',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['getRepo', 'listIssues', 'createIssue', 'createPR', 'getFile'],
        description: 'GitHub action',
      },
      owner: {
        name: 'owner',
        type: 'string',
        required: true,
        description: 'Repository owner',
      },
      repo: {
        name: 'repo',
        type: 'string',
        required: true,
        description: 'Repository name',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        data: { type: 'object' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'GITHUB_TOKEN',
  },

  // ============================================
  // TOOL BUBBLES
  // ============================================

  'reddit-scrape-tool': {
    name: 'reddit-scrape-tool',
    className: 'RedditScrapeTool',
    type: 'tool',
    shortDescription: 'Scrape Reddit posts',
    longDescription: 'Scrape posts from any Reddit subreddit',
    icon: 'reddit',
    color: '#FF4500',
    schema: {
      subreddit: {
        name: 'subreddit',
        type: 'string',
        required: true,
        description: 'Subreddit name to scrape (without r/)',
      },
      limit: {
        name: 'limit',
        type: 'number',
        required: false,
        default: 10,
        description: 'Number of posts to fetch',
      },
      sort: {
        name: 'sort',
        type: 'enum',
        required: false,
        default: 'hot',
        enumValues: ['hot', 'new', 'top', 'rising'],
        description: 'Sort order',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        posts: {
          type: 'array',
          description: 'Array of Reddit posts',
        },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'none',
  },

  'web-search-tool': {
    name: 'web-search-tool',
    className: 'WebSearchTool',
    type: 'tool',
    shortDescription: 'Search the web',
    longDescription: 'Perform web searches and get results',
    icon: 'search',
    color: '#4285F4',
    schema: {
      query: {
        name: 'query',
        type: 'string',
        required: true,
        description: 'Search query',
      },
      limit: {
        name: 'limit',
        type: 'number',
        required: false,
        default: 10,
        description: 'Number of results',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        results: { type: 'array' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'none',
  },

  'web-scrape-tool': {
    name: 'web-scrape-tool',
    className: 'WebScrapeTool',
    type: 'tool',
    shortDescription: 'Scrape web pages',
    longDescription: 'Extract content from web pages',
    icon: 'globe',
    color: '#059669',
    schema: {
      url: {
        name: 'url',
        type: 'string',
        required: true,
        description: 'URL to scrape',
      },
      selector: {
        name: 'selector',
        type: 'string',
        required: false,
        description: 'CSS selector to extract',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        content: { type: 'string' },
        title: { type: 'string' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'none',
  },

  'twitter-tool': {
    name: 'twitter-tool',
    className: 'TwitterTool',
    type: 'tool',
    shortDescription: 'Scrape Twitter/X',
    longDescription: 'Scrape tweets and profiles from Twitter/X',
    icon: 'twitter',
    color: '#1DA1F2',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['searchTweets', 'getProfile', 'getTweets'],
        description: 'Twitter action',
      },
      query: {
        name: 'query',
        type: 'string',
        required: false,
        description: 'Search query or username',
      },
      limit: {
        name: 'limit',
        type: 'number',
        required: false,
        default: 10,
        description: 'Number of results',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        tweets: { type: 'array' },
        profile: { type: 'object' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'APIFY_CRED',
  },

  'linkedin-tool': {
    name: 'linkedin-tool',
    className: 'LinkedInTool',
    type: 'tool',
    shortDescription: 'Scrape LinkedIn',
    longDescription: 'Scrape LinkedIn profiles, posts, and jobs',
    icon: 'linkedin',
    color: '#0A66C2',
    schema: {
      operation: {
        name: 'operation',
        type: 'enum',
        required: true,
        enumValues: ['scrapePosts', 'searchPosts', 'scrapeJobs'],
        description: 'Operation to perform: scrapePosts (profiles), searchPosts (keywords), or scrapeJobs',
      },
      username: {
        name: 'username',
        type: 'string',
        required: false,
        description: 'LinkedIn username for scrapePosts operation (e.g., "satyanadella", "billgates")',
      },
      keyword: {
        name: 'keyword',
        type: 'string',
        required: false,
        description: 'Keyword or phrase to search for (searchPosts/scrapeJobs)',
      },
      location: {
        name: 'location',
        type: 'string',
        required: false,
        description: 'Location for job search (e.g., "San Francisco", "Remote")',
      },
      sortBy: {
        name: 'sortBy',
        type: 'enum',
        required: false,
        enumValues: ['relevance', 'date_posted'],
        default: 'relevance',
        description: 'Sort results by relevance or date posted',
      },
      dateFilter: {
        name: 'dateFilter',
        type: 'enum',
        required: false,
        enumValues: ['', 'past-24h', 'past-week', 'past-month'],
        default: '',
        description: 'Filter posts/jobs by date range',
      },
      limit: {
        name: 'limit',
        type: 'number',
        required: false,
        default: 50,
        description: 'Maximum number of items to fetch (default: 50, max: 1000)',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        operation: { type: 'string' },
        posts: { type: 'array' },
        jobs: { type: 'array' },
        username: { type: 'string' },
        keyword: { type: 'string' },
        totalResults: { type: 'number' },
        hasNextPage: { type: 'boolean' },
      },
    },
    authType: 'apikey',
    credentialType: 'APIFY_CRED',
  },

  'instagram-tool': {
    name: 'instagram-tool',
    className: 'InstagramTool',
    type: 'tool',
    shortDescription: 'Scrape Instagram',
    longDescription: 'Scrape Instagram profiles, posts, and hashtags',
    icon: 'instagram',
    color: '#E4405F',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['getProfile', 'getPosts', 'searchHashtag'],
        description: 'Instagram action',
      },
      username: {
        name: 'username',
        type: 'string',
        required: false,
        description: 'Instagram username',
      },
      hashtag: {
        name: 'hashtag',
        type: 'string',
        required: false,
        description: 'Hashtag to search',
      },
      limit: {
        name: 'limit',
        type: 'number',
        required: false,
        default: 10,
        description: 'Number of results',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        profile: { type: 'object' },
        posts: { type: 'array' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'APIFY_CRED',
  },

  'youtube-tool': {
    name: 'youtube-tool',
    className: 'YouTubeTool',
    type: 'tool',
    shortDescription: 'Scrape YouTube',
    longDescription: 'Scrape YouTube videos, channels, and transcripts',
    icon: 'youtube',
    color: '#FF0000',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['searchVideos', 'getChannel', 'getTranscript'],
        description: 'YouTube action',
      },
      query: {
        name: 'query',
        type: 'string',
        required: false,
        description: 'Search query or video URL',
      },
      limit: {
        name: 'limit',
        type: 'number',
        required: false,
        default: 10,
        description: 'Number of results',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        videos: { type: 'array' },
        transcript: { type: 'string' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'APIFY_CRED',
  },

  'tiktok-tool': {
    name: 'tiktok-tool',
    className: 'TikTokTool',
    type: 'tool',
    shortDescription: 'Scrape TikTok',
    longDescription: 'Scrape TikTok videos and profiles',
    icon: 'tiktok',
    color: '#000000',
    schema: {
      action: {
        name: 'action',
        type: 'enum',
        required: true,
        enumValues: ['searchVideos', 'getProfile', 'getTrending'],
        description: 'TikTok action',
      },
      query: {
        name: 'query',
        type: 'string',
        required: false,
        description: 'Search query or username',
      },
      limit: {
        name: 'limit',
        type: 'number',
        required: false,
        default: 10,
        description: 'Number of results',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        videos: { type: 'array' },
        profile: { type: 'object' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'APIFY_CRED',
  },

  'google-maps-tool': {
    name: 'google-maps-tool',
    className: 'GoogleMapsTool',
    type: 'tool',
    shortDescription: 'Scrape Google Maps',
    longDescription: 'Scrape business listings from Google Maps',
    icon: 'map',
    color: '#4285F4',
    schema: {
      query: {
        name: 'query',
        type: 'string',
        required: true,
        description: 'Search query (e.g., "restaurants in NYC")',
      },
      limit: {
        name: 'limit',
        type: 'number',
        required: false,
        default: 20,
        description: 'Number of results',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        places: { type: 'array' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'APIFY_CRED',
  },

  'research-agent-tool': {
    name: 'research-agent-tool',
    className: 'ResearchAgentTool',
    type: 'tool',
    shortDescription: 'AI-powered research',
    longDescription: 'Conduct AI-powered research on any topic',
    icon: 'microscope',
    color: '#7C3AED',
    schema: {
      topic: {
        name: 'topic',
        type: 'string',
        required: true,
        description: 'Research topic or question',
      },
      depth: {
        name: 'depth',
        type: 'enum',
        required: false,
        default: 'medium',
        enumValues: ['shallow', 'medium', 'deep'],
        description: 'Research depth',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        summary: { type: 'string' },
        sources: { type: 'array' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'apikey',
    credentialType: 'GOOGLE_GEMINI_CRED',
  },

  // ============================================
  // WORKFLOW BUBBLES
  // ============================================

  'database-analyzer': {
    name: 'database-analyzer',
    className: 'DatabaseAnalyzerWorkflowBubble',
    type: 'workflow',
    shortDescription: 'Analyze database schema',
    longDescription: 'AI-powered database schema analysis and optimization suggestions',
    icon: 'database',
    color: '#0EA5E9',
    schema: {
      connectionString: {
        name: 'connectionString',
        type: 'string',
        required: true,
        description: 'Database connection string',
      },
      analysisType: {
        name: 'analysisType',
        type: 'enum',
        required: false,
        enumValues: ['schema', 'performance', 'security'],
        description: 'Type of analysis',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        analysis: { type: 'object' },
        recommendations: { type: 'array' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'connection-string',
    credentialType: 'DATABASE_CRED',
  },

  'slack-notifier': {
    name: 'slack-notifier',
    className: 'SlackNotifierWorkflowBubble',
    type: 'workflow',
    shortDescription: 'Rich Slack notifications',
    longDescription: 'Send rich, formatted notifications to Slack with templates',
    icon: 'bell',
    color: '#4A154B',
    schema: {
      channel: {
        name: 'channel',
        type: 'string',
        required: true,
        description: 'Slack channel',
      },
      template: {
        name: 'template',
        type: 'enum',
        required: false,
        enumValues: ['success', 'error', 'warning', 'info', 'custom'],
        description: 'Notification template',
      },
      title: {
        name: 'title',
        type: 'string',
        required: true,
        description: 'Notification title',
      },
      message: {
        name: 'message',
        type: 'string',
        required: true,
        description: 'Notification message',
      },
    },
    resultSchema: {
      type: 'object',
      properties: {
        ts: { type: 'string' },
        success: { type: 'boolean' },
        error: { type: 'string' },
      },
    },
    authType: 'oauth',
    credentialType: 'SLACK_CRED',
  },
};

/**
 * Get bubble by name
 */
export function getBubble(name: string): BubbleDefinition | undefined {
  return BUBBLE_REGISTRY[name];
}

/**
 * Get all bubbles of a specific type
 */
export function getBubblesByType(type: BubbleType): BubbleDefinition[] {
  return Object.values(BUBBLE_REGISTRY).filter((b) => b.type === type);
}

/**
 * Get all bubble names
 */
export function getAllBubbleNames(): string[] {
  return Object.keys(BUBBLE_REGISTRY);
}

/**
 * Search bubbles by name or description
 */
export function searchBubbles(query: string): BubbleDefinition[] {
  const lowerQuery = query.toLowerCase();
  return Object.values(BUBBLE_REGISTRY).filter(
    (b) =>
      b.name.toLowerCase().includes(lowerQuery) ||
      b.shortDescription.toLowerCase().includes(lowerQuery) ||
      b.className.toLowerCase().includes(lowerQuery)
  );
}

/**
 * Compact bubble summary for AI context
 */
export interface BubbleSummaryForAI {
  name: string;
  className: string;
  type: BubbleType;
  description: string;
  icon: string;
  color: string;
  parameters: {
    name: string;
    type: string;
    required: boolean;
    description?: string;
    enumValues?: string[];
    default?: unknown;
  }[];
  authType?: 'oauth' | 'apikey' | 'none' | 'connection-string';
}

/**
 * Get bubble registry in a compact format suitable for AI context.
 * Groups bubbles by type and extracts essential parameter info.
 */
export function getBubbleRegistryForAI(): {
  services: BubbleSummaryForAI[];
  tools: BubbleSummaryForAI[];
  workflows: BubbleSummaryForAI[];
} {
  const bubbles = Object.values(BUBBLE_REGISTRY);

  const transformBubble = (bubble: BubbleDefinition): BubbleSummaryForAI => {
    const parameters = Object.entries(bubble.schema).map(([key, param]) => ({
      name: key,
      type: param.type,
      required: param.required ?? false,
      description: param.description,
      enumValues: param.enumValues,
      default: param.default,
    }));

    return {
      name: bubble.name,
      className: bubble.className,
      type: bubble.type,
      description: bubble.shortDescription,
      icon: bubble.icon,
      color: bubble.color,
      parameters,
      authType: bubble.authType,
    };
  };

  return {
    services: bubbles.filter((b) => b.type === 'service').map(transformBubble),
    tools: bubbles.filter((b) => b.type === 'tool').map(transformBubble),
    workflows: bubbles.filter((b) => b.type === 'workflow').map(transformBubble),
  };
}
