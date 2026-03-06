'use client';

import React, { useState, useRef, useEffect } from 'react';
import { MoreVertical, Trash2, FileText, Tag } from 'lucide-react';
import { clsx } from 'clsx';
import type { Artifact } from '@/lib/artifacts';

interface ArtifactWithPreview extends Artifact {
  entryCount?: number;
  latestEntrySnippet?: string | null;
}

interface ArtifactCardProps {
  artifact: ArtifactWithPreview;
  onClick: () => void;
  onDelete: () => void;
}

export function ArtifactCard({ artifact, onClick, onDelete }: ArtifactCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };

    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [menuOpen]);

  return (
    <div
      onClick={onClick}
      className={clsx(
        'group relative p-4 rounded-lg border border-border bg-card',
        'hover:border-foreground/10 hover:translate-y-[-1px] transition-all duration-200 cursor-pointer',
        'hover:shadow-md'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0 pr-2">
          <h3 className="font-medium truncate">{artifact.title}</h3>
          {artifact.summary && (
            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
              {artifact.summary}
            </p>
          )}
        </div>

        {/* Actions menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen(!menuOpen);
            }}
            className={clsx(
              'p-1.5 rounded-md transition-colors',
              'opacity-0 group-hover:opacity-100',
              'hover:bg-accent',
              menuOpen && 'opacity-100 bg-accent'
            )}
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {menuOpen && (
            <div
              className={clsx(
                'absolute right-0 top-full mt-1 z-50',
                'w-40 py-1 rounded-lg shadow-lg',
                'bg-popover border border-border'
              )}
            >
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onClick();
                  setMenuOpen(false);
                }}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-accent"
              >
                <FileText className="w-4 h-4" />
                View Details
              </button>
              <div className="my-1 border-t border-border" />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                  setMenuOpen(false);
                }}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Tags */}
      {artifact.tags && artifact.tags.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap mb-3">
          <Tag className="w-3 h-3 text-muted-foreground" />
          {artifact.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs rounded-full bg-muted text-muted-foreground"
            >
              {tag}
            </span>
          ))}
          {artifact.tags.length > 3 && (
            <span className="text-xs text-muted-foreground">
              +{artifact.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Entry preview */}
      {artifact.latestEntrySnippet && (
        <p className="text-xs text-muted-foreground line-clamp-2 mb-3 italic">
          {artifact.latestEntrySnippet}
        </p>
      )}

      {/* Stats */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        {artifact.entryCount != null && (
          <span>{artifact.entryCount} {artifact.entryCount === 1 ? 'entry' : 'entries'}</span>
        )}
        <span>Updated {formatRelativeTime(artifact.updatedAt)}</span>
      </div>
    </div>
  );
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}
