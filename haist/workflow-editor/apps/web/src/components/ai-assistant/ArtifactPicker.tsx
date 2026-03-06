'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Layers, Check, X, Search, ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';

interface Artifact {
  id: string;
  title: string;
  summary: string | null;
}

interface ArtifactPickerProps {
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  maxSelections?: number;
  disabled?: boolean;
}

export function ArtifactPicker({
  selectedIds,
  onSelectionChange,
  maxSelections = 3,
  disabled = false,
}: ArtifactPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Fetch artifacts on open
  useEffect(() => {
    if (isOpen && artifacts.length === 0) {
      fetchArtifacts();
    }
  }, [isOpen]);

  const fetchArtifacts = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/artifacts');
      if (response.ok) {
        const data = await response.json();
        setArtifacts(data.artifacts || []);
      }
    } catch (error) {
      console.error('Failed to fetch artifacts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleArtifact = (id: string) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((i) => i !== id));
    } else if (selectedIds.length < maxSelections) {
      onSelectionChange([...selectedIds, id]);
    }
  };

  const removeArtifact = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectionChange(selectedIds.filter((i) => i !== id));
  };

  const filteredArtifacts = artifacts.filter(
    (a) =>
      a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (a.summary?.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const selectedArtifacts = artifacts.filter((a) => selectedIds.includes(a.id));

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={clsx(
          'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-colors',
          'border',
          disabled && 'opacity-50 cursor-not-allowed',
          selectedIds.length > 0
            ? 'bg-primary/10 text-primary border-primary/30 hover:bg-primary/20'
            : 'bg-muted/50 text-muted-foreground hover:bg-muted border-border/50 hover:border-border'
        )}
      >
        <Layers className="w-3.5 h-3.5" />
        {selectedIds.length > 0 ? (
          <span className="font-medium">
            {selectedIds.length} artifact{selectedIds.length > 1 ? 's' : ''}
          </span>
        ) : (
          <span>Context</span>
        )}
        <ChevronDown className={clsx('w-3 h-3 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {/* Selected artifacts pills (shown when items are selected) */}
      {selectedIds.length > 0 && !isOpen && (
        <div className="absolute left-0 top-full mt-1 flex flex-wrap gap-1 max-w-[280px]">
          {selectedArtifacts.map((artifact) => (
            <span
              key={artifact.id}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs"
            >
              <span className="truncate max-w-[120px]">{artifact.title}</span>
              <button
                onClick={(e) => removeArtifact(artifact.id, e)}
                className="p-0.5 hover:bg-primary/20 rounded-full"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden">
          {/* Header with search */}
          <div className="p-2 border-b border-border">
            <div className="flex items-center gap-2 px-2 py-1.5 bg-muted/50 rounded-lg">
              <Search className="w-3.5 h-3.5 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search artifacts..."
                className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground/60"
                autoFocus
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="p-0.5 hover:bg-muted rounded"
                >
                  <X className="w-3 h-3 text-muted-foreground" />
                </button>
              )}
            </div>
          </div>

          {/* Artifacts list */}
          <div className="max-h-56 overflow-y-auto p-1.5">
            {isLoading ? (
              <div className="text-center py-6 text-muted-foreground text-sm">
                Loading artifacts...
              </div>
            ) : filteredArtifacts.length === 0 ? (
              <div className="text-center py-6 text-muted-foreground text-sm">
                {searchQuery ? 'No artifacts found' : 'No artifacts yet'}
              </div>
            ) : (
              filteredArtifacts.map((artifact) => {
                const isSelected = selectedIds.includes(artifact.id);
                const isDisabled = !isSelected && selectedIds.length >= maxSelections;

                return (
                  <button
                    key={artifact.id}
                    onClick={() => !isDisabled && toggleArtifact(artifact.id)}
                    disabled={isDisabled}
                    className={clsx(
                      'w-full text-left p-2 rounded-lg mb-0.5 transition-colors',
                      isSelected
                        ? 'bg-primary/10 border border-primary/30'
                        : 'hover:bg-muted/70 border border-transparent',
                      isDisabled && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <div
                        className={clsx(
                          'w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center mt-0.5',
                          isSelected ? 'bg-primary border-primary' : 'border-border'
                        )}
                      >
                        {isSelected && <Check className="w-2.5 h-2.5 text-primary-foreground" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{artifact.title}</div>
                        {artifact.summary && (
                          <div className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
                            {artifact.summary}
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="p-2 border-t border-border flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {selectedIds.length}/{maxSelections} selected
            </span>
            {selectedIds.length > 0 && (
              <button
                onClick={() => onSelectionChange([])}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Clear all
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
