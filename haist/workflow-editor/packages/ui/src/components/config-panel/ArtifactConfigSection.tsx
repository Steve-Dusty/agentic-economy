'use client';

import React, { useState, useEffect } from 'react';
import { Archive, ChevronDown, ChevronUp, X } from 'lucide-react';
import { clsx } from 'clsx';
import type { ArtifactConfig } from '@workflow-editor/core';
import { DEFAULT_ARTIFACT_CONFIG } from '@workflow-editor/core';

interface Artifact {
  id: string;
  title: string;
  tags?: string[];
}

interface ArtifactConfigSectionProps {
  config: ArtifactConfig | undefined;
  onChange: (config: ArtifactConfig) => void;
}

/**
 * Artifact configuration section for AI agent nodes
 * Allows configuring automatic artifact injection
 */
export function ArtifactConfigSection({
  config,
  onChange,
}: ArtifactConfigSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [isLoadingArtifacts, setIsLoadingArtifacts] = useState(false);

  // Merge with defaults
  const currentConfig: ArtifactConfig = {
    ...DEFAULT_ARTIFACT_CONFIG,
    ...config,
  };

  // Fetch artifacts when expanded
  useEffect(() => {
    if (isExpanded && artifacts.length === 0) {
      fetchArtifacts();
    }
  }, [isExpanded, artifacts.length]);

  const fetchArtifacts = async () => {
    setIsLoadingArtifacts(true);
    try {
      const response = await fetch('/api/artifacts');
      if (response.ok) {
        const data = await response.json();
        setArtifacts(data.artifacts || []);
      }
    } catch (err) {
      console.error('Failed to fetch artifacts:', err);
    } finally {
      setIsLoadingArtifacts(false);
    }
  };

  const updateConfig = (updates: Partial<ArtifactConfig>) => {
    onChange({
      ...currentConfig,
      ...updates,
    });
  };

  const toggleIncludeArtifact = (artifactId: string) => {
    const current = currentConfig.includeArtifacts || [];
    const updated = current.includes(artifactId)
      ? current.filter((id) => id !== artifactId)
      : [...current, artifactId];
    updateConfig({ includeArtifacts: updated.length > 0 ? updated : undefined });
  };

  const toggleExcludeArtifact = (artifactId: string) => {
    const current = currentConfig.excludeArtifacts || [];
    const updated = current.includes(artifactId)
      ? current.filter((id) => id !== artifactId)
      : [...current, artifactId];
    updateConfig({ excludeArtifacts: updated.length > 0 ? updated : undefined });
  };

  const getArtifactById = (id: string): Artifact | undefined => {
    return artifacts.find((a) => a.id === id);
  };

  return (
    <div className="space-y-3 p-3 bg-muted/50 rounded-md border border-border">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full text-left"
      >
        <div className="flex items-center gap-2">
          <Archive className="w-4 h-4 text-muted-foreground" />
          <span className="text-xs font-medium">Artifact Context</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {/* Summary when collapsed */}
      {!isExpanded && (
        <p className="text-xs text-muted-foreground">
          {currentConfig.autoInject
            ? `Auto-inject up to ${currentConfig.maxArtifacts} relevant artifacts`
            : 'Artifact injection disabled'}
        </p>
      )}

      {/* Expanded content */}
      {isExpanded && (
        <div className="space-y-4 pt-2">
          {/* Auto-inject toggle */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-xs font-medium">Auto-inject Artifacts</label>
              <p className="text-xs text-muted-foreground">
                Automatically include relevant context
              </p>
            </div>
            <button
              onClick={() => updateConfig({ autoInject: !currentConfig.autoInject })}
              className={clsx(
                'relative w-10 h-5 rounded-full transition-colors',
                currentConfig.autoInject ? 'bg-primary' : 'bg-muted-foreground/30'
              )}
            >
              <span
                className={clsx(
                  'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform',
                  currentConfig.autoInject ? 'left-5' : 'left-0.5'
                )}
              />
            </button>
          </div>

          {/* Max artifacts */}
          {currentConfig.autoInject && (
            <div>
              <label className="text-xs font-medium">Max Artifacts</label>
              <input
                type="number"
                min="1"
                max="10"
                value={currentConfig.maxArtifacts}
                onChange={(e) =>
                  updateConfig({ maxArtifacts: Math.max(1, Math.min(10, Number(e.target.value))) })
                }
                className={clsx(
                  'w-full mt-1 px-3 py-2 text-sm rounded-md',
                  'bg-background border border-input',
                  'focus:outline-none focus:ring-2 focus:ring-ring'
                )}
              />
              <p className="text-xs text-muted-foreground mt-0.5">
                Maximum artifacts to inject (1-10)
              </p>
            </div>
          )}

          {/* Include artifacts */}
          <div>
            <label className="text-xs font-medium">Always Include</label>
            <p className="text-xs text-muted-foreground mb-2">
              These artifacts will always be included
            </p>

            {/* Selected includes */}
            {currentConfig.includeArtifacts && currentConfig.includeArtifacts.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {currentConfig.includeArtifacts.map((id) => {
                  const artifact = getArtifactById(id);
                  return (
                    <span
                      key={id}
                      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-primary/10 text-primary"
                    >
                      {artifact?.title || id.slice(0, 8)}
                      <button
                        onClick={() => toggleIncludeArtifact(id)}
                        className="hover:text-primary/70"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  );
                })}
              </div>
            )}

            {/* Artifact selector */}
            {isLoadingArtifacts ? (
              <div className="text-xs text-muted-foreground">Loading artifacts...</div>
            ) : artifacts.length === 0 ? (
              <div className="text-xs text-muted-foreground">No artifacts available</div>
            ) : (
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) {
                    toggleIncludeArtifact(e.target.value);
                  }
                }}
                className={clsx(
                  'w-full px-3 py-2 text-sm rounded-md',
                  'bg-background border border-input',
                  'focus:outline-none focus:ring-2 focus:ring-ring'
                )}
              >
                <option value="">Add artifact...</option>
                {artifacts
                  .filter((a) => !currentConfig.includeArtifacts?.includes(a.id))
                  .map((artifact) => (
                    <option key={artifact.id} value={artifact.id}>
                      {artifact.title}
                    </option>
                  ))}
              </select>
            )}
          </div>

          {/* Exclude artifacts */}
          <div>
            <label className="text-xs font-medium">Always Exclude</label>
            <p className="text-xs text-muted-foreground mb-2">
              These artifacts will never be included
            </p>

            {/* Selected excludes */}
            {currentConfig.excludeArtifacts && currentConfig.excludeArtifacts.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {currentConfig.excludeArtifacts.map((id) => {
                  const artifact = getArtifactById(id);
                  return (
                    <span
                      key={id}
                      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-destructive/10 text-destructive"
                    >
                      {artifact?.title || id.slice(0, 8)}
                      <button
                        onClick={() => toggleExcludeArtifact(id)}
                        className="hover:text-destructive/70"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  );
                })}
              </div>
            )}

            {/* Artifact selector */}
            {!isLoadingArtifacts && artifacts.length > 0 && (
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) {
                    toggleExcludeArtifact(e.target.value);
                  }
                }}
                className={clsx(
                  'w-full px-3 py-2 text-sm rounded-md',
                  'bg-background border border-input',
                  'focus:outline-none focus:ring-2 focus:ring-ring'
                )}
              >
                <option value="">Add artifact to exclude...</option>
                {artifacts
                  .filter((a) => !currentConfig.excludeArtifacts?.includes(a.id))
                  .map((artifact) => (
                    <option key={artifact.id} value={artifact.id}>
                      {artifact.title}
                    </option>
                  ))}
              </select>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
