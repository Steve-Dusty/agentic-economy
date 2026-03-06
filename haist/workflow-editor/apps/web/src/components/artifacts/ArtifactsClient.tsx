'use client';

import React, { useEffect, useState, useMemo, useRef } from 'react';
import { Plus, Grid, List, Search, Archive } from 'lucide-react';
import { clsx } from 'clsx';
import { useUIStore } from '@workflow-editor/state';
import { ArtifactCard } from './ArtifactCard';
import { ArtifactDetailModal } from './ArtifactDetailModal';
import { CreateArtifactModal } from './CreateArtifactModal';
import { AuthenticatedLayout } from '../layout';
import {
  TutorialProvider,
  TutorialTooltip,
  TutorialOverlay,
  CompletionModal,
  useTutorialContext,
} from '@/components/tutorial';
import type { Artifact } from '@/lib/artifacts';

type ViewMode = 'grid' | 'table';

export function ArtifactsClient() {
  return (
    <TutorialProvider>
      <ArtifactsContent />
    </TutorialProvider>
  );
}

function ArtifactsContent() {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());

  // Tutorial refs
  const contentRef = useRef<HTMLDivElement>(null);
  const tutorial = useTutorialContext();

  const addNotification = useUIStore((state) => state.addNotification);

  // Fetch artifacts
  const fetchArtifacts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/artifacts');
      if (!response.ok) {
        throw new Error('Failed to fetch artifacts');
      }
      const data = await response.json();
      setArtifacts(data.artifacts || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch artifacts');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchArtifacts();
  }, []);

  // Collect all unique tags
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    artifacts.forEach((a) => a.tags?.forEach((t) => tagSet.add(t)));
    return Array.from(tagSet).sort();
  }, [artifacts]);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => {
      const next = new Set(prev);
      if (next.has(tag)) next.delete(tag);
      else next.add(tag);
      return next;
    });
  };

  // Filter artifacts by search and tags
  const filteredArtifacts = useMemo(() => {
    let result = artifacts;
    if (searchQuery) {
      const lower = searchQuery.toLowerCase();
      result = result.filter(
        (a) =>
          a.title.toLowerCase().includes(lower) ||
          a.summary?.toLowerCase().includes(lower) ||
          a.tags?.some((t) => t.toLowerCase().includes(lower))
      );
    }
    if (selectedTags.size > 0) {
      result = result.filter((a) =>
        a.tags?.some((t) => selectedTags.has(t))
      );
    }
    return result;
  }, [artifacts, searchQuery, selectedTags]);

  const handleCreateSuccess = (newArtifact: Artifact) => {
    setArtifacts((prev) => [newArtifact, ...prev]);
    setIsCreateModalOpen(false);
    addNotification({
      type: 'success',
      title: 'Artifact created',
      message: `"${newArtifact.title}" has been created`,
    });
  };

  const handleDelete = async (id: string) => {
    try {
      const response = await fetch(`/api/artifacts/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Failed to delete artifact');
      }
      setArtifacts((prev) => prev.filter((a) => a.id !== id));
      setSelectedArtifactId(null);
      addNotification({
        type: 'success',
        title: 'Artifact deleted',
        message: 'The artifact has been deleted',
      });
    } catch {
      addNotification({
        type: 'error',
        title: 'Delete failed',
        message: 'Failed to delete artifact',
      });
    }
  };

  const handleUpdate = (updatedArtifact: Artifact) => {
    setArtifacts((prev) =>
      prev.map((a) => (a.id === updatedArtifact.id ? updatedArtifact : a))
    );
  };

  return (
    <AuthenticatedLayout title="Artifacts">
      <div className="p-6">
        {/* Toolbar */}
        <div
          ref={contentRef}
          className={clsx(
            'flex items-center gap-4 mb-6',
            tutorial.isActive && tutorial.currentStep === 7 && 'tutorial-pulse-highlight rounded-lg p-2 -m-2'
          )}
        >
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search artifacts..."
              className={clsx(
                'w-full pl-10 pr-4 py-2 rounded-lg',
                'bg-background border border-border',
                'focus:outline-none focus:ring-2 focus:ring-ring/20 focus:border-ring/30',
                'placeholder:text-muted-foreground/50 transition-colors'
              )}
            />
          </div>

          {/* View toggle */}
          <div className="flex items-center bg-muted/50 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              className={clsx(
                'p-2 rounded-md transition-colors',
                viewMode === 'grid'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
              title="Grid view"
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={clsx(
                'p-2 rounded-md transition-colors',
                viewMode === 'table'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
              title="Table view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          {/* Create Artifact Button */}
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg',
              'bg-primary text-primary-foreground hover:bg-primary/90',
              'transition-colors text-sm font-medium'
            )}
          >
            <Plus className="w-4 h-4" />
            Create Artifact
          </button>
        </div>

        {/* Tag filters */}
        {allTags.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap mb-4">
            <span className="text-xs text-muted-foreground font-medium">Filter:</span>
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={clsx(
                  'px-2.5 py-1 text-xs rounded-full border transition-colors',
                  selectedTags.has(tag)
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-transparent text-muted-foreground border-border hover:border-foreground/20 hover:text-foreground'
                )}
              >
                {tag}
              </button>
            ))}
            {selectedTags.size > 0 && (
              <button
                onClick={() => setSelectedTags(new Set())}
                className="text-xs text-muted-foreground hover:text-foreground underline"
              >
                Clear
              </button>
            )}
          </div>
        )}

        {/* Content */}
        {error && (
          <div className="mb-4 p-4 rounded-md bg-destructive/10 text-destructive border border-destructive/20">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        ) : filteredArtifacts.length === 0 ? (
          <EmptyState
            hasSearch={!!searchQuery}
            onCreateClick={() => setIsCreateModalOpen(true)}
          />
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredArtifacts.map((artifact) => (
              <ArtifactCard
                key={artifact.id}
                artifact={artifact}
                onClick={() => setSelectedArtifactId(artifact.id)}
                onDelete={() => handleDelete(artifact.id)}
              />
            ))}
          </div>
        ) : (
          <ArtifactsTable
            artifacts={filteredArtifacts}
            onSelect={(id) => setSelectedArtifactId(id)}
            onDelete={handleDelete}
          />
        )}
      </div>

      {/* Modals */}
      <CreateArtifactModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleCreateSuccess}
      />

      <ArtifactDetailModal
        artifactId={selectedArtifactId}
        onClose={() => setSelectedArtifactId(null)}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
      />

      {/* Tutorial Step 7: Artifacts intro */}
      <TutorialOverlay targetRef={contentRef} step={7} padding={12} />
      <TutorialTooltip
        step={7}
        targetRef={contentRef}
        title="Your Artifacts Library"
        message="View and manage outputs from your workflows here. Artifacts are created automatically from workflow runs or manually."
        position="bottom"
      />

      {/* Tutorial Completion Modal (step 6) */}
      <CompletionModal />
    </AuthenticatedLayout>
  );
}

function EmptyState({
  hasSearch,
  onCreateClick,
}: {
  hasSearch: boolean;
  onCreateClick: () => void;
}) {
  if (hasSearch) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
          <Search className="w-8 h-8 text-muted-foreground" />
        </div>
        <h3 className="font-medium mb-2">No artifacts found</h3>
        <p className="text-sm text-muted-foreground">
          Try adjusting your search query
        </p>
      </div>
    );
  }

  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
        <Archive className="w-8 h-8 text-muted-foreground" />
      </div>
      <h3 className="font-medium mb-2">No artifacts yet</h3>
      <p className="text-sm text-muted-foreground mb-4">
        Artifacts are created automatically from workflow outputs, or you can create them manually.
      </p>
      <button
        onClick={onCreateClick}
        className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
      >
        Create Artifact
      </button>
    </div>
  );
}

function ArtifactsTable({
  artifacts,
  onSelect,
  onDelete,
}: {
  artifacts: Artifact[];
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <table className="w-full">
        <thead className="bg-muted/30">
          <tr>
            <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">
              Title
            </th>
            <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">
              Summary
            </th>
            <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">
              Tags
            </th>
            <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">
              Updated
            </th>
            <th className="w-20"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {artifacts.map((artifact) => (
            <tr
              key={artifact.id}
              className="hover:bg-muted/50 cursor-pointer transition-colors"
              onClick={() => onSelect(artifact.id)}
            >
              <td className="px-4 py-3 font-medium">{artifact.title}</td>
              <td className="px-4 py-3 text-sm text-muted-foreground truncate max-w-xs">
                {artifact.summary || '-'}
              </td>
              <td className="px-4 py-3">
                <div className="flex gap-1 flex-wrap">
                  {artifact.tags?.slice(0, 2).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 text-xs rounded-full bg-primary/10 text-primary"
                    >
                      {tag}
                    </span>
                  ))}
                  {artifact.tags && artifact.tags.length > 2 && (
                    <span className="text-xs text-muted-foreground">
                      +{artifact.tags.length - 2}
                    </span>
                  )}
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-muted-foreground">
                {formatRelativeTime(artifact.updatedAt)}
              </td>
              <td className="px-4 py-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(artifact.id);
                  }}
                  className="p-1.5 rounded-md text-destructive hover:bg-destructive/10"
                >
                  <Archive className="w-4 h-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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
