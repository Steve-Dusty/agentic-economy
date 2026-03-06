'use client';

import React from 'react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import type { AIAssistantContext } from '@/lib/ai-assistant/types';

interface ConnectionStatusProps {
  context: AIAssistantContext | null;
}

// Normalize app names for consistent matching
// Removes underscores, hyphens, and spaces, then uppercases
function normalizeAppName(name: string): string {
  return name.toUpperCase().replace(/[_\-\s]/g, '');
}

// Map of various app name formats to our canonical names
// Composio may return names like "google_calendar", "googlecalendar", "GOOGLE_CALENDAR", etc.
const APP_NAME_ALIASES: Record<string, string[]> = {
  // Google Services - map normalized form to all variations we check
  GMAIL: ['GMAIL'],
  GOOGLECALENDAR: ['GOOGLECALENDAR', 'GOOGLE_CALENDAR', 'GCALENDAR'],
  GOOGLEDRIVE: ['GOOGLEDRIVE', 'GOOGLE_DRIVE', 'GDRIVE'],
  GOOGLEDOCS: ['GOOGLEDOCS', 'GOOGLE_DOCS', 'GDOCS'],
  GOOGLESHEETS: ['GOOGLESHEETS', 'GOOGLE_SHEETS', 'GSHEETS'],
  GOOGLETASKS: ['GOOGLETASKS', 'GOOGLE_TASKS', 'GTASKS'],
  GOOGLEMAPS: ['GOOGLEMAPS', 'GOOGLE_MAPS', 'GMAPS'],
  GOOGLEMEET: ['GOOGLEMEET', 'GOOGLE_MEET', 'GMEET'],
  YOUTUBE: ['YOUTUBE'],

  // Microsoft Services
  OUTLOOK: ['OUTLOOK', 'MICROSOFTOUTLOOK', 'MS_OUTLOOK'],
  ONEDRIVE: ['ONEDRIVE', 'ONE_DRIVE', 'MICROSOFT_ONEDRIVE'],
  MICROSOFTTEAMS: ['MICROSOFTTEAMS', 'MICROSOFT_TEAMS', 'MSTEAMS', 'TEAMS'],

  // Others with variations
  BROWSERBASETOOL: ['BROWSERBASETOOL', 'BROWSERBASE_TOOL', 'BROWSERBASE'],
};

// Build reverse lookup: from any variation to normalized form
const VARIATION_TO_NORMALIZED: Record<string, string> = {};
for (const [normalized, variations] of Object.entries(APP_NAME_ALIASES)) {
  for (const variation of variations) {
    VARIATION_TO_NORMALIZED[variation.replace(/[_\-\s]/g, '')] = normalized;
  }
}

function getNormalizedAppName(name: string): string {
  const cleaned = normalizeAppName(name);
  return VARIATION_TO_NORMALIZED[cleaned] || cleaned;
}

export function ConnectionStatus({ context }: ConnectionStatusProps) {
  if (!context) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm">Loading connections...</span>
      </div>
    );
  }

  const connectedAccounts = context.composio.connectedAccounts;

  // Build a set of normalized connected toolkit names for flexible matching
  const connectedToolkitsNormalized = new Set(
    connectedAccounts
      .filter((acc) => acc.status === 'ACTIVE')
      .map((acc) => getNormalizedAppName(acc.toolkit))
  );

  const availableToolkits = context.composio.availableToolkits;
  const connectedCount = connectedToolkitsNormalized.size;

  // Service display info
  const serviceInfo: Record<string, { name: string; icon: string }> = {
    // Google Services
    GMAIL: { name: 'Gmail', icon: '📧' },
    GOOGLECALENDAR: { name: 'Calendar', icon: '📅' },
    GOOGLEDRIVE: { name: 'Drive', icon: '📁' },
    GOOGLEDOCS: { name: 'Docs', icon: '📄' },
    GOOGLESHEETS: { name: 'Sheets', icon: '📊' },
    GOOGLETASKS: { name: 'Tasks', icon: '✅' },
    GOOGLE_MAPS: { name: 'Maps', icon: '🗺️' },
    GOOGLEMEET: { name: 'Meet', icon: '📹' },
    YOUTUBE: { name: 'YouTube', icon: '▶️' },

    // Microsoft Services
    OUTLOOK: { name: 'Outlook', icon: '📬' },
    ONE_DRIVE: { name: 'OneDrive', icon: '☁️' },
    MICROSOFT_TEAMS: { name: 'Teams', icon: '👥' },

    // Communication
    SLACK: { name: 'Slack', icon: '💬' },
    DISCORD: { name: 'Discord', icon: '🎮' },

    // Productivity
    NOTION: { name: 'Notion', icon: '📝' },
    LINEAR: { name: 'Linear', icon: '📐' },
    JIRA: { name: 'Jira', icon: '🎫' },
    ASANA: { name: 'Asana', icon: '📋' },
    CALENDLY: { name: 'Calendly', icon: '🗓️' },
    CANVAS: { name: 'Canvas', icon: '🎓' },

    // Development
    GITHUB: { name: 'GitHub', icon: '🐙' },
    FIGMA: { name: 'Figma', icon: '🎨' },

    // Social
    TWITTER: { name: 'X', icon: '𝕏' },
    LINKEDIN: { name: 'LinkedIn', icon: '💼' },
    REDDIT: { name: 'Reddit', icon: '🤖' },

    // Design & Creative
    CANVA: { name: 'Canva', icon: '🖼️' },

    // Sales & CRM
    SALESFORCE: { name: 'Salesforce', icon: '☁️' },
    APOLLO: { name: 'Apollo', icon: '🚀' },

    // Search & Tools
    EXA: { name: 'Exa', icon: '🔍' },
    BROWSERBASE_TOOL: { name: 'Browserbase', icon: '🌐' },
    FIRECRAWL: { name: 'Firecrawl', icon: '🔥' },
  };

  return (
    <div>
      <h4 className="text-sm font-medium mb-3">
        Services ({connectedCount}/{availableToolkits.length} connected)
      </h4>
      <div className="space-y-2">
        {availableToolkits.map((toolkit) => {
          const upperToolkit = toolkit.toUpperCase();
          const normalizedToolkit = getNormalizedAppName(toolkit);
          // Check if any connected account matches this toolkit (using normalized names)
          const isConnected = connectedToolkitsNormalized.has(normalizedToolkit);
          const info = serviceInfo[upperToolkit] || {
            name: toolkit,
            icon: '🔌',
          };

          return (
            <div
              key={toolkit}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 rounded-md text-sm',
                isConnected ? 'bg-green-500/10' : 'bg-muted/50'
              )}
            >
              {isConnected ? (
                <CheckCircle2 className="w-4 h-4 text-green-500" />
              ) : (
                <Circle className="w-4 h-4 text-muted-foreground" />
              )}
              <span>{info.icon}</span>
              <span className={isConnected ? 'font-medium' : 'text-muted-foreground'}>
                {info.name}
              </span>
              {isConnected && (
                <span className="ml-auto text-xs text-green-600">
                  Connected
                </span>
              )}
            </div>
          );
        })}
      </div>
      <p className="text-xs text-muted-foreground mt-3">
        Connected services can be used directly in workflows.
        Connect more services in Settings.
      </p>
    </div>
  );
}
