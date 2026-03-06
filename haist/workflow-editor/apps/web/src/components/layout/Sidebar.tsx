"use client";

import React, { useRef, useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  Archive,
  Zap,
  Plus,
  ExternalLink,
  PanelLeft,
} from "lucide-react";
import { clsx } from "clsx";
import { DEV_USER } from "@/lib/dev-user";
// NotificationBell moved to AuthenticatedLayout header
import { SidebarConversations } from "./SidebarConversations";
import { useConversationStore } from "@/lib/ai-assistant/conversation-store";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  external?: boolean;
}

const navItems: NavItem[] = [
  {
    href: "/automations",
    label: "Automations",
    icon: Zap,
  },
  {
    href: "/chat",
    label: "Chats",
    icon: MessageSquare,
  },
  {
    href: "/artifacts",
    label: "Artifacts",
    icon: Archive,
  },
];

interface SidebarProps {
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function Sidebar({ isCollapsed = false, onToggleCollapse }: SidebarProps) {
  const pathname = usePathname();
  const clearActiveConversation = useConversationStore(
    (state) => state.clearActiveConversation
  );

  // Tutorial refs for nav items
  const automationsNavRef = useRef<HTMLDivElement>(null);
  const artifactsNavRef = useRef<HTMLDivElement>(null);

  // Tutorial context - safely handle when not in TutorialProvider
  const [tutorialContext, setTutorialContext] = useState<{
    isActive: boolean;
    currentStep: number;
    nextStep: () => void;
  } | null>(null);

  // Try to get tutorial context on mount
  useEffect(() => {
    // This is a workaround since Sidebar might be rendered outside TutorialProvider
    // We'll check if the tutorial state exists in localStorage
    try {
      const stored = localStorage.getItem("blockd-tutorial-state");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.isActive) {
          setTutorialContext({
            isActive: parsed.isActive,
            currentStep: parsed.currentStep,
            nextStep: () => {
              // Update localStorage and trigger re-render
              const updated = { ...parsed, currentStep: parsed.currentStep + 1 };
              localStorage.setItem("blockd-tutorial-state", JSON.stringify(updated));
              setTutorialContext(prev => prev ? { ...prev, currentStep: updated.currentStep } : null);
            },
          });
        }
      }
    } catch (e) {
      // Ignore errors
    }
  }, []);

  // Listen for storage changes (when tutorial advances on other pages)
  useEffect(() => {
    const handleStorage = () => {
      try {
        const stored = localStorage.getItem("blockd-tutorial-state");
        if (stored) {
          const parsed = JSON.parse(stored);
          setTutorialContext(prev => {
            if (!parsed.isActive) return null;
            return {
              isActive: parsed.isActive,
              currentStep: parsed.currentStep,
              nextStep: () => {
                const updated = { ...parsed, currentStep: parsed.currentStep + 1 };
                localStorage.setItem("blockd-tutorial-state", JSON.stringify(updated));
                setTutorialContext(p => p ? { ...p, currentStep: updated.currentStep } : null);
              },
            };
          });
        }
      } catch (e) {
        // Ignore errors
      }
    };

    window.addEventListener("storage", handleStorage);
    // Also poll for changes since storage event doesn't fire in same tab
    const interval = setInterval(handleStorage, 500);
    return () => {
      window.removeEventListener("storage", handleStorage);
      clearInterval(interval);
    };
  }, []);

  // Handle nav click for tutorial advancement
  const handleNavClick = (href: string) => {
    if (tutorialContext?.isActive) {
      // Step 4: User clicks Automations
      if (tutorialContext.currentStep === 4 && href === "/automations") {
        tutorialContext.nextStep();
      }
      // Step 6: User clicks Artifacts
      if (tutorialContext.currentStep === 6 && href === "/artifacts") {
        tutorialContext.nextStep();
      }
    }
  };

  return (
    <aside
      className={clsx(
        "h-screen bg-card border-r border-border flex flex-col shrink-0 transition-[width] duration-150 ease-out",
        isCollapsed ? "w-[3.05rem]" : "w-64"
      )}
    >
      {/* Header with Logo */}
      <div className="relative flex w-full items-center p-2 pt-2">
        <div
          className={clsx(
            "flex items-center gap-1.5 pl-2 h-8 overflow-hidden transition-opacity duration-150",
            isCollapsed ? "opacity-0 pointer-events-none" : "opacity-100"
          )}
        >
          <Link
            href="/automations"
            onClick={() => clearActiveConversation()}
            className="flex flex-row items-center gap-2"
            aria-label="Home"
          >
            <Image
              src="/blockd-logo.png"
              alt="blockd"
              width={28}
              height={28}
              className="h-7 w-7 flex-shrink-0"
            />
            <span className="text-sm font-semibold text-foreground">blockd</span>
          </Link>
        </div>
        <div className={clsx("absolute top-2 flex items-center gap-1", isCollapsed ? "left-1/2 -translate-x-1/2" : "right-2")}>
          <button
            onClick={onToggleCollapse}
            className={clsx(
              "inline-flex items-center justify-center",
              "h-8 w-8 rounded-md",
              "active:scale-95 transition-colors group",
              "hover:bg-muted"
            )}
            type="button"
            aria-label={isCollapsed ? "Open sidebar" : "Close sidebar"}
          >
            <div className="relative size-4 flex items-center justify-center">
              <PanelLeft className="w-5 h-5 transition text-muted-foreground group-hover:text-foreground" />
            </div>
          </button>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="flex flex-col gap-px pt-2">
        <div className="px-2">
          <Link
            href="/chat"
            onClick={() => clearActiveConversation()}
            className={clsx(
              "sidebar-nav-item group",
              "h-8 w-full rounded-lg py-1.5",
              isCollapsed ? "px-0 justify-center" : "px-4",
              "active:bg-muted active:scale-100"
            )}
          >
            <div
              className={clsx(
                "w-full flex flex-row items-center gap-3",
                isCollapsed ? "justify-center" : "-translate-x-2 justify-start"
              )}
            >
              <div className="flex items-center justify-center text-foreground">
                <div className="flex items-center justify-center rounded-full transition-all ease-in-out group-hover:-rotate-3 group-hover:scale-110 group-active:rotate-6 group-active:scale-[0.98]">
                  <div className="flex items-center justify-center rounded-full size-[1.4rem] -mx-[0.2rem] bg-foreground/10 group-hover:bg-foreground/15">
                    <Plus className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                  </div>
                </div>
              </div>
              <span
                className={clsx(
                  "truncate text-sm whitespace-nowrap flex-1 text-foreground transition-opacity duration-150",
                  isCollapsed ? "opacity-0 hidden" : "opacity-100"
                )}
              >
                New chat
              </span>
              <span
                className={clsx(
                  "flex items-center flex-shrink-0 -mr-2 opacity-0 group-hover:opacity-100 transition-opacity duration-75",
                  isCollapsed && "hidden"
                )}
              >
                <span className="text-muted-foreground text-xs px-0.5">
                  ⇧⌘O
                </span>
              </span>
            </div>
          </Link>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex flex-grow flex-col overflow-y-auto overflow-x-hidden relative transition-[border-color] border-t-[0.5px] border-transparent mt-2">
        <nav className="flex flex-col px-2 gap-px">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            const isChat = item.href === "/chat";
            const isAutomations = item.href === "/automations";
            const isArtifacts = item.href === "/artifacts";

            // Determine if this nav item should be highlighted for tutorial
            const isTutorialHighlight =
              tutorialContext?.isActive &&
              ((tutorialContext.currentStep === 4 && isAutomations) ||
                (tutorialContext.currentStep === 6 && isArtifacts));

            return (
              <div
                key={item.href}
                className="relative group"
                ref={isAutomations ? automationsNavRef : isArtifacts ? artifactsNavRef : undefined}
              >
                <Link
                  href={item.href}
                  onClick={() => {
                    if (isChat) clearActiveConversation();
                    handleNavClick(item.href);
                  }}
                  className={clsx(
                    "sidebar-nav-item",
                    "h-8 w-full rounded-lg py-1.5",
                    isCollapsed ? "px-0 justify-center" : "px-4",
                    "active:bg-muted active:scale-100",
                    isActive && "!bg-muted",
                    isTutorialHighlight && "ring-2 ring-primary ring-offset-2 ring-offset-background"
                  )}
                >
                  <div
                    className={clsx(
                      "w-full flex flex-row items-center gap-3",
                      isCollapsed ? "justify-center" : "-translate-x-2 justify-start"
                    )}
                  >
                    <div className="flex items-center justify-center text-foreground">
                      <div
                        className="group"
                        style={{
                          width: "16px",
                          height: "16px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <Icon
                          className={clsx(
                            "w-5 h-5",
                            isActive
                              ? "text-foreground"
                              : "text-muted-foreground group-hover:text-foreground"
                          )}
                        />
                      </div>
                    </div>
                    <span
                      className={clsx(
                        "truncate text-sm whitespace-nowrap flex-1 transition-opacity duration-150",
                        isActive
                          ? "text-foreground"
                          : "text-muted-foreground group-hover:text-foreground",
                        isCollapsed ? "opacity-0 hidden" : "opacity-100"
                      )}
                    >
                      {item.label}
                    </span>
                    {item.external && !isCollapsed && (
                      <ExternalLink className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-50 transition-opacity" />
                    )}
                  </div>
                </Link>
              </div>
            );
          })}
        </nav>

        {/* Conversations List - Hidden when collapsed */}
        {!isCollapsed && <SidebarConversations />}
      </div>

      {/* Footer - Dev User */}
      <div className="flex items-center gap-2 transition border-t border-border px-3 py-3">
        <div className="flex shrink-0 items-center justify-center rounded-full font-medium select-none h-8 w-8 text-xs bg-primary/10 text-primary">
          D
        </div>
        {!isCollapsed && (
          <span className="text-sm text-muted-foreground truncate">{DEV_USER.name}</span>
        )}
      </div>

      {/* Tutorial Step 4: Navigate to Automations */}
      {tutorialContext?.isActive && tutorialContext.currentStep === 4 && (
        <SidebarTutorialTooltip
          targetRef={automationsNavRef}
          title="Explore Automations"
          message="Click here to see how you can create automation rules for your connected services."
          currentStep={4}
          totalSteps={8}
        />
      )}

      {/* Tutorial Step 6: Navigate to Artifacts */}
      {tutorialContext?.isActive && tutorialContext.currentStep === 6 && (
        <SidebarTutorialTooltip
          targetRef={artifactsNavRef}
          title="View Your Artifacts"
          message="Click here to see your artifacts library where workflow outputs are stored."
          currentStep={6}
          totalSteps={8}
        />
      )}
    </aside>
  );
}

// Custom tutorial tooltip for sidebar (doesn't require TutorialProvider context)
function SidebarTutorialTooltip({
  targetRef,
  title,
  message,
  currentStep,
  totalSteps,
}: {
  targetRef: React.RefObject<HTMLDivElement | null>;
  title: string;
  message: string;
  currentStep: number;
  totalSteps: number;
}) {
  const [rect, setRect] = React.useState<DOMRect | null>(null);

  React.useEffect(() => {
    if (!targetRef.current) {
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
  }, [targetRef]);

  if (!rect) return null;

  const tooltipGap = 12;

  return (
    <>
      {/* Overlay - darken everything except target */}
      <div
        className="fixed left-0 right-0 top-0 bg-black/50 z-[50] animate-fade-in"
        style={{ height: Math.max(0, rect.top - 4) }}
      />
      <div
        className="fixed left-0 right-0 bottom-0 bg-black/50 z-[50] animate-fade-in"
        style={{ top: rect.bottom + 4 }}
      />
      <div
        className="fixed left-0 bg-black/50 z-[50] animate-fade-in"
        style={{
          top: rect.top - 4,
          width: Math.max(0, rect.left - 4),
          height: rect.height + 8,
        }}
      />
      <div
        className="fixed right-0 bg-black/50 z-[50] animate-fade-in"
        style={{
          top: rect.top - 4,
          left: rect.right + 4,
          height: rect.height + 8,
        }}
      />

      {/* Highlight border */}
      <div
        className="fixed border-2 border-primary/50 animate-pulse-glow pointer-events-none z-[51]"
        style={{
          left: rect.left - 4,
          top: rect.top - 4,
          width: rect.width + 8,
          height: rect.height + 8,
          borderRadius: 8,
          boxShadow: "0 0 20px hsl(var(--primary) / 0.3)",
        }}
      />

      {/* Tooltip */}
      <div
        className="fixed z-[60] w-72 animate-tutorial-tooltip-in"
        style={{
          top: rect.top + rect.height / 2,
          left: rect.right + tooltipGap,
          transform: "translateY(-50%)",
        }}
      >
        <div className="relative bg-card border border-border rounded-xl shadow-lg overflow-hidden">
          {/* Arrow pointing left */}
          <div className="tutorial-arrow-left" />

          <div className="p-4">
            <h4 className="font-semibold text-foreground mb-1">{title}</h4>
            <p className="text-sm text-muted-foreground mb-4">{message}</p>

            {/* Progress dots */}
            <div className="flex items-center gap-1.5">
              {Array.from({ length: totalSteps }, (_, i) => (
                <div
                  key={i}
                  className={clsx(
                    "w-2 h-2 rounded-full transition-colors",
                    i + 1 === currentStep
                      ? "bg-primary"
                      : i + 1 < currentStep
                        ? "bg-primary/40"
                        : "bg-border"
                  )}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
