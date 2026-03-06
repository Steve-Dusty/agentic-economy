"use client";

import React from "react";
import { Check } from "lucide-react";
import { useTutorialContext } from "./TutorialProvider";

export function CompletionModal() {
  const { isActive, currentStep, completeTutorial } = useTutorialContext();

  if (!isActive || currentStep !== 8) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none">
      <div className="pointer-events-auto animate-scale-in">
        <div className="bg-card border border-border rounded-xl shadow-lg p-6 w-80">
          <div className="text-center mb-4">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-500/10 mb-3">
              <Check className="w-6 h-6 text-green-500" />
            </div>
            <h4 className="font-semibold text-foreground mb-1">
              You&apos;re All Set!
            </h4>
            <p className="text-sm text-muted-foreground">
              You&apos;ve explored the key features. Your connected services are ready to use in workflows.
            </p>
          </div>
          <button
            onClick={() => completeTutorial()}
            className="w-full py-2.5 px-4 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
          >
            Start Automating!
          </button>
        </div>
      </div>
    </div>
  );
}
