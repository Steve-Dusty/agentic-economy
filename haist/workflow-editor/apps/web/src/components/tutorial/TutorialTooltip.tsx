"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useTutorialContext, TutorialStep } from "./TutorialProvider";
import { clsx } from "clsx";

interface TutorialTooltipProps {
  step: TutorialStep;
  targetRef: React.RefObject<HTMLElement | null>;
  title: string;
  message: string;
  position?: "top" | "bottom" | "left" | "right";
  showNext?: boolean;
  showSkip?: boolean;
  nextLabel?: string;
  nextDisabled?: boolean;
  disabledMessage?: string;
  onNext?: () => void;
  nextHref?: string;
}

export function TutorialTooltip({
  step,
  targetRef,
  title,
  message,
  position = "bottom",
  showNext = true,
  showSkip = true,
  nextLabel = "Next",
  nextDisabled = false,
  disabledMessage,
  onNext,
  nextHref,
}: TutorialTooltipProps) {
  const router = useRouter();
  const { currentStep, isActive, nextStep, skipTutorial, completeTutorial } =
    useTutorialContext();
  const [rect, setRect] = useState<DOMRect | null>(null);

  // Track target element position
  useEffect(() => {
    if (!isActive || currentStep !== step || !targetRef.current) {
      setRect(null);
      return;
    }

    const updateRect = () => {
      if (targetRef.current) {
        setRect(targetRef.current.getBoundingClientRect());
      }
    };

    updateRect();

    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, true);

    const resizeObserver = new ResizeObserver(updateRect);
    if (targetRef.current) {
      resizeObserver.observe(targetRef.current);
    }

    return () => {
      window.removeEventListener("resize", updateRect);
      window.removeEventListener("scroll", updateRect, true);
      resizeObserver.disconnect();
    };
  }, [isActive, currentStep, step, targetRef]);

  // Only show when active and on the correct step
  if (!isActive || currentStep !== step || !rect) {
    return null;
  }

  const totalSteps = 8;
  const isLastStep = step === 8;
  const tooltipWidth = 320; // w-80 = 20rem = 320px
  const tooltipGap = 12;

  const handleNext = () => {
    if (onNext) {
      onNext();
    } else if (isLastStep) {
      completeTutorial();
    } else {
      nextStep();
      if (nextHref) {
        router.push(nextHref);
      }
    }
  };

  // Calculate fixed position based on target rect and desired position
  let tooltipStyle: React.CSSProperties = {};
  let arrowClass = "";

  switch (position) {
    case "top":
      tooltipStyle = {
        bottom: window.innerHeight - rect.top + tooltipGap,
        left: rect.left + rect.width / 2 - tooltipWidth / 2,
      };
      arrowClass = "tutorial-arrow-down";
      break;
    case "bottom":
      tooltipStyle = {
        top: rect.bottom + tooltipGap,
        left: rect.left + rect.width / 2 - tooltipWidth / 2,
      };
      arrowClass = "tutorial-arrow-up";
      break;
    case "left":
      tooltipStyle = {
        top: rect.top + rect.height / 2,
        right: window.innerWidth - rect.left + tooltipGap,
        transform: "translateY(-50%)",
      };
      arrowClass = "tutorial-arrow-right";
      break;
    case "right":
      tooltipStyle = {
        top: rect.top + rect.height / 2,
        left: rect.right + tooltipGap,
        transform: "translateY(-50%)",
      };
      arrowClass = "tutorial-arrow-left";
      break;
  }

  // Ensure tooltip stays within viewport
  if (tooltipStyle.left !== undefined && typeof tooltipStyle.left === "number") {
    tooltipStyle.left = Math.max(16, Math.min(tooltipStyle.left, window.innerWidth - tooltipWidth - 16));
  }

  return (
    <div
      className="fixed z-[60] w-80 animate-tutorial-tooltip-in"
      style={tooltipStyle}
    >
      <div className="relative bg-card border border-border rounded-xl shadow-lg overflow-hidden">
        {/* Arrow */}
        <div className={clsx("absolute", arrowClass)} />

        {/* Content */}
        <div className="p-4">
          <h4 className="font-semibold text-foreground mb-1">{title}</h4>
          <p className="text-sm text-muted-foreground mb-4">{message}</p>

          {/* Disabled message */}
          {nextDisabled && disabledMessage && (
            <p className="text-xs text-warning mb-3 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-warning animate-pulse" />
              {disabledMessage}
            </p>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between">
            {/* Progress dots */}
            <div className="flex items-center gap-1.5">
              {Array.from({ length: totalSteps }, (_, i) => (
                <div
                  key={i}
                  className={clsx(
                    "w-2 h-2 rounded-full transition-colors",
                    i + 1 === step
                      ? "bg-primary"
                      : i + 1 < step
                      ? "bg-primary/40"
                      : "bg-border"
                  )}
                />
              ))}
            </div>

            {/* Buttons */}
            <div className="flex items-center gap-2">
              {showSkip && !isLastStep && (
                <button
                  onClick={skipTutorial}
                  className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Skip
                </button>
              )}
              {showNext && (
                <button
                  onClick={handleNext}
                  disabled={nextDisabled}
                  className={clsx(
                    "px-4 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1 transition-all",
                    nextDisabled
                      ? "bg-muted text-muted-foreground cursor-not-allowed"
                      : "bg-primary text-primary-foreground hover:bg-primary/90"
                  )}
                >
                  {isLastStep ? "Start Automating!" : nextLabel}
                  {!isLastStep && <ChevronRight className="w-4 h-4" />}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
