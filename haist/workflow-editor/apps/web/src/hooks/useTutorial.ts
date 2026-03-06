"use client";

import { useTutorialContext } from "@/components/tutorial/TutorialProvider";

export function useTutorial() {
  return useTutorialContext();
}

export type { TutorialStep, TutorialState } from "@/components/tutorial/TutorialProvider";
