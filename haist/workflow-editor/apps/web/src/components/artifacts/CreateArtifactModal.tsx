'use client';

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { clsx } from 'clsx';
import type { Artifact } from '@/lib/artifacts';

interface CreateArtifactModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (artifact: Artifact) => void;
}

export function CreateArtifactModal({
  isOpen,
  onClose,
  onSuccess,
}: CreateArtifactModalProps) {
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState('');
  const [initialContent, setInitialContent] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setTitle('');
      setTags('');
      setInitialContent('');
      setError(null);
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!title.trim()) {
      setError('Please enter a title for the artifact');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const response = await fetch('/api/artifacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          tags: tags
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean),
          content: initialContent.trim() || undefined,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to create artifact');
      }

      const data = await response.json();
      onSuccess(data.artifact);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create artifact');
    } finally {
      setIsCreating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-card rounded-lg shadow-xl w-full max-w-md mx-4 border border-border">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold">Create New Artifact</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-md hover:bg-accent transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-md bg-destructive/10 text-destructive text-sm border border-destructive/20">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1.5">
              Title <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Meeting Notes with John"
              autoFocus
              className={clsx(
                'w-full px-3 py-2 rounded-md',
                'bg-background border border-input',
                'focus:outline-none focus:ring-2 focus:ring-ring'
              )}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">
              Tags{' '}
              <span className="text-muted-foreground font-normal">
                (comma-separated)
              </span>
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g., meetings, project-x, john"
              className={clsx(
                'w-full px-3 py-2 rounded-md',
                'bg-background border border-input',
                'focus:outline-none focus:ring-2 focus:ring-ring'
              )}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">
              Initial Content{' '}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </label>
            <textarea
              value={initialContent}
              onChange={(e) => setInitialContent(e.target.value)}
              placeholder="Add initial context or notes for this artifact..."
              rows={4}
              className={clsx(
                'w-full px-3 py-2 rounded-md resize-none',
                'bg-background border border-input',
                'focus:outline-none focus:ring-2 focus:ring-ring'
              )}
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-md hover:bg-accent transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className={clsx(
                'px-4 py-2 rounded-md',
                'bg-primary text-primary-foreground hover:bg-primary/90',
                'transition-colors',
                isCreating && 'opacity-50 cursor-not-allowed'
              )}
            >
              {isCreating ? 'Creating...' : 'Create Artifact'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
