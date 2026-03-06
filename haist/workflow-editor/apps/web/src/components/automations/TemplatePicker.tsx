'use client';

import React, { useState } from 'react';
import { X, Search, ArrowRight } from 'lucide-react';
import { clsx } from 'clsx';
import {
  RULE_TEMPLATES,
  TEMPLATE_CATEGORIES,
  type RuleTemplate,
  type TemplateCategory,
} from '@/lib/execution-rules/templates';
import type { ExecutionRuleInput } from '@/lib/execution-rules/types';

interface TemplatePickerProps {
  onSelect: (template: ExecutionRuleInput) => void;
  onClose: () => void;
}

export function TemplatePicker({ onSelect, onClose }: TemplatePickerProps) {
  const [selectedCategory, setSelectedCategory] = useState<TemplateCategory | 'all'>('all');
  const [search, setSearch] = useState('');

  const filtered = RULE_TEMPLATES.filter((t) => {
    if (selectedCategory !== 'all' && t.category !== selectedCategory) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        t.name.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card border rounded-lg shadow-lg w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h2 className="text-lg font-semibold">Start from Template</h2>
            <p className="text-sm text-muted-foreground">Pick a template and customize it</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-muted rounded-md transition-colors"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        {/* Search + Categories */}
        <div className="p-4 border-b space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search templates..."
              className="w-full pl-9 pr-3 py-2 border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setSelectedCategory('all')}
              className={clsx(
                'px-3 py-1 text-xs rounded-full transition-colors',
                selectedCategory === 'all'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground'
              )}
            >
              All
            </button>
            {(Object.entries(TEMPLATE_CATEGORIES) as [TemplateCategory, { label: string; icon: string }][]).map(
              ([key, { label, icon }]) => (
                <button
                  key={key}
                  onClick={() => setSelectedCategory(key)}
                  className={clsx(
                    'px-3 py-1 text-xs rounded-full transition-colors',
                    selectedCategory === key
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:text-foreground'
                  )}
                >
                  {icon} {label}
                </button>
              )
            )}
          </div>
        </div>

        {/* Template Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {filtered.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">No templates match your search.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {filtered.map((template) => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onSelect={() => onSelect(template.template)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TemplateCard({
  template,
  onSelect,
}: {
  template: RuleTemplate;
  onSelect: () => void;
}) {
  const category = TEMPLATE_CATEGORIES[template.category];

  return (
    <button
      onClick={onSelect}
      className={clsx(
        'text-left p-4 border rounded-lg bg-background',
        'hover:border-primary/50 hover:bg-muted/30 transition-all',
        'group'
      )}
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl">{template.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium text-sm truncate">{template.name}</h3>
            <ArrowRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2">
            {template.description}
          </p>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded-full text-muted-foreground">
              {category.icon} {category.label}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded-full text-muted-foreground">
              {template.template.activationMode}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded-full text-muted-foreground">
              {template.template.executionSteps.length} steps
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}
