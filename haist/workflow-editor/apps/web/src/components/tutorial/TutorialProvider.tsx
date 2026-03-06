"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

export type TutorialStep = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export interface TutorialState {
  isActive: boolean;
  currentStep: TutorialStep;
  hasCompleted: boolean;
  hasSkipped: boolean;
  showWelcome: boolean;
  hasConnectedIntegration: boolean;
}

interface TutorialContextValue extends TutorialState {
  startTutorial: () => void;
  skipTutorial: () => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (step: TutorialStep) => void;
  completeTutorial: () => void;
  resetTutorial: () => void;
  setHasConnectedIntegration: (connected: boolean) => void;
  dismissWelcome: () => void;
}

const STORAGE_KEY = "blockd-tutorial-state";

const defaultState: TutorialState = {
  isActive: false,
  currentStep: 0,
  hasCompleted: false,
  hasSkipped: false,
  showWelcome: true,
  hasConnectedIntegration: false,
};

const TutorialContext = createContext<TutorialContextValue | null>(null);

export function TutorialProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<TutorialState>(defaultState);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load state from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as Partial<TutorialState>;
        setState((prev) => ({
          ...prev,
          ...parsed,
          // If user has completed or skipped, don't show welcome
          showWelcome: !parsed.hasCompleted && !parsed.hasSkipped,
        }));
      }
    } catch (e) {
      console.warn("Failed to load tutorial state:", e);
    }
    setIsLoaded(true);
  }, []);

  // Persist state to localStorage
  useEffect(() => {
    if (!isLoaded) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn("Failed to save tutorial state:", e);
    }
  }, [state, isLoaded]);

  const startTutorial = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isActive: true,
      currentStep: 1,
      showWelcome: false,
    }));
  }, []);

  const skipTutorial = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isActive: false,
      hasSkipped: true,
      showWelcome: false,
    }));
  }, []);

  const nextStep = useCallback(() => {
    setState((prev) => {
      // Step 1 requires integration connection
      if (prev.currentStep === 1 && !prev.hasConnectedIntegration) {
        return prev; // Don't advance
      }

      const nextStepNum = Math.min(prev.currentStep + 1, 8) as TutorialStep;
      return {
        ...prev,
        currentStep: nextStepNum,
      };
    });
  }, []);

  const prevStep = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentStep: Math.max(prev.currentStep - 1, 1) as TutorialStep,
    }));
  }, []);

  const goToStep = useCallback((step: TutorialStep) => {
    setState((prev) => ({
      ...prev,
      currentStep: step,
    }));
  }, []);

  const completeTutorial = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isActive: false,
      hasCompleted: true,
      showWelcome: false,
    }));
  }, []);

  const resetTutorial = useCallback(() => {
    setState(defaultState);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      console.warn("Failed to remove tutorial state:", e);
    }
  }, []);

  const setHasConnectedIntegration = useCallback((connected: boolean) => {
    setState((prev) => ({
      ...prev,
      hasConnectedIntegration: connected,
    }));
  }, []);

  const dismissWelcome = useCallback(() => {
    setState((prev) => ({
      ...prev,
      showWelcome: false,
    }));
  }, []);

  // Don't render children until we've loaded from localStorage to prevent flash
  if (!isLoaded) {
    return null;
  }

  return (
    <TutorialContext.Provider
      value={{
        ...state,
        startTutorial,
        skipTutorial,
        nextStep,
        prevStep,
        goToStep,
        completeTutorial,
        resetTutorial,
        setHasConnectedIntegration,
        dismissWelcome,
      }}
    >
      {children}
    </TutorialContext.Provider>
  );
}

export function useTutorialContext() {
  const context = useContext(TutorialContext);
  if (!context) {
    throw new Error("useTutorialContext must be used within TutorialProvider");
  }
  return context;
}
