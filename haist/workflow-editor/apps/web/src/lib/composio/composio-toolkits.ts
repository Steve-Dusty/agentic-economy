/**
 * Composio Toolkits Data
 *
 * Static metadata for Composio toolkits and their tools.
 * This provides tool descriptions for the UI when dynamic fetching isn't available.
 */

export interface ComposioToolDefinition {
  name: string;
  description: string;
  inputs: string;
  outputs: string;
}

export interface ComposioToolkitDefinition {
  toolkit: string;
  label: string;
  icon: string;
  tools: ComposioToolDefinition[];
}

/**
 * Auth config ID environment variable mapping
 */
export const AUTH_CONFIG_MAP: Record<string, string> = {
  // Google Services
  GMAIL: 'GMAIL_AUTH_CONFIG_ID',
  GOOGLECALENDAR: 'GOOGLE_CALENDAR_AUTH_CONFIG_ID',
  GOOGLEDRIVE: 'GOOGLE_DRIVE_AUTH_CONFIG_ID',
  GOOGLEDOCS: 'GOOGLE_DOCS_AUTH_CONFIG_ID',
  GOOGLESHEETS: 'GOOGLE_SHEETS_AUTH_CONFIG_ID',
  GOOGLETASKS: 'GOOGLE_TASKS_AUTH_CONFIG_ID',
  GOOGLE_MAPS: 'GOOGLE_MAPS_AUTH_CONFIG_ID',
  GOOGLEMEET: 'GOOGLEMEET_AUTH_CONFIG_ID',
  YOUTUBE: 'YOUTUBE_AUTH_CONFIG_ID',

  // Microsoft Services
  OUTLOOK: 'OUTLOOK_AUTH_CONFIG_ID',
  ONE_DRIVE: 'ONE_DRIVE_AUTH_CONFIG_ID',
  MICROSOFT_TEAMS: 'MICROSOFT_TEAMS_AUTH_CONFIG_ID',

  // Communication
  SLACK: 'SLACK_AUTH_CONFIG_ID',
  DISCORD: 'DISCORD_AUTH_CONFIG_ID',

  // Productivity
  NOTION: 'NOTION_AUTH_CONFIG_ID',
  LINEAR: 'LINEAR_AUTH_CONFIG_ID',
  JIRA: 'JIRA_AUTH_CONFIG_ID',
  ASANA: 'ASANA_AUTH_CONFIG_ID',
  CALENDLY: 'CALENDLY_AUTH_CONFIG_ID',
  CANVAS: 'CANVAS_AUTH_CONFIG_ID',

  // Development
  GITHUB: 'GITHUB_AUTH_CONFIG_ID',
  FIGMA: 'FIGMA_AUTH_CONFIG_ID',

  // Social
  TWITTER: 'TWITTER_AUTH_CONFIG_ID',
  LINKEDIN: 'LINKEDIN_AUTH_CONFIG_ID',
  REDDIT: 'REDDIT_AUTH_CONFIG_ID',

  // Design & Creative
  CANVA: 'CANVA_AUTH_CONFIG_ID',

  // Sales & CRM
  SALESFORCE: 'SALESFORCE_AUTH_CONFIG_ID',
  APOLLO: 'APOLLO_AUTH_CONFIG_ID',

  // Search & Tools
  EXA: 'EXA_AUTH_CONFIG_ID',
  BROWSERBASE_TOOL: 'BROWSERBASE_TOOL_AUTH_CONFIG_ID',
  FIRECRAWL:'FIRECRAWL_AUTH_CONFIG_ID',
};

/**
 * Get auth config ID for a toolkit
 */
export function getAuthConfigId(toolkit: string): string | undefined {
  const envVar = AUTH_CONFIG_MAP[toolkit.toUpperCase()];
  return envVar ? process.env[envVar] : undefined;
}

/**
 * Composio Toolkits Data
 */
export const COMPOSIO_TOOLKITS_DATA: ComposioToolkitDefinition[] = [
  {
    toolkit: 'GMAIL',
    label: 'Gmail',
    icon: '📧',
    tools: [
      {
        name: 'GMAIL_SEND_EMAIL',
        description:
          'Sends an email via Gmail API. At least one recipient (recipient_email, cc, or bcc) and at least one of subject or body must be provided.',
        inputs:
          'recipient_email: string (Required, the email address to send to), subject: string (Required, email subject line), body: string (Required, email body text), is_html?: boolean (set to true if body contains HTML), cc?: array of email strings, bcc?: array of email strings',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GMAIL_FETCH_EMAILS',
        description:
          'Fetches a list of email messages from a Gmail account, supporting filtering and pagination.',
        inputs:
          'max_results?: integer, query?: string, label_ids?: array, include_payload?: boolean',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GMAIL_CREATE_EMAIL_DRAFT',
        description:
          'Creates a Gmail email draft. Supports To/Cc/Bcc, subject, plain/HTML body, and attachments.',
        inputs:
          'recipient_email?: string, subject?: string, body?: string, cc?: array, bcc?: array, is_html?: boolean',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GMAIL_REPLY_TO_THREAD',
        description:
          'Sends a reply within a specific Gmail thread using the original thread subject.',
        inputs:
          'thread_id: string (Required), recipient_email?: string, message_body?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GMAIL_LIST_THREADS',
        description:
          'Retrieves a list of email threads from a Gmail account with filtering and pagination.',
        inputs: 'max_results?: integer, query?: string, verbose?: boolean',
        outputs: 'data: object, successful: boolean, error?: string',
      },
    ],
  },
  {
    toolkit: 'GOOGLECALENDAR',
    label: 'Google Calendar',
    icon: '📅',
    tools: [
      {
        name: 'GOOGLECALENDAR_CREATE_EVENT',
        description: 'Creates a new calendar event using start_datetime plus duration fields.',
        inputs:
          'calendar_id: string (Required, use "primary" for main calendar), start_datetime: string (Required, ISO format like "2026-01-16T13:00:00"), timezone: string (Required, like "America/New_York"), event_duration_hour: number (Required), event_duration_minutes: number (default 0), summary: string (Required, event title), description?: string, location?: string, attendees?: array of email strings like ["user@example.com"]',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GOOGLECALENDAR_EVENTS_LIST',
        description: 'Returns events on the specified calendar.',
        inputs:
          'calendarId: string (Required), timeMin?: string, timeMax?: string, maxResults?: integer',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GOOGLECALENDAR_FREE_BUSY_QUERY',
        description: 'Returns free/busy information for a set of calendars.',
        inputs:
          'items: array (Required), timeMin: string (Required), timeMax: string (Required)',
        outputs: 'data: object, successful: boolean, error?: string',
      },
    ],
  },
  {
    toolkit: 'SLACK',
    label: 'Slack',
    icon: '💬',
    tools: [
      {
        name: 'SLACK_SEND_MESSAGE',
        description:
          'Posts a message to a Slack channel, direct message, or private group.',
        inputs:
          'channel: string (Required), text?: string, blocks?: string, attachments?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'SLACK_CREATE_CHANNEL',
        description: 'Initiates a public or private channel-based conversation.',
        inputs: 'name: string (Required), is_private?: boolean',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'SLACK_LIST_ALL_USERS',
        description:
          'Retrieves a paginated list of all users in a Slack workspace.',
        inputs: 'limit?: integer, cursor?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'SLACK_FETCH_CONVERSATION_HISTORY',
        description:
          'Fetches a chronological list of messages from a Slack conversation.',
        inputs: 'channel: string (Required), limit?: integer, oldest?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
    ],
  },
  {
    toolkit: 'NOTION',
    label: 'Notion',
    icon: '📝',
    tools: [
      {
        name: 'NOTION_CREATE_NOTION_PAGE',
        description:
          'Creates a new empty page under a specified parent page or database.',
        inputs: 'parent_id: string (Required), title: string (Required), icon?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'NOTION_ADD_PAGE_CONTENT',
        description: 'Adds a content block to a Notion page/block.',
        inputs:
          'parent_block_id: string (Required), content_block: object (Required)',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'NOTION_QUERY_DATABASE',
        description: 'Queries a Notion database to retrieve pages (rows).',
        inputs:
          'database_id: string (Required), page_size?: integer, sorts?: array',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'NOTION_SEARCH_NOTION_PAGE',
        description:
          'Searches Notion pages and databases by title.',
        inputs: 'query?: string, page_size?: integer',
        outputs: 'data: object, successful: boolean, error?: string',
      },
    ],
  },
  {
    toolkit: 'GOOGLEDRIVE',
    label: 'Google Drive',
    icon: '📁',
    tools: [
      {
        name: 'GOOGLEDRIVE_LIST_FILES',
        description: 'Lists a user\'s files and folders in Google Drive.',
        inputs: 'pageSize?: integer, q?: string, folderId?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GOOGLEDRIVE_UPLOAD_FILE',
        description: 'Uploads a file (max 5MB) to Google Drive.',
        inputs:
          'file_to_upload: object (Required), folder_to_upload_to?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GOOGLEDRIVE_CREATE_FOLDER',
        description:
          'Creates a new folder in Google Drive, optionally within a parent folder.',
        inputs: 'folder_name: string (Required), parent_id?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
    ],
  },
  {
    toolkit: 'GOOGLEDOCS',
    label: 'Google Docs',
    icon: '📄',
    tools: [
      {
        name: 'GOOGLEDOCS_CREATE_DOCUMENT',
        description:
          'Creates a new Google Docs document with the provided title and initial text.',
        inputs: 'title: string (Required), text: string (Required)',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GOOGLEDOCS_GET_DOCUMENT_BY_ID',
        description: 'Retrieves an existing Google Document by its ID.',
        inputs: 'id: string (Required)',
        outputs: 'data: object, successful: boolean, error?: string',
      },
    ],
  },
  {
    toolkit: 'GOOGLESHEETS',
    label: 'Google Sheets',
    icon: '📊',
    tools: [
      {
        name: 'GOOGLESHEETS_CREATE_GOOGLE_SHEET1',
        description:
          'Creates a new Google Spreadsheet with the provided title.',
        inputs: 'title: string (Required)',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GOOGLESHEETS_BATCH_UPDATE',
        description:
          'Updates a specified range in a Google Sheet with given values.',
        inputs:
          'spreadsheet_id: string (Required), sheet_name: string (Required), values: array (Required)',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GOOGLESHEETS_BATCH_GET',
        description:
          'Retrieves data from specified cell ranges in a Google Spreadsheet.',
        inputs: 'spreadsheet_id: string (Required), ranges?: array',
        outputs: 'data: object, successful: boolean, error?: string',
      },
    ],
  },
  {
    toolkit: 'GITHUB',
    label: 'GitHub',
    icon: '🐙',
    tools: [
      {
        name: 'GITHUB_CREATE_ISSUE',
        description: 'Creates a new issue in a GitHub repository.',
        inputs:
          'owner: string (Required), repo: string (Required), title: string (Required), body?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'GITHUB_LIST_REPOSITORIES',
        description: 'Lists repositories for the authenticated user.',
        inputs: 'per_page?: integer, page?: integer, sort?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
    ],
  },
  {
    toolkit: 'OUTLOOK',
    label: 'Outlook',
    icon: '📬',
    tools: [
      {
        name: 'OUTLOOK_SEND_EMAIL',
        description:
          'Sends an email with subject, body, recipients via Microsoft Graph API.',
        inputs:
          'to_email: string (Required), subject: string (Required), body: string (Required), is_html?: boolean',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'OUTLOOK_CALENDAR_CREATE_EVENT',
        description: 'Creates a new Outlook calendar event.',
        inputs:
          'subject: string (Required), body: string (Required), start_datetime: string (Required), end_datetime: string (Required), time_zone: string (Required)',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'OUTLOOK_REPLY_TO_EMAIL',
        description:
          'Sends a plain text reply to an existing Outlook email message, identified by message_id. Keeps the email in the same thread.',
        inputs:
          'message_id: string (Required, the ID of the message to reply to), comment: string (Required, the reply body text), cc_emails?: array of email strings, bcc_emails?: array of email strings, user_id?: string (defaults to "me")',
        outputs: 'data: object, successful: boolean, error?: string',
      },
      {
        name: 'OUTLOOK_LIST_EVENTS',
        description:
          'Retrieves events from a user\'s Outlook calendar.',
        inputs: 'top?: integer, filter?: string, timezone?: string',
        outputs: 'data: object, successful: boolean, error?: string',
      },
    ],
  },
];

/**
 * Get toolkit by ID
 */
export function getComposioToolkit(
  toolkitId: string
): ComposioToolkitDefinition | undefined {
  return COMPOSIO_TOOLKITS_DATA.find(
    (t) => t.toolkit.toUpperCase() === toolkitId.toUpperCase()
  );
}

/**
 * Get all toolkits
 */
export function getAllComposioToolkits(): ComposioToolkitDefinition[] {
  return COMPOSIO_TOOLKITS_DATA;
}

/**
 * Get tool by name
 */
export function getComposioTool(
  toolName: string
): ComposioToolDefinition | undefined {
  for (const toolkit of COMPOSIO_TOOLKITS_DATA) {
    const tool = toolkit.tools.find((t) => t.name === toolName);
    if (tool) return tool;
  }
  return undefined;
}

/**
 * Get toolkit for a tool
 */
export function getToolkitForTool(
  toolName: string
): ComposioToolkitDefinition | undefined {
  for (const toolkit of COMPOSIO_TOOLKITS_DATA) {
    if (toolkit.tools.some((t) => t.name === toolName)) {
      return toolkit;
    }
  }
  return undefined;
}
