"use client";

import React, { useEffect, useState } from "react";
import { useTutorialContext } from "./TutorialProvider";

interface TutorialOverlayProps {
  targetRef: React.RefObject<HTMLElement | null>;
  step: number;
  padding?: number;
  borderRadius?: number;
}

export function TutorialOverlay({
  targetRef,
  step,
  padding = 8,
  borderRadius = 16,
}: TutorialOverlayProps) {
  const { currentStep, isActive } = useTutorialContext();
  const [rect, setRect] = useState<DOMRect | null>(null);

  // Update spotlight position when target changes
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

    // Update on resize/scroll
    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, true);

    // Use ResizeObserver for more accurate tracking
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

  if (!isActive || currentStep !== step || !rect) {
    return null;
  }

  // Calculate spotlight cutout position
  const spotlightLeft = rect.left - padding;
  const spotlightTop = rect.top - padding;
  const spotlightWidth = rect.width + padding * 2;
  const spotlightHeight = rect.height + padding * 2;
  const spotlightRight = spotlightLeft + spotlightWidth;
  const spotlightBottom = spotlightTop + spotlightHeight;

  // Use 4 rectangles around the spotlight to create the darkened overlay
  // This allows pointer-events to pass through the spotlight area
  return (
    <>
      {/* Top overlay - from top of screen to top of spotlight */}
      <div
        className="fixed left-0 right-0 top-0 bg-black/50 z-[50] animate-fade-in"
        style={{ height: Math.max(0, spotlightTop) }}
      />

      {/* Bottom overlay - from bottom of spotlight to bottom of screen */}
      <div
        className="fixed left-0 right-0 bottom-0 bg-black/50 z-[50] animate-fade-in"
        style={{ top: spotlightBottom }}
      />

      {/* Left overlay - left side of spotlight (between top and bottom overlays) */}
      <div
        className="fixed left-0 bg-black/50 z-[50] animate-fade-in"
        style={{
          top: spotlightTop,
          width: Math.max(0, spotlightLeft),
          height: spotlightHeight,
        }}
      />

      {/* Right overlay - right side of spotlight (between top and bottom overlays) */}
      <div
        className="fixed right-0 bg-black/50 z-[50] animate-fade-in"
        style={{
          top: spotlightTop,
          left: spotlightRight,
          height: spotlightHeight,
        }}
      />

      {/* Highlight border around spotlight - pointer-events-none so clicks go through */}
      <div
        className="fixed border-2 border-primary/50 animate-pulse-glow pointer-events-none z-[51]"
        style={{
          left: spotlightLeft,
          top: spotlightTop,
          width: spotlightWidth,
          height: spotlightHeight,
          borderRadius: borderRadius,
          boxShadow: "0 0 20px hsl(var(--primary) / 0.3)",
        }}
      />
    </>
  );
}
