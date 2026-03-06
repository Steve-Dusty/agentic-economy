"use client";

import React from "react";
import { X, Sparkles, Plug, Zap } from "lucide-react";
import { useTutorialContext } from "./TutorialProvider";

export function WelcomeModal() {
  const { showWelcome, hasCompleted, hasSkipped, startTutorial, skipTutorial } =
    useTutorialContext();

  // Don't show if already completed/skipped or welcome dismissed
  if (!showWelcome || hasCompleted || hasSkipped) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={skipTutorial}
      />

      {/* Modal */}
      <div className="relative bg-card border border-border rounded-2xl shadow-2xl w-full max-w-md mx-4 animate-scale-in overflow-hidden">
        {/* Close button */}
        <button
          onClick={skipTutorial}
          className="absolute top-4 right-4 p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors z-10"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header gradient */}
        <div className="h-2 bg-gradient-primary" />

        {/* Content */}
        <div className="p-8">
          {/* Logo and title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-4">
              <img
                src="/blockd-logo.png"
                alt="Blockd"
                className="w-10 h-10"
              />
            </div>
            <h2 className="text-2xl font-semibold text-foreground mb-2">
              Welcome to Blockd
            </h2>
            <p className="text-muted-foreground">
              Let&apos;s get you started with automation
            </p>
          </div>

          {/* Value props */}
          <div className="space-y-4 mb-8">
            <div className="flex items-start gap-4 p-3 rounded-xl bg-muted/50">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-medium text-foreground text-sm">
                  Create workflows with natural language
                </h3>
                <p className="text-muted-foreground text-sm">
                  Just describe what you want to automate
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4 p-3 rounded-xl bg-muted/50">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Plug className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-medium text-foreground text-sm">
                  Connect 30+ services
                </h3>
                <p className="text-muted-foreground text-sm">
                  Gmail, Slack, Notion, GitHub and more
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4 p-3 rounded-xl bg-muted/50">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Zap className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-medium text-foreground text-sm">
                  Automate repetitive tasks
                </h3>
                <p className="text-muted-foreground text-sm">
                  Save hours every week on routine work
                </p>
              </div>
            </div>
          </div>

          {/* CTAs */}
          <div className="flex flex-col gap-3">
            <button
              onClick={startTutorial}
              className="w-full py-3 px-4 rounded-xl bg-gradient-primary text-white font-medium transition-all hover:opacity-90 hover:shadow-lg hover:shadow-primary/25 active:scale-[0.98]"
            >
              Start Tutorial
            </button>
            <button
              onClick={skipTutorial}
              className="w-full py-3 px-4 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
