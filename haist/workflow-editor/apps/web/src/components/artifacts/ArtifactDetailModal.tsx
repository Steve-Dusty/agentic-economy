'use client';

import React, { useEffect, useState } from 'react';
import { X, Pencil, Trash2, Plus, Save, FileText } from 'lucide-react';
import { clsx } from 'clsx';
import { useUIStore } from '@workflow-editor/state';
import type { Artifact, ArtifactWithEntries, ArtifactEntry } from '@/lib/artifacts';

interface ArtifactDetailModalProps {
  artifactId: string | null;
  onClose: () => void;
  onUpdate: (artifact: Artifact) => void;
  onDelete: (id: string) => void;
}

export function ArtifactDetailModal({
  artifactId,
  onClose,
  onUpdate,
  onDelete,
}: ArtifactDetailModalProps) {
  const [artifact, setArtifact] = useState<ArtifactWithEntries | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editSummary, setEditSummary] = useState('');
  const [editTags, setEditTags] = useState('');
  const [newEntryContent, setNewEntryContent] = useState('');
  const [isAddingEntry, setIsAddingEntry] = useState(false);
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);
  const [editEntryContent, setEditEntryContent] = useState('');

  const addNotification = useUIStore((state) => state.addNotification);

  // Fetch artifact details
  useEffect(() => {
    if (!artifactId) {
      setArtifact(null);
      return;
    }

    const fetchArtifact = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`/api/artifacts/${artifactId}`);
        if (!response.ok) throw new Error('Failed to fetch artifact');
        const data = await response.json();
        setArtifact(data.artifact);
        setEditTitle(data.artifact.title);
        setEditSummary(data.artifact.summary || '');
        setEditTags(data.artifact.tags?.join(', ') || '');
      } catch (err) {
        addNotification({
          type: 'error',
          title: 'Error',
          message: 'Failed to load artifact details',
        });
        onClose();
      } finally {
        setIsLoading(false);
      }
    };

    fetchArtifact();
  }, [artifactId, addNotification, onClose]);

  if (!artifactId) return null;

  const handleSave = async () => {
    if (!artifact) return;

    try {
      const response = await fetch(`/api/artifacts/${artifact.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editTitle.trim(),
          summary: editSummary.trim() || null,
          tags: editTags.split(',').map((t) => t.trim()).filter(Boolean),
        }),
      });

      if (!response.ok) throw new Error('Failed to update artifact');

      const data = await response.json();
      setArtifact((prev) => prev ? { ...prev, ...data.artifact } : null);
      onUpdate(data.artifact);
      setIsEditing(false);
      addNotification({
        type: 'success',
        title: 'Saved',
        message: 'Artifact updated successfully',
      });
    } catch {
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to save changes',
      });
    }
  };

  const handleAddEntry = async () => {
    if (!artifact || !newEntryContent.trim()) return;

    try {
      const response = await fetch(`/api/artifacts/${artifact.id}/entries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: newEntryContent.trim(),
          source: 'manual',
        }),
      });

      if (!response.ok) throw new Error('Failed to add entry');

      const data = await response.json();
      setArtifact((prev) =>
        prev
          ? {
              ...prev,
              entries: [data.entry, ...prev.entries],
            }
          : null
      );
      setNewEntryContent('');
      setIsAddingEntry(false);
      addNotification({
        type: 'success',
        title: 'Entry added',
        message: 'New entry has been added to the artifact',
      });
    } catch {
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to add entry',
      });
    }
  };

  const handleDelete = () => {
    if (!artifact) return;
    onDelete(artifact.id);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-card rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col border border-border">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          {isEditing ? (
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className={clsx(
                'flex-1 px-3 py-1.5 rounded-md text-lg font-semibold',
                'bg-background border border-input',
                'focus:outline-none focus:ring-2 focus:ring-ring'
              )}
              autoFocus
            />
          ) : (
            <h2 className="text-lg font-semibold">{artifact?.title || 'Loading...'}</h2>
          )}
          <div className="flex items-center gap-2 ml-4">
            {isEditing ? (
              <button
                onClick={handleSave}
                className="p-2 rounded-md hover:bg-accent text-primary"
                title="Save changes"
              >
                <Save className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="p-2 rounded-md hover:bg-accent"
                title="Edit"
              >
                <Pencil className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={handleDelete}
              className="p-2 rounded-md hover:bg-destructive/10 text-destructive"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-md hover:bg-accent"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          ) : artifact ? (
            <div className="space-y-6">
              {/* Summary */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-2">
                  Summary
                </h3>
                {isEditing ? (
                  <textarea
                    value={editSummary}
                    onChange={(e) => setEditSummary(e.target.value)}
                    placeholder="Add a summary..."
                    rows={2}
                    className={clsx(
                      'w-full px-3 py-2 rounded-md text-sm',
                      'bg-background border border-input',
                      'focus:outline-none focus:ring-2 focus:ring-ring',
                      'resize-none'
                    )}
                  />
                ) : artifact.summary ? (
                  <p className="text-sm">{artifact.summary}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">No summary</p>
                )}
              </div>

              {/* Tags */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-2">
                  Tags
                </h3>
                {isEditing ? (
                  <input
                    type="text"
                    value={editTags}
                    onChange={(e) => setEditTags(e.target.value)}
                    placeholder="Comma-separated tags..."
                    className={clsx(
                      'w-full px-3 py-2 rounded-md text-sm',
                      'bg-background border border-input',
                      'focus:outline-none focus:ring-2 focus:ring-ring'
                    )}
                  />
                ) : artifact.tags && artifact.tags.length > 0 ? (
                  <div className="flex gap-2 flex-wrap">
                    {artifact.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-1 text-xs rounded-full bg-primary/10 text-primary"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No tags</p>
                )}
              </div>

              {/* Entries */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-muted-foreground">
                    Entries ({artifact.entries?.length || 0})
                  </h3>
                  <button
                    onClick={() => setIsAddingEntry(true)}
                    className="flex items-center gap-1 text-sm text-primary hover:underline"
                  >
                    <Plus className="w-3 h-3" />
                    Add Entry
                  </button>
                </div>

                {/* New entry form */}
                {isAddingEntry && (
                  <div className="mb-4 p-4 rounded-lg bg-muted/50 border border-border">
                    <textarea
                      value={newEntryContent}
                      onChange={(e) => setNewEntryContent(e.target.value)}
                      placeholder="Enter new content..."
                      rows={4}
                      className={clsx(
                        'w-full px-3 py-2 rounded-md text-sm',
                        'bg-background border border-input',
                        'focus:outline-none focus:ring-2 focus:ring-ring',
                        'resize-none'
                      )}
                      autoFocus
                    />
                    <div className="flex justify-end gap-2 mt-3">
                      <button
                        onClick={() => {
                          setIsAddingEntry(false);
                          setNewEntryContent('');
                        }}
                        className="px-3 py-1.5 text-sm rounded-md hover:bg-accent"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleAddEntry}
                        disabled={!newEntryContent.trim()}
                        className={clsx(
                          'px-3 py-1.5 text-sm rounded-md',
                          'bg-primary text-primary-foreground hover:bg-primary/90',
                          'disabled:opacity-50 disabled:cursor-not-allowed'
                        )}
                      >
                        Add Entry
                      </button>
                    </div>
                  </div>
                )}

                {/* Entry list */}
                <div className="space-y-3">
                  {artifact.entries && artifact.entries.length > 0 ? (
                    artifact.entries.map((entry) => (
                      <EntryCard
                        key={entry.id}
                        entry={entry}
                        isEditing={editingEntryId === entry.id}
                        editContent={editingEntryId === entry.id ? editEntryContent : ''}
                        onEditStart={() => {
                          setEditingEntryId(entry.id);
                          setEditEntryContent(entry.content);
                        }}
                        onEditCancel={() => setEditingEntryId(null)}
                        onEditChange={setEditEntryContent}
                        onEditSave={async () => {
                          // Use PATCH on the entry via entries API (POST to update - we'll use the artifact update pattern)
                          try {
                            const response = await fetch(`/api/artifacts/${artifact.id}/entries/${entry.id}`, {
                              method: 'PATCH',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ content: editEntryContent.trim() }),
                            });
                            if (response.ok) {
                              setArtifact((prev) =>
                                prev ? {
                                  ...prev,
                                  entries: prev.entries.map((e) =>
                                    e.id === entry.id ? { ...e, content: editEntryContent.trim() } : e
                                  ),
                                } : null
                              );
                              setEditingEntryId(null);
                              addNotification({ type: 'success', title: 'Entry updated', message: 'Entry has been updated' });
                            } else {
                              addNotification({ type: 'error', title: 'Error', message: 'Failed to update entry' });
                            }
                          } catch {
                            addNotification({ type: 'error', title: 'Error', message: 'Failed to update entry' });
                          }
                        }}
                      />
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No entries yet
                    </p>
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function EntryCard({
  entry,
  isEditing,
  editContent,
  onEditStart,
  onEditCancel,
  onEditChange,
  onEditSave,
}: {
  entry: ArtifactEntry;
  isEditing?: boolean;
  editContent?: string;
  onEditStart?: () => void;
  onEditCancel?: () => void;
  onEditChange?: (val: string) => void;
  onEditSave?: () => void;
}) {
  const sourceLabels: Record<string, string> = {
    workflow_output: 'Workflow Output',
    manual: 'Manual Entry',
    ai_summary: 'AI Summary',
  };

  return (
    <div className="p-4 rounded-lg bg-muted/30 border border-border group/entry">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <FileText className="w-3 h-3" />
          <span>{sourceLabels[entry.source] || entry.source}</span>
          {entry.workflowName && (
            <>
              <span>•</span>
              <span>{entry.workflowName}</span>
            </>
          )}
          <span>•</span>
          <span>{formatDate(entry.createdAt)}</span>
        </div>
        {!isEditing && onEditStart && (
          <button
            onClick={onEditStart}
            className="opacity-0 group-hover/entry:opacity-100 p-1 rounded hover:bg-accent transition-opacity"
            title="Edit entry"
          >
            <Pencil className="w-3 h-3" />
          </button>
        )}
      </div>
      {isEditing ? (
        <div>
          <textarea
            value={editContent}
            onChange={(e) => onEditChange?.(e.target.value)}
            rows={4}
            className={clsx(
              'w-full px-3 py-2 rounded-md text-sm',
              'bg-background border border-input',
              'focus:outline-none focus:ring-2 focus:ring-ring',
              'resize-none'
            )}
            autoFocus
          />
          <div className="flex justify-end gap-2 mt-2">
            <button
              onClick={onEditCancel}
              className="px-3 py-1 text-xs rounded-md hover:bg-accent"
            >
              Cancel
            </button>
            <button
              onClick={onEditSave}
              className="px-3 py-1 text-xs rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
            >
              Save
            </button>
          </div>
        </div>
      ) : (
        <p className="text-sm whitespace-pre-wrap">{entry.content}</p>
      )}
    </div>
  );
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
