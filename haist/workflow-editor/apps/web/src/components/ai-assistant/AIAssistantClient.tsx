"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  ArrowUp,
  Plus,
  X,
  Loader2,
  Check,
  ChevronDown,
  Pencil,
  GraduationCap,
  Code,
  Coffee,
  Lightbulb,
} from "lucide-react";
import { useComposioStore, useUIStore } from "@workflow-editor/state";
import { Notifications } from "@workflow-editor/ui";
import { clsx } from "clsx";
import { Sidebar } from "../layout/Sidebar";
import { ChatPanel } from "./ChatPanel";
import { WorkflowPreviewPanel } from "./WorkflowPreviewPanel";
import { ConnectionStatus } from "./ConnectionStatus";
import type {
  ChatMessage,
  AIAssistantContext,
  AIResponse,
  AssistantMode,
  ToolRouterMessage,
  ToolRouterChatResponse,
  ToolCallResult,
  InjectedArtifactInfo,
} from "@/lib/ai-assistant/types";
import type { WorkflowDocument } from "@workflow-editor/core";
import { useConversationStore } from "@/lib/ai-assistant/conversation-store";
import {
  TutorialProvider,
  WelcomeModal,
  TutorialTooltip,
  TutorialOverlay,
  CompletionModal,
  useTutorialContext,
} from "@/components/tutorial";

// Blockd-style categories
const categories = [
  { id: "write", label: "Write", icon: Pencil },
  { id: "learn", label: "Learn", icon: GraduationCap },
  { id: "code", label: "Code", icon: Code },
  { id: "life", label: "Life stuff", icon: Coffee },
  { id: "ideas", label: "Blockd's choice", icon: Lightbulb },
];

// Blockd prompt suffix
const BLOCKD_PROMPT_SUFFIX = `If you need more information from me, ask me 1-2 key questions right away. If you think I should upload any documents that would help you do a better job, let me know. You can use the tools you have access to - like Google Drive, web search, etc. - if they'll help you better accomplish this task. Do not use analysis tool. Please keep your responses friendly, brief and conversational. Please execute the task as soon as you can - an artifact would be great if it makes sense. If using an artifact, consider what kind of artifact (interactive, visual, checklist, etc.) might be most helpful for this specific task. Thanks for your help!`;

// Helper to create Blockd-style prompt
const createBlockdPrompt = (action: string) =>
  `Hi Blockd! Could you ${action}? ${BLOCKD_PROMPT_SUFFIX}`;

// Blockd-style prompts for each category
const categoryTemplates: Record<string, { title: string; prompt: string }[]> = {
  write: [
    {
      title: "Create a content strategy",
      prompt: createBlockdPrompt("create a content strategy"),
    },
    {
      title: "Edit my content",
      prompt: createBlockdPrompt("edit my content"),
    },
    {
      title: "Write compelling CTAs",
      prompt: createBlockdPrompt("write compelling CTAs"),
    },
    {
      title: "Draft an outline for my project",
      prompt: createBlockdPrompt("draft an outline for my project"),
    },
    {
      title: "Develop instructional content",
      prompt: createBlockdPrompt("develop instructional content"),
    },
  ],
  learn: [
    {
      title: "Explain a complex topic",
      prompt: createBlockdPrompt("explain a complex topic"),
    },
    {
      title: "Help me study for an exam",
      prompt: createBlockdPrompt("help me study for an exam"),
    },
    {
      title: "Create a learning plan",
      prompt: createBlockdPrompt("create a learning plan"),
    },
    {
      title: "Summarize a book or article",
      prompt: createBlockdPrompt("summarize a book or article"),
    },
    {
      title: "Research a topic in depth",
      prompt: createBlockdPrompt("research a topic in depth"),
    },
  ],
  code: [
    {
      title: "Write code for a feature",
      prompt: createBlockdPrompt("write code for a feature"),
    },
    {
      title: "Debug my code",
      prompt: createBlockdPrompt("debug my code"),
    },
    {
      title: "Explain how this code works",
      prompt: createBlockdPrompt("explain how this code works"),
    },
    {
      title: "Review my code for improvements",
      prompt: createBlockdPrompt("review my code for improvements"),
    },
    {
      title: "Help me architect a solution",
      prompt: createBlockdPrompt("help me architect a solution"),
    },
  ],
  life: [
    {
      title: "Help me make a decision",
      prompt: createBlockdPrompt("help me make a decision"),
    },
    {
      title: "Plan a trip or event",
      prompt: createBlockdPrompt("plan a trip or event"),
    },
    {
      title: "Give me career advice",
      prompt: createBlockdPrompt("give me career advice"),
    },
    {
      title: "Create a daily routine",
      prompt: createBlockdPrompt("create a daily routine"),
    },
    {
      title: "Help me set and track goals",
      prompt: createBlockdPrompt("help me set and track goals"),
    },
  ],
  ideas: [
    {
      title: "Surprise me with something interesting",
      prompt: createBlockdPrompt("surprise me with something interesting"),
    },
    {
      title: "Give me a creative challenge",
      prompt: createBlockdPrompt("give me a creative challenge"),
    },
    {
      title: "Propose a thought experiment",
      prompt: createBlockdPrompt("propose a thought experiment"),
    },
    {
      title: "Suggest something fun to learn",
      prompt: createBlockdPrompt("suggest something fun to learn"),
    },
    {
      title: "Recommend a new hobby or skill",
      prompt: createBlockdPrompt("recommend a new hobby or skill"),
    },
  ],
};

interface Integration {
  name: string;
  icon: string;
  composioToolkit?: string | null; // Composio toolkit ID, null = not yet supported
  authType?: "oauth" | "api_key" | "openclaw"; // Default is oauth
}

const integrations: Record<string, Integration[]> = {
  Google: [
    {
      name: "Gmail",
      icon: "/integrations/gmail.svg",
      composioToolkit: "GMAIL",
    },
    {
      name: "Google Calendar",
      icon: "/integrations/google-calendar.svg",
      composioToolkit: "GOOGLECALENDAR",
    },
    {
      name: "Google Drive",
      icon: "/integrations/google-drive.svg",
      composioToolkit: "GOOGLEDRIVE",
    },
    {
      name: "Google Sheets",
      icon: "/integrations/google-sheets.svg",
      composioToolkit: "GOOGLESHEETS",
    },
    {
      name: "Google Docs",
      icon: "/integrations/google-docs.svg",
      composioToolkit: "GOOGLEDOCS",
    },
    {
      name: "Google Tasks",
      icon: "/integrations/google-tasks.svg",
      composioToolkit: "GOOGLETASKS",
    },
    {
      name: "Google Meet",
      icon: "/integrations/google-meet.svg",
      composioToolkit: "GOOGLEMEET",
    },
    {
      name: "Google Maps",
      icon: "/integrations/google-maps.svg",
      composioToolkit: "GOOGLE_MAPS",
    },
    {
      name: "YouTube",
      icon: "/integrations/youtube.svg",
      composioToolkit: "YOUTUBE",
    },
  ],
  Microsoft: [
    {
      name: "Outlook",
      icon: "/integrations/outlook.svg",
      composioToolkit: "OUTLOOK",
    },
    {
      name: "OneDrive",
      icon: "/integrations/onedrive.svg",
      composioToolkit: "ONE_DRIVE",
    },
    {
      name: "Microsoft Teams",
      icon: "/integrations/microsoft-teams.svg",
      composioToolkit: "MICROSOFT_TEAMS",
    },
  ],
  Communication: [
    {
      name: "Slack",
      icon: "/integrations/slack.svg",
      composioToolkit: "SLACK",
    },
    {
      name: "Discord",
      icon: "/integrations/discord.svg",
      composioToolkit: "DISCORD",
    },
  ],
  Productivity: [
    {
      name: "Notion",
      icon: "/integrations/notion.svg",
      composioToolkit: "NOTION",
    },
    {
      name: "Linear",
      icon: "/integrations/linear.svg",
      composioToolkit: "LINEAR",
    },
    {
      name: "Jira",
      icon: "/integrations/jira.svg",
      composioToolkit: "JIRA",
      authType: "api_key",
    },
    {
      name: "Asana",
      icon: "/integrations/asana.svg",
      composioToolkit: "ASANA",
    },
    {
      name: "Calendly",
      icon: "/integrations/calendly.svg",
      composioToolkit: "CALENDLY",
    },
  ],
  Development: [
    {
      name: "GitHub",
      icon: "/integrations/github.svg",
      composioToolkit: "GITHUB",
    },
    {
      name: "Figma",
      icon: "/integrations/figma.svg",
      composioToolkit: "FIGMA",
    },
  ],
  Social: [
    { name: "X", icon: "/integrations/x.svg", composioToolkit: "TWITTER" },
    {
      name: "LinkedIn",
      icon: "/integrations/linkedin.svg",
      composioToolkit: "LINKEDIN",
    },
    {
      name: "Reddit",
      icon: "/integrations/reddit.svg",
      composioToolkit: "REDDIT",
    },
  ],
  Local: [
    {
      name: "OpenClaw",
      icon: "/integrations/openclaw.svg",
      composioToolkit: null,
      authType: "openclaw",
    },
  ],
  Other: [
    {
      name: "Canva",
      icon: "/integrations/canva.svg",
      composioToolkit: "CANVA",
    },
    {
      name: "Salesforce",
      icon: "/integrations/salesforce.svg",
      composioToolkit: "SALESFORCE",
    },
    {
      name: "Canvas",
      icon: "/integrations/canvas.svg",
      composioToolkit: "CANVAS",
      authType: "api_key",
    },
    {
      name: "Apollo",
      icon: "/integrations/apollo-io.svg",
      composioToolkit: "APOLLO",
      authType: "api_key",
    },
    {
      name: "Exa",
      icon: "/integrations/exa-color.png",
      composioToolkit: "EXA",
      authType: "api_key",
    },
    {
      name: "Firecrawl",
      icon: "/integrations/firecrawl.svg",
      composioToolkit: "FIRECRAWL",
      authType: "api_key",
    },
  ],
};

export function AIAssistantClient() {
  return (
    <TutorialProvider>
      <AIAssistantContent />
    </TutorialProvider>
  );
}

function AIAssistantContent() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentWorkflow, setCurrentWorkflow] =
    useState<WorkflowDocument | null>(null);
  const [context, setContext] = useState<AIAssistantContext | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [showChat, setShowChat] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [hoveredPrompt, setHoveredPrompt] = useState<string | null>(null);

  // Mode toggle state - separate histories for each mode
  const [mode, setMode] = useState<AssistantMode>("tool-router");
  const [toolRouterMessages, setToolRouterMessages] = useState<
    ToolRouterMessage[]
  >([]);

  // Artifact selection state for context injection
  const [selectedArtifactIds, setSelectedArtifactIds] = useState<string[]>([]);

  // Integrations dropdown state
  const [showIntegrations, setShowIntegrations] = useState(false);

  // Sidebar collapsed state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // OpenClaw connection state
  const [showOpenClawModal, setShowOpenClawModal] = useState(false);
  const [openClawUrl, setOpenClawUrl] = useState("http://127.0.0.1:18789");
  const [openClawToken, setOpenClawToken] = useState("ab2f2fc22392317fa32ef6ebc3af798583f45da2a14b0884");
  const [openClawConnecting, setOpenClawConnecting] = useState(false);
  const [openClawConnected, setOpenClawConnected] = useState(false);

  // Tutorial refs for target elements
  const integrationsSectionRef = useRef<HTMLDivElement>(null);
  const categoryPillsRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLDivElement>(null);

  // Tutorial context
  const tutorial = useTutorialContext();

  // Conversation store
  const {
    activeConversationId,
    setActiveConversationId,
    fetchConversations,
    createConversation,
    selectConversation,
    updateConversationMode,
    addMessage,
  } = useConversationStore();

  // Composio store for integration connections
  const {
    fetchConnectedAccounts,
    initiateAuth,
    isToolkitConnected,
    pendingAuth,
  } = useComposioStore();
  const { addNotification } = useUIStore();

  // Track if component has mounted (for hydration-safe rendering)
  const [hasMounted, setHasMounted] = useState(false);
  useEffect(() => {
    setHasMounted(true);
  }, []);

  // Fetch connected accounts on mount
  useEffect(() => {
    fetchConnectedAccounts();
  }, [fetchConnectedAccounts]);

  // Check OpenClaw connection status on mount
  useEffect(() => {
    async function checkOpenClaw() {
      try {
        const res = await fetch("/api/openclaw/config");
        if (res.ok) {
          const data = await res.json();
          setOpenClawConnected(data.connected === true);
        }
      } catch {
        // Silently fail — OpenClaw is optional
      }
    }
    checkOpenClaw();
  }, []);

  // Listen for OAuth popup completion
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === "composio-auth-complete") {
        const { success, app } = event.data;
        if (success) {
          addNotification({
            type: "success",
            title: "Connected",
            message: `${app} has been connected successfully.`,
          });
          fetchConnectedAccounts();
          // Mark tutorial as having connected integration
          tutorial.setHasConnectedIntegration(true);
        }
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [fetchConnectedAccounts, addNotification, tutorial]);

  // Auto-open integrations section when tutorial is on step 1
  useEffect(() => {
    if (tutorial.isActive && tutorial.currentStep === 1 && !showIntegrations) {
      setShowIntegrations(true);
    }
  }, [tutorial.isActive, tutorial.currentStep, showIntegrations]);

  // Check if any integration is already connected (for tutorial state)
  useEffect(() => {
    const hasAnyConnection = Object.values(integrations)
      .flat()
      .some(
        (int) => int.composioToolkit && isToolkitConnected(int.composioToolkit),
      );
    if (hasAnyConnection && !tutorial.hasConnectedIntegration) {
      tutorial.setHasConnectedIntegration(true);
    }
  }, [isToolkitConnected, tutorial]);

  // Fetch context on mount
  useEffect(() => {
    async function fetchContext() {
      try {
        const response = await fetch("/api/ai-assistant/context");
        if (!response.ok) {
          throw new Error("Failed to fetch context");
        }
        const data = await response.json();
        setContext(data);
      } catch (err) {
        console.error("Failed to fetch context:", err);
        setError("Failed to load AI assistant context");
      }
    }

    fetchContext();
  }, []);

  // Load conversations from store on mount
  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Check for inactive conversations and summarize them when user returns after 30+ min
  useEffect(() => {
    // Only run in browser (not during SSR)
    if (typeof window === "undefined") return;

    const INACTIVITY_THRESHOLD_MS = 5 * 60 * 1000; // 30 minutes
    const STORAGE_KEY = "ai-assistant-last-activity";

    async function checkAndSummarizeInactive() {
      try {
        const lastActivity = window.localStorage.getItem(STORAGE_KEY);
        const now = Date.now();

        if (lastActivity) {
          const elapsed = now - parseInt(lastActivity, 10);

          if (elapsed >= INACTIVITY_THRESHOLD_MS) {
            // User has been away for 30+ minutes - trigger summarization in background
            console.log(
              "[ai-assistant] User returned after 30+ min, checking for inactive conversations...",
            );

            fetch("/api/cron/summarize-inactive", {
              method: "GET",
            })
              .then((res) => {
                if (res.ok) {
                  res.json().then((data) => {
                    if (data.processed > 0) {
                      console.log(
                        `[ai-assistant] Summarized ${data.processed} inactive conversation(s)`,
                      );
                    }
                  });
                }
              })
              .catch((err) => {
                console.error(
                  "[ai-assistant] Failed to summarize inactive conversations:",
                  err,
                );
              });
          }
        }

        // Update last activity timestamp
        window.localStorage.setItem(STORAGE_KEY, now.toString());
      } catch (err) {
        // localStorage might not be available (private browsing, etc.)
        console.warn("[ai-assistant] Could not check activity timestamp:", err);
      }
    }

    checkAndSummarizeInactive();
  }, []);

  // Track if we're currently sending a message (to avoid state reset race condition)
  const isSendingRef = React.useRef(false);

  // Load active conversation when activeConversationId changes
  useEffect(() => {
    async function loadActiveConversation() {
      // Don't reset state while actively sending a message
      if (isSendingRef.current) {
        return;
      }

      if (activeConversationId) {
        const conv = await selectConversation(activeConversationId);
        if (conv) {
          setMessages(conv.messages || []);
          setToolRouterMessages(conv.toolRouterMessages || []);
          setMode(conv.mode);
          if (
            (conv.messages && conv.messages.length > 0) ||
            (conv.toolRouterMessages && conv.toolRouterMessages.length > 0)
          ) {
            setShowChat(true);
          }
        }
      } else {
        // Reset to landing page when no active conversation
        setMessages([]);
        setToolRouterMessages([]);
        setShowChat(false);
        setCurrentWorkflow(null);
        setSelectedArtifactIds([]);
      }
    }

    loadActiveConversation();
  }, [activeConversationId, selectConversation]);

  const handleModeChange = async (newMode: AssistantMode) => {
    setMode(newMode);
    // Update conversation mode if we have an active conversation
    if (activeConversationId) {
      await updateConversationMode(activeConversationId, newMode);
    }
  };

  // Handle sending a message
  const handleSendMessage = async (content: string, artifactIds?: string[]) => {
    if (isLoading || !content.trim()) return;

    // Mark that we're sending (prevents useEffect from resetting state)
    isSendingRef.current = true;

    // Show chat view
    setShowChat(true);

    // Create or get conversation if needed
    let convId = activeConversationId;
    if (!convId) {
      const newConv = await createConversation("tool-router");
      if (newConv) {
        convId = newConv.id;
      }
    }

    // Add user message
    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    // Build conversation history including this new message
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setIsLoading(true);
    setError(null);
    setInputValue("");

    // Save user message to database
    if (convId) {
      await addMessage(convId, userMessage, "tool-router");
    }

    try {
      const response = await fetch("/api/ai-assistant/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: content,
          conversationHistory: updatedMessages,
          manualArtifactIds: artifactIds || selectedArtifactIds,
          enableAutoArtifacts: true,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get AI response");
      }

      const data = await response.json();
      const aiResponse: AIResponse = data.response;

      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: `assistant_${Date.now()}`,
        role: "assistant",
        content: aiResponse.message,
        timestamp: new Date().toISOString(),
        workflow: aiResponse.workflow,
        requiredConnections: aiResponse.requiredConnections,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Save assistant message to database
      if (convId) {
        await addMessage(convId, assistantMessage, "tool-router");
      }

      // Update current workflow if one was generated
      if (aiResponse.workflow) {
        setCurrentWorkflow(aiResponse.workflow);
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      setError("Failed to get AI response. Please try again.");
    } finally {
      setIsLoading(false);
      isSendingRef.current = false;
      // Update activity timestamp
      if (typeof window !== "undefined") {
        try {
          window.localStorage.setItem(
            "ai-assistant-last-activity",
            Date.now().toString(),
          );
        } catch {}
      }
    }
  };

  // Handle sending a message in tool router mode
  const handleToolRouterMessage = async (
    content: string,
    artifactIds?: string[],
  ) => {
    if (isLoading || !content.trim()) return;

    // Mark that we're sending (prevents useEffect from resetting state)
    isSendingRef.current = true;

    // Show chat view
    setShowChat(true);

    // Create or get conversation if needed
    let convId = activeConversationId;
    if (!convId) {
      const newConv = await createConversation("tool-router");
      if (newConv) {
        convId = newConv.id;
      }
    }

    // Add user message
    const userMessage: ToolRouterMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...toolRouterMessages, userMessage];
    setToolRouterMessages(updatedMessages);
    setIsLoading(true);
    setError(null);
    setInputValue("");

    // Save user message to database
    if (convId) {
      await addMessage(convId, userMessage, "tool-router");
    }

    // Create assistant message immediately for progressive updates
    const assistantMessageId = `assistant_${Date.now()}`;
    const assistantMessage: ToolRouterMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      toolCalls: [],
    };

    setToolRouterMessages((prev) => [...prev, assistantMessage]);

    try {
      const response = await fetch("/api/ai-assistant/tool-router/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: content,
          conversationHistory: updatedMessages,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get AI response");
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body reader available");
      }

      const decoder = new TextDecoder();
      let buffer = "";
      const pendingToolCalls = new Map<string, Partial<ToolCallResult>>();
      let finalToolCalls: ToolCallResult[] = [];
      let finalInjectedArtifacts: InjectedArtifactInfo[] | undefined;
      let currentEventType = "";

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE events
          const lines = buffer.split('\n');
          buffer = lines.pop() || ""; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEventType = line.slice(7).trim();
              continue;
            }

            if (line.startsWith('data: ')) {
              try {
                const eventData = JSON.parse(line.slice(6));
                const eventType = currentEventType;

                switch (eventType) {
                  case 'text':
                    // Append text chunk progressively
                    if (eventData.chunk) {
                      setToolRouterMessages((prev) => prev.map((msg) =>
                        msg.id === assistantMessageId
                          ? { ...msg, content: msg.content + eventData.chunk }
                          : msg
                      ));
                    }
                    break;

                  case 'tool_call':
                    // Add tool call with pending state
                    const toolCall: ToolCallResult = {
                      id: eventData.id,
                      toolName: eventData.toolName,
                      toolkit: eventData.toolkit,
                      success: false,
                      timestamp: new Date().toISOString(),
                    };
                    pendingToolCalls.set(eventData.id, toolCall);

                    setToolRouterMessages((prev) => prev.map((msg) =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            toolCalls: [...(msg.toolCalls || []), toolCall]
                          }
                        : msg
                    ));
                    break;

                  case 'tool_result':
                    // Update tool call with result
                    if (pendingToolCalls.has(eventData.id)) {
                      const updatedToolCall = {
                        ...pendingToolCalls.get(eventData.id)!,
                        success: eventData.success,
                        result: eventData.result,
                        error: eventData.error,
                      } as ToolCallResult;

                      setToolRouterMessages((prev) => prev.map((msg) =>
                        msg.id === assistantMessageId
                          ? {
                              ...msg,
                              toolCalls: msg.toolCalls?.map((tc) =>
                                tc.id === eventData.id ? updatedToolCall : tc
                              ) || []
                            }
                          : msg
                      ));
                    }
                    break;

                  case 'done':
                    // Final summary
                    finalToolCalls = eventData.toolCalls || [];
                    finalInjectedArtifacts = eventData.injectedArtifacts;
                    break;

                  case 'error':
                    throw new Error(eventData.message || 'Unknown streaming error');
                }
              } catch (parseError) {
                console.error('Error parsing SSE event:', parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      // Finalize the assistant message with any remaining data
      setToolRouterMessages((prev) => prev.map((msg) =>
        msg.id === assistantMessageId
          ? {
              ...msg,
              toolCalls: finalToolCalls.length > 0 ? finalToolCalls : msg.toolCalls,
              injectedArtifacts: finalInjectedArtifacts,
            }
          : msg
      ));

      // Save final assistant message to database
      if (convId) {
        // Read final content from DOM-consistent state via a promise
        const finalContent = await new Promise<string>((resolve) => {
          setToolRouterMessages((prev) => {
            const currentMsg = prev.find(m => m.id === assistantMessageId);
            resolve(currentMsg?.content || '');
            return prev;
          });
        });

        const finalMessage: ToolRouterMessage = {
          ...assistantMessage,
          content: finalContent,
          toolCalls: finalToolCalls.length > 0 ? finalToolCalls : undefined,
          injectedArtifacts: finalInjectedArtifacts,
        };

        await addMessage(convId, finalMessage, "tool-router");
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      setError("Failed to get AI response. Please try again.");

      // Remove the empty assistant message on error
      setToolRouterMessages((prev) => prev.filter(msg => msg.id !== assistantMessageId));
    } finally {
      setIsLoading(false);
      isSendingRef.current = false;
      // Update activity timestamp
      if (typeof window !== "undefined") {
        try {
          window.localStorage.setItem(
            "ai-assistant-last-activity",
            Date.now().toString(),
          );
        } catch {}
      }
    }
  };

  // Handle rule invocation via @mention
  const handleRuleInvoke = async (
    ruleId: string,
    ruleName: string,
    context: string,
  ) => {
    if (isLoading) return;

    // Mark that we're sending (prevents useEffect from resetting state)
    isSendingRef.current = true;

    // Show chat view
    setShowChat(true);

    // Create or get conversation if needed
    let convId = activeConversationId;
    if (!convId) {
      const newConv = await createConversation("tool-router");
      if (newConv) {
        convId = newConv.id;
      }
    }

    // Add user message showing the rule invocation
    const userMessage: ToolRouterMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content: `@[Rule: ${ruleName}] ${context}`,
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...toolRouterMessages, userMessage];
    setToolRouterMessages(updatedMessages);
    setIsLoading(true);
    setError(null);

    // Save user message to database
    if (convId) {
      await addMessage(convId, userMessage, "tool-router");
    }

    try {
      // Build conversation history for the rule executor
      const conversationHistory = updatedMessages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role, content: m.content }));

      // Invoke the rule via the API
      const response = await fetch("/api/automations/invoke", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ruleId,
          context,
          conversationHistory,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to invoke rule");
      }

      const data = await response.json();
      const result = data.result;

      // Add assistant message with the result
      const assistantMessage: ToolRouterMessage = {
        id: `assistant_${Date.now()}`,
        role: "assistant",
        content: result.success
          ? `Rule "${ruleName}" executed successfully.\n\n${result.output || ""}`
          : `Rule "${ruleName}" failed: ${result.error || "Unknown error"}`,
        timestamp: new Date().toISOString(),
      };

      setToolRouterMessages((prev) => [...prev, assistantMessage]);

      // Save assistant message to database
      if (convId) {
        await addMessage(convId, assistantMessage, "tool-router");
      }
    } catch (err) {
      console.error("Failed to invoke rule:", err);

      // Add error message
      const errorMessage: ToolRouterMessage = {
        id: `assistant_${Date.now()}`,
        role: "assistant",
        content: `Failed to invoke rule "${ruleName}": ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
      };

      setToolRouterMessages((prev) => [...prev, errorMessage]);

      if (convId) {
        await addMessage(convId, errorMessage, "tool-router");
      }

      setError("Failed to invoke rule. Please try again.");
    } finally {
      setIsLoading(false);
      isSendingRef.current = false;
      // Update activity timestamp
      if (typeof window !== "undefined") {
        try {
          window.localStorage.setItem(
            "ai-assistant-last-activity",
            Date.now().toString(),
          );
        } catch {}
      }
    }
  };

  // Handle saving workflow
  const handleSaveWorkflow = async () => {
    if (!currentWorkflow || isSaving) return;

    setIsSaving(true);
    setError(null);

    try {
      const response = await fetch("/api/ai-assistant/save-workflow", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          workflow: currentWorkflow,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save workflow");
      }

      const data = await response.json();

      if (data.success && data.workflowId) {
        window.location.href = `/editor/${data.workflowId}`;
      } else {
        throw new Error(data.error || "Failed to save workflow");
      }
    } catch (err) {
      console.error("Failed to save workflow:", err);
      setError("Failed to save workflow. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  // Handle selecting a workflow from messages
  const handleSelectWorkflow = (workflow: WorkflowDocument) => {
    setCurrentWorkflow(workflow);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      // Check for rule mention in tool-router mode
      if (mode === "tool-router") {
        // Import parseRuleMention dynamically to check for rule mentions
        const { parseRuleMention } =
          await import("@/lib/ai-assistant/hooks/useRuleMention");
        const ruleMention = parseRuleMention(inputValue.trim());

        if (ruleMention.hasRuleMention && ruleMention.ruleName) {
          // Fetch the rule by name and invoke it
          try {
            const response = await fetch("/api/automations/manual");
            if (response.ok) {
              const data = await response.json();
              const rule = data.rules?.find(
                (r: { id: string; name: string }) =>
                  r.name === ruleMention.ruleName,
              );
              if (rule) {
                handleRuleInvoke(rule.id, rule.name, ruleMention.context || "");
                setInputValue("");
                return;
              }
            }
          } catch (error) {
            console.error("Failed to invoke rule from landing page:", error);
          }
        }
        handleToolRouterMessage(inputValue);
      } else {
        handleSendMessage(inputValue);
      }
    }
  };

  const handleCategoryClick = (categoryId: string) => {
    setSelectedCategory(selectedCategory === categoryId ? null : categoryId);
    // Auto-advance tutorial when user clicks a category on step 2
    if (tutorial.isActive && tutorial.currentStep === 2) {
      tutorial.nextStep();
    }
  };

  const handleTemplateClick = (prompt: string) => {
    setInputValue(prompt);
    setSelectedCategory(null);
  };

  // Handle OpenClaw connection
  const handleOpenClawConnect = async () => {
    if (!openClawUrl.trim() || !openClawToken.trim()) return;

    setOpenClawConnecting(true);
    try {
      const res = await fetch("/api/openclaw/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: openClawUrl.trim(), token: openClawToken.trim() }),
      });

      const data = await res.json();

      if (res.ok && data.connected) {
        setOpenClawConnected(true);
        setShowOpenClawModal(false);
        addNotification({
          type: "success",
          title: "Connected",
          message: "OpenClaw gateway is connected.",
        });
      } else {
        addNotification({
          type: "error",
          title: "Connection Failed",
          message: data.error || "Could not connect to OpenClaw gateway.",
        });
      }
    } catch (error) {
      addNotification({
        type: "error",
        title: "Connection Failed",
        message: error instanceof Error ? error.message : "Failed to connect to OpenClaw.",
      });
    } finally {
      setOpenClawConnecting(false);
    }
  };

  // Handle clicking on an integration button
  const handleIntegrationClick = async (integration: Integration) => {
    // Handle OpenClaw integration
    if (integration.authType === "openclaw") {
      if (openClawConnected) {
        addNotification({
          type: "info",
          title: "Already Connected",
          message: "OpenClaw is already connected.",
        });
        return;
      }
      setShowOpenClawModal(true);
      return;
    }

    if (!integration.composioToolkit) {
      addNotification({
        type: "info",
        title: "Coming Soon",
        message: `${integration.name} integration is coming soon!`,
      });
      return;
    }

    if (isToolkitConnected(integration.composioToolkit)) {
      addNotification({
        type: "info",
        title: "Already Connected",
        message: `${integration.name} is already connected.`,
      });
      return;
    }

    try {
      const redirectUrl = await initiateAuth(integration.composioToolkit);
      if (redirectUrl) {
        const popup = window.open(
          redirectUrl,
          "composio-auth",
          "width=600,height=700,scrollbars=yes",
        );
        const pollTimer = setInterval(() => {
          if (popup?.closed) {
            clearInterval(pollTimer);
            fetchConnectedAccounts();
          }
        }, 1000);
        setTimeout(() => clearInterval(pollTimer), 5 * 60 * 1000);
      }
    } catch (error) {
      addNotification({
        type: "error",
        title: "Connection Failed",
        message:
          error instanceof Error
            ? error.message
            : `Failed to connect ${integration.name}`,
      });
    }
  };

  // Show chat view if there are messages (in either mode)
  const hasMessages =
    mode === "tool-router"
      ? toolRouterMessages.length > 0
      : messages.length > 0;

  if (showChat && hasMessages) {
    return (
      <div className="flex h-screen bg-background overflow-hidden">
        <Sidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div className="flex-1 flex flex-col min-w-0">
          {/* Error Banner */}
          {error && (
            <div className="bg-destructive/10 border-b border-destructive/20 px-4 py-3 animate-slide-in-from-bottom">
              <div className="text-sm text-destructive">{error}</div>
            </div>
          )}

          {/* Main Content */}
          <div className="flex-1 flex overflow-hidden">
            {/* Chat Panel */}
            <div className="flex-1 flex flex-col min-w-0">
              <ChatPanel
                messages={messages}
                toolRouterMessages={toolRouterMessages}
                mode={mode}
                onModeChange={handleModeChange}
                onSendMessage={
                  mode === "tool-router"
                    ? handleToolRouterMessage
                    : handleSendMessage
                }
                onSelectWorkflow={handleSelectWorkflow}
                isLoading={isLoading}
                context={context}
                selectedArtifactIds={selectedArtifactIds}
                onArtifactSelectionChange={setSelectedArtifactIds}
                onRuleInvoke={handleRuleInvoke}
              />
            </div>

            {/* Right sidebar removed */}
          </div>
        </div>
      </div>
    );
  }

  // Get greeting based on day
  const getDayOfWeek = () => {
    const days = [
      "Sunday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
    ];
    return days[new Date().getDay()];
  };

  // Landing page view - Claude style
  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div className="flex-1 flex flex-col min-w-0 text-foreground relative overflow-hidden">
        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto thin-scrollbar">
          <main className="mx-auto w-full max-w-2xl px-4 md:px-8 pt-[15vh] md:pt-[20vh] flex flex-col items-center gap-8">
            {/* Greeting */}
            <div className="text-center animate-fade-in">
              <h1 className="claude-greeting select-none">
                Happy {getDayOfWeek()}
              </h1>
            </div>

            {/* Blockd-style input */}
            <div className="w-full max-w-2xl animate-fade-in-up delay-100 relative">
              <form onSubmit={handleSubmit}>
                <div
                  ref={chatInputRef}
                  className={clsx(
                    "claude-input-container",
                    tutorial.isActive &&
                      tutorial.currentStep === 3 &&
                      "tutorial-pulse-highlight",
                  )}>
                  <div className="flex flex-col m-3.5 gap-3">
                    <div className="relative">
                      <div className="w-full overflow-y-auto break-words max-h-96 min-h-[3rem] pl-1.5 pt-1.5">
                        {/* Preview overlay for hovered prompt */}
                        {hoveredPrompt && !inputValue && (
                          <div className="absolute inset-0 pl-1.5 pt-1.5 pointer-events-none overflow-hidden">
                            <p className="text-base text-muted-foreground/60 line-clamp-2">
                              {hoveredPrompt}
                            </p>
                          </div>
                        )}
                        <textarea
                          value={inputValue}
                          onChange={(e) => setInputValue(e.target.value)}
                          placeholder={
                            hoveredPrompt ? "" : "How can I help you today?"
                          }
                          className="w-full bg-transparent text-foreground text-base placeholder-muted-foreground resize-none focus:outline-none min-h-[48px] max-h-[200px] relative z-10"
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                              e.preventDefault();
                              handleSubmit(e);
                            }
                          }}
                          rows={1}
                          style={
                            { fieldSizing: "content" } as React.CSSProperties
                          }
                        />
                      </div>
                    </div>
                    <div className="flex gap-2 w-full items-center">
                      <div className="relative flex-1 flex items-center shrink min-w-0 gap-1">
                        {/* Plus button like Blockd */}
                        <button
                          type="button"
                          className="claude-ghost-btn"
                          aria-label="Add attachment">
                          <Plus className="w-5 h-5 text-muted-foreground" />
                        </button>
                      </div>
                      <button
                        type="submit"
                        disabled={!inputValue.trim() || isLoading}
                        className="claude-send-btn"
                        aria-label="Send message">
                        {isLoading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </form>

              {/* Blockd-style category pills */}
              <div
                ref={categoryPillsRef}
                className="mt-6 flex flex-wrap gap-2 justify-center relative">
                {categories.map((category) => {
                  const Icon = category.icon;
                  const isSelected = selectedCategory === category.id;
                  return (
                    <button
                      key={category.id}
                      type="button"
                      onClick={() => handleCategoryClick(category.id)}
                      className={clsx(
                        "claude-category-pill",
                        isSelected && "active",
                      )}>
                      <Icon className="w-4 h-4 text-muted-foreground" />
                      <span>{category.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Template suggestions */}
              {selectedCategory && categoryTemplates[selectedCategory] && (
                <div className="mt-6 p-5 bg-card rounded-xl border border-border animate-scale-in">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-medium text-foreground">
                      {categories.find((c) => c.id === selectedCategory)?.label}{" "}
                      Templates
                    </h3>
                    <button
                      onClick={() => setSelectedCategory(null)}
                      className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="space-y-0.5">
                    {categoryTemplates[selectedCategory].map(
                      (template, index) => (
                        <button
                          key={index}
                          onClick={() => handleTemplateClick(template.prompt)}
                          onMouseEnter={() => setHoveredPrompt(template.prompt)}
                          onMouseLeave={() => setHoveredPrompt(null)}
                          className="w-full text-left py-2.5 px-3 rounded-lg hover:bg-foreground/5 border-l-2 border-transparent hover:border-primary/50 transition-all duration-150 group flex items-center justify-between">
                          <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                            {template.title}
                          </span>
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="14"
                            height="14"
                            fill="currentColor"
                            viewBox="0 0 256 256"
                            className="text-muted-foreground/50 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                            <path d="M181.66,133.66l-80,80a8,8,0,0,1-11.32-11.32L164.69,128,90.34,53.66a8,8,0,0,1,11.32-11.32l80,80A8,8,0,0,1,181.66,133.66Z" />
                          </svg>
                        </button>
                      ),
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Integrations section - more subtle like Blockd */}
            <div
              ref={integrationsSectionRef}
              className="w-full max-w-2xl mt-8 animate-fade-in-up delay-300 relative">
              <button
                onClick={() => setShowIntegrations(!showIntegrations)}
                className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg hover:bg-muted/50 transition-all duration-200 group">
                <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                  {showIntegrations ? "Hide" : "Show"} Supported Integrations
                </span>
                <ChevronDown
                  className={clsx(
                    "w-4 h-4 text-muted-foreground transition-transform duration-300 group-hover:text-foreground",
                    showIntegrations && "rotate-180",
                  )}
                />
              </button>

              {/* Animated collapsible container */}
              <div
                className={clsx(
                  "grid transition-all duration-300 ease-in-out",
                  showIntegrations
                    ? "grid-rows-[1fr] opacity-100"
                    : "grid-rows-[0fr] opacity-0",
                )}>
                <div className="overflow-hidden">
                  <div className="pt-6 space-y-4">
                    {Object.entries(integrations).map(([category, items]) => (
                      <div
                        key={category}
                        className="flex flex-col sm:flex-row items-center gap-4">
                        <p className="text-xs font-medium text-muted-foreground whitespace-nowrap w-32 flex-shrink-0 text-center sm:text-right">
                          {category}
                        </p>
                        <div className="flex flex-wrap gap-2 items-center justify-center sm:justify-start">
                          {items.map((integration) => (
                            <IntegrationButton
                              key={integration.name}
                              integration={integration}
                              isConnected={
                                hasMounted && integration.authType === "openclaw"
                                  ? openClawConnected
                                  : hasMounted && integration.composioToolkit
                                    ? isToolkitConnected(
                                        integration.composioToolkit,
                                      )
                                    : false
                              }
                              isConnecting={
                                hasMounted && integration.authType === "openclaw"
                                  ? openClawConnecting
                                  : hasMounted &&
                                    pendingAuth !== null &&
                                    pendingAuth === integration.composioToolkit
                              }
                              onClick={() =>
                                handleIntegrationClick(integration)
                              }
                            />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>

      {/* Tutorial Overlays and Tooltips - rendered at root level for proper z-index */}
      <TutorialOverlay
        targetRef={integrationsSectionRef}
        step={1}
        padding={12}
      />
      <TutorialTooltip
        step={1}
        targetRef={integrationsSectionRef}
        title="Connect Your Services"
        message="First, connect the services you use. Click to authenticate Gmail, Slack, or any of 30+ services."
        position="top"
        nextDisabled={!tutorial.hasConnectedIntegration}
        disabledMessage="Connect at least one service to continue"
      />

      <TutorialOverlay targetRef={categoryPillsRef} step={2} padding={8} />
      <TutorialTooltip
        step={2}
        targetRef={categoryPillsRef}
        title="Explore Templates"
        message="Pick a category to see workflow templates you can use"
        position="bottom"
        showNext={false}
      />

      <TutorialOverlay targetRef={chatInputRef} step={3} padding={8} />
      <TutorialTooltip
        step={3}
        targetRef={chatInputRef}
        title="Describe Your Automation"
        message="Describe what you want to automate, or continue to see more features!"
        position="bottom"
      />

      {/* Tutorial Completion Modal (step 6) */}
      <CompletionModal />

      {/* Welcome Modal */}
      <WelcomeModal />

      {/* OpenClaw Connection Modal */}
      {showOpenClawModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-fade-in">
          <div className="bg-card border border-border rounded-xl shadow-xl w-full max-w-md mx-4 p-6 animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <img src="/integrations/openclaw.svg" alt="OpenClaw" className="w-5 h-5" />
                <h3 className="text-base font-medium text-foreground">Connect OpenClaw</h3>
              </div>
              <button
                onClick={() => setShowOpenClawModal(false)}
                className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-sm text-muted-foreground mb-5">
              Connect your local OpenClaw gateway to give the AI access to your machine — files, shell commands, and more.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Gateway URL</label>
                <input
                  type="text"
                  value={openClawUrl}
                  onChange={(e) => setOpenClawUrl(e.target.value)}
                  placeholder="http://127.0.0.1:18789"
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground placeholder-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/40 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Auth Token</label>
                <input
                  type="password"
                  value={openClawToken}
                  onChange={(e) => setOpenClawToken(e.target.value)}
                  placeholder="Your gateway token"
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground placeholder-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/40 transition-colors"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleOpenClawConnect();
                    }
                  }}
                />
              </div>
              <button
                onClick={handleOpenClawConnect}
                disabled={openClawConnecting || !openClawUrl.trim() || !openClawToken.trim()}
                className="w-full py-2.5 px-4 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {openClawConnecting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  "Connect"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <Notifications />
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <div className="p-5 rounded-2xl bg-card/50 border border-border/50 hover:bg-card hover:border-border transition-all duration-200 group">
      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/15 transition-colors">
        <Icon className="w-5 h-5 text-primary" />
      </div>
      <h3 className="font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function IntegrationButton({
  integration,
  isConnected,
  isConnecting,
  onClick,
}: {
  integration: Integration;
  isConnected: boolean;
  isConnecting: boolean;
  onClick: () => void;
}) {
  const isConnectable = integration.composioToolkit != null || integration.authType === "openclaw";

  return (
    <div className="relative group/int">
      <button
        onClick={onClick}
        disabled={isConnecting}
        className={clsx(
          "w-10 h-10 flex items-center justify-center rounded-xl border transition-all duration-150",
          isConnectable
            ? "bg-card border-border hover:border-foreground/20 cursor-pointer group-hover/int:scale-105"
            : "bg-card/50 border-border/50 cursor-default opacity-50",
          isConnected && "border-border",
        )}>
        {isConnecting ? (
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        ) : (
          <img
            alt={`${integration.name} logo`}
            className="h-5 w-5"
            loading="lazy"
            src={integration.icon}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        )}

        {/* Connected dot badge */}
        {isConnected && !isConnecting && (
          <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full ring-2 ring-card" />
        )}
      </button>

      {/* Tooltip */}
      <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1 bg-popover text-popover-foreground text-xs font-medium rounded-lg whitespace-nowrap opacity-0 group-hover/int:opacity-100 transition-opacity duration-150 z-10 border border-border shadow-lg">
        {integration.name}
        {isConnected && (
          <span className="ml-1.5 text-green-400">Connected</span>
        )}
        {!isConnectable && (
          <span className="ml-1.5 text-muted-foreground">Soon</span>
        )}
      </span>
    </div>
  );
}
