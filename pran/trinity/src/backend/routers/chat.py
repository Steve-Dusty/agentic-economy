"""
Agent chat and activity routes for the Trinity backend.

Includes execution queue integration to prevent parallel execution on the same agent.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
import httpx
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional

from models import User, ChatMessageRequest, ModelChangeRequest, ParallelTaskRequest, ActivityType, ExecutionSource
from dependencies import get_current_user
from services.docker_service import get_agent_container
from services.activity_service import activity_service
from services.execution_queue import get_execution_queue, QueueFullError, AgentBusyError
from services.slot_service import get_slot_service
from services.task_execution_service import (
    get_task_execution_service,
    agent_post_with_retry,
)
from database import db
from utils.credential_sanitizer import sanitize_execution_log, sanitize_response

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/agents", tags=["chat"])

# WebSocket manager (injected from main.py)
_websocket_manager = None


def set_websocket_manager(manager):
    """Set WebSocket manager for broadcasting collaboration events."""
    global _websocket_manager
    _websocket_manager = manager


async def broadcast_collaboration_event(source_agent: str, target_agent: str, action: str = "chat"):
    """Broadcast agent collaboration event to all WebSocket clients."""
    if _websocket_manager:
        event = {
            "type": "agent_collaboration",
            "source_agent": source_agent,
            "target_agent": target_agent,
            "action": action,
            "timestamp": datetime.utcnow().isoformat()
        }
        await _websocket_manager.broadcast(json.dumps(event))
    else:
        print(f"[Warning] WebSocket manager not set, skipping collaboration broadcast")


@router.post("/{name}/chat")
async def chat_with_agent(
    name: str,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    x_source_agent: Optional[str] = Header(None),
    x_via_mcp: Optional[str] = Header(None),
    x_mcp_key_id: Optional[str] = Header(None),
    x_mcp_key_name: Optional[str] = Header(None)
):
    """
    Proxy chat messages to agent's internal web server and persist to database.

    This endpoint enforces single-execution-at-a-time via the execution queue.
    If the agent is busy, the request is queued (up to 3 waiting).
    If the queue is full, returns 429 Too Many Requests.

    Headers:
    - X-Source-Agent: Set when one agent calls another (agent-to-agent)
    - X-Via-MCP: Set for all MCP calls (both user and agent-scoped)
    """
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(status_code=503, detail="Agent is not running")

    # Determine execution source
    if x_source_agent:
        source = ExecutionSource.AGENT
    else:
        source = ExecutionSource.USER

    # Create execution request and submit to queue
    queue = get_execution_queue()
    execution = queue.create_execution(
        agent_name=name,
        message=request.message,
        source=source,
        source_agent=x_source_agent,
        source_user_id=str(current_user.id),
        source_user_email=current_user.email or current_user.username
    )

    try:
        queue_result, execution = await queue.submit(execution, wait_if_busy=True)
        logger.info(f"[Chat] Agent '{name}' execution {execution.id}: {queue_result}")
    except QueueFullError as e:
        logger.warning(f"[Chat] Agent '{name}' queue full, rejecting request")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Agent queue is full",
                "agent": name,
                "queue_length": e.queue_length,
                "retry_after": 30,
                "message": f"Agent '{name}' is busy with {e.queue_length} queued requests. Please try again later."
            }
        )

    # Track queue position for observability
    is_queued = queue_result.startswith("queued:")

    # Create execution record for all MCP calls (both agent-to-agent and user MCP)
    # This ensures they appear in the Tasks tab alongside scheduled and manual tasks
    task_execution_id = None
    is_mcp_call = x_source_agent or x_via_mcp
    if is_mcp_call:
        # Determine triggered_by: "agent" for agent-to-agent, "mcp" for user MCP calls
        triggered_by = "agent" if x_source_agent else "mcp"
        task_execution = db.create_task_execution(
            agent_name=name,
            message=request.message,
            triggered_by=triggered_by,
            source_user_id=current_user.id,
            source_user_email=current_user.email or current_user.username,
            source_agent_name=x_source_agent,
            source_mcp_key_id=x_mcp_key_id,
            source_mcp_key_name=x_mcp_key_name
        )
        task_execution_id = task_execution.id if task_execution else None
        if x_source_agent:
            logger.info(f"[Chat] Created task execution {task_execution_id} for agent-to-agent call from {x_source_agent}")
        else:
            logger.info(f"[Chat] Created task execution {task_execution_id} for MCP call from user {current_user.username}")

    # Broadcast collaboration event if this is agent-to-agent communication
    collaboration_activity_id = None
    if x_source_agent:
        await broadcast_collaboration_event(
            source_agent=x_source_agent,
            target_agent=name,
            action="chat"
        )

        # Track agent collaboration activity
        collaboration_activity_id = await activity_service.track_activity(
            agent_name=x_source_agent,  # Activity belongs to source agent
            activity_type=ActivityType.AGENT_COLLABORATION,
            user_id=current_user.id,
            triggered_by="agent",
            related_execution_id=task_execution_id,  # Database execution ID for structured queries
            details={
                "source_agent": x_source_agent,
                "target_agent": name,
                "action": "chat",
                "message_preview": request.message[:100],
                "execution_id": task_execution_id,  # Also in details for WebSocket events
                "queue_status": queue_result
            }
        )

    # Get or create chat session for this user+agent
    session = db.get_or_create_chat_session(
        agent_name=name,
        user_id=current_user.id,
        user_email=current_user.email or current_user.username
    )

    # Track chat start activity
    # triggered_by: "agent" for agent-to-agent, "mcp" for user MCP calls, "user" for UI chat
    activity_triggered_by = "agent" if x_source_agent else ("mcp" if x_via_mcp else "user")
    chat_activity_id = await activity_service.track_activity(
        agent_name=name,
        activity_type=ActivityType.CHAT_START,
        user_id=current_user.id,
        triggered_by=activity_triggered_by,
        parent_activity_id=collaboration_activity_id,  # Link to collaboration if agent-initiated
        related_execution_id=task_execution_id,  # Database execution ID for structured queries
        details={
            "message_preview": request.message[:100],
            "source_agent": x_source_agent,
            "execution_id": task_execution_id,  # Also in details for WebSocket events
            "queue_status": queue_result
        }
    )

    # Log user message to database
    user_message = db.add_chat_message(
        session_id=session.id,
        agent_name=name,
        user_id=current_user.id,
        user_email=current_user.email or current_user.username,
        role="user",
        content=request.message
    )

    execution_success = False
    try:
        payload = {"message": request.message, "stream": False}
        if request.model:
            payload["model"] = request.model

        start_time = datetime.utcnow()

        # Use retry helper to handle agent server startup delays
        response = await agent_post_with_retry(
            name,
            "/api/chat",
            payload,
            max_retries=3,
            retry_delay=1.0,
            timeout=600.0  # 10 min timeout for chat mode
        )
        response.raise_for_status()

        response_data = response.json()

        # Extract metadata for persistence
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        metadata = response_data.get("metadata", {})
        session_data = response_data.get("session", {})

        # Serialize tool calls if present
        # Note: Check is not None, not truthiness - empty list [] is valid log
        # execution_log is now raw Claude Code format for UI
        # execution_log_simplified is the old format for activity tracking
        execution_log = response_data.get("execution_log", [])
        execution_log_simplified = response_data.get("execution_log_simplified", execution_log)
        execution_log_json = json.dumps(execution_log) if execution_log is not None else None
        tool_calls_json = json.dumps(execution_log_simplified) if execution_log_simplified is not None else None

        # SECURITY: Sanitize credentials from execution logs and response before persistence
        execution_log_json = sanitize_execution_log(execution_log_json)
        tool_calls_json = sanitize_execution_log(tool_calls_json)
        sanitized_response = sanitize_response(response_data.get("response", ""))

        # Log assistant response to database with observability data
        # SECURITY: Use sanitized response
        assistant_message = db.add_chat_message(
            session_id=session.id,
            agent_name=name,
            user_id=current_user.id,
            user_email=current_user.email or current_user.username,
            role="assistant",
            content=sanitized_response,
            cost=metadata.get("cost_usd"),
            context_used=session_data.get("context_tokens"),
            context_max=session_data.get("context_window"),
            tool_calls=tool_calls_json,
            execution_time_ms=execution_time_ms
        )

        # Note: Tool calls are stored in chat_messages.tool_calls JSON column
        # Individual tool_call activities were removed (Issue #45) - they were
        # duplicate data that accumulated as orphans (never completed)

        # Track chat completion
        await activity_service.complete_activity(
            activity_id=chat_activity_id,
            status="completed",
            details={
                "related_chat_message_id": assistant_message.id,
                "context_used": session_data.get("context_tokens"),
                "context_max": session_data.get("context_window"),
                "cost_usd": metadata.get("cost_usd"),
                "execution_time_ms": execution_time_ms,
                "tool_count": len(execution_log_simplified),
                "execution_id": task_execution_id  # Use database execution ID, not queue ID
            }
        )

        # Complete collaboration activity if this was agent-to-agent
        if collaboration_activity_id:
            await activity_service.complete_activity(
                activity_id=collaboration_activity_id,
                status="completed",
                details={
                    "related_chat_message_id": assistant_message.id,
                    "response_length": len(response_data.get("response", "")),
                    "execution_time_ms": execution_time_ms,
                    "execution_id": task_execution_id  # Use database execution ID, not queue ID
                }
            )

        # Update task execution record for MCP calls (agent-to-agent or user MCP)
        # SECURITY: Use sanitized response and execution logs
        if task_execution_id:
            context_used = session_data.get("context_tokens", 0)
            db.update_execution_status(
                execution_id=task_execution_id,
                status="success",
                response=sanitized_response,
                context_used=context_used if context_used > 0 else None,
                context_max=session_data.get("context_window") or 200000,
                cost=metadata.get("cost_usd"),
                tool_calls=tool_calls_json,  # Simplified format for activity tracking
                execution_log=execution_log_json  # Raw Claude Code format for UI
            )

        execution_success = True

        # Add execution metadata to response
        # Include both IDs for clarity:
        # - id: Queue execution ID (transient, for queue status tracking)
        # - task_execution_id: Database execution ID (permanent, for API queries and navigation)
        response_data["execution"] = {
            "id": execution.id,  # Queue ID (transient)
            "task_execution_id": task_execution_id,  # Database ID (permanent) - use this for navigation
            "queue_status": queue_result,
            "was_queued": is_queued
        }

        return response_data
    except httpx.HTTPError as e:
        import logging
        # Extract detailed error message from agent response if available
        error_msg = f"HTTP error: {type(e).__name__}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                if "detail" in error_data:
                    error_msg = error_data["detail"]
            except Exception:
                # Try raw text if JSON parsing fails
                if e.response.text:
                    error_msg = e.response.text[:500]
        logging.getLogger("trinity.errors").error(f"Failed to communicate with agent {name}: {error_msg}")

        # Track chat failure
        await activity_service.complete_activity(
            activity_id=chat_activity_id,
            status="failed",
            error=error_msg
        )

        # Update task execution record for agent-to-agent calls on failure
        if task_execution_id:
            db.update_execution_status(
                execution_id=task_execution_id,
                status="failed",
                error=error_msg
            )

        # Complete collaboration activity on failure (was missing - caused activities to stay in "started" state)
        if collaboration_activity_id:
            await activity_service.complete_activity(
                activity_id=collaboration_activity_id,
                status="failed",
                error=error_msg
            )

        raise HTTPException(
            status_code=503,
            detail=f"Failed to communicate with agent: {error_msg}"
        )
    finally:
        # Always release the queue slot when done
        await queue.complete(name, success=execution_success)


async def _execute_task_background(
    agent_name: str,
    request: ParallelTaskRequest,
    execution_id: str,
    task_activity_id: str,
    collaboration_activity_id: Optional[str],
    x_source_agent: Optional[str],
    release_slot: bool = False,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None
):
    """
    Background task execution for async mode.
    Runs the task and updates execution record/activities when complete.

    Args:
        release_slot: If True, release the slot when task completes (CAPACITY-001)
        user_id: User ID for session persistence (THINK-001)
        user_email: User email for session persistence (THINK-001)
    """
    slot_service = get_slot_service() if release_slot else None
    try:
        payload = {
            "message": request.message,
            "model": request.model,
            "allowed_tools": request.allowed_tools,
            "system_prompt": request.system_prompt,
            "timeout_seconds": request.timeout_seconds,
            "execution_id": execution_id,
            "resume_session_id": request.resume_session_id  # EXEC-023: Claude Code session resume
        }

        start_time = datetime.utcnow()

        response = await agent_post_with_retry(
            agent_name,
            "/api/task",
            payload,
            max_retries=3,
            retry_delay=1.0,
            timeout=float(request.timeout_seconds or 600) + 10
        )
        response.raise_for_status()

        response_data = response.json()
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        metadata = response_data.get("metadata", {})

        # SECURITY: Sanitize credentials from execution logs and response
        sanitized_resp = sanitize_response(response_data.get("response"))
        context_used = metadata.get("input_tokens", 0) + metadata.get("output_tokens", 0)

        # Update execution record with success
        if execution_id:
            execution_log = response_data.get("execution_log", [])
            execution_log_json = json.dumps(execution_log) if execution_log else None
            execution_log_json = sanitize_execution_log(execution_log_json)

            db.update_execution_status(
                execution_id=execution_id,
                status="success",
                response=sanitized_resp,
                context_used=context_used if context_used > 0 else None,
                context_max=metadata.get("context_window") or 200000,
                cost=metadata.get("cost_usd"),
                tool_calls=execution_log_json,
                execution_log=execution_log_json
            )

        # THINK-001: Persist to chat session if requested (for authenticated Chat tab async mode)
        if request.save_to_session and user_id and user_email:
            try:
                if request.create_new_session:
                    session = db.create_new_chat_session(
                        agent_name=agent_name,
                        user_id=user_id,
                        user_email=user_email
                    )
                else:
                    session = db.get_or_create_chat_session(
                        agent_name=agent_name,
                        user_id=user_id,
                        user_email=user_email
                    )

                original_user_message = request.user_message or request.message
                db.add_chat_message(
                    session_id=session.id,
                    agent_name=agent_name,
                    user_id=user_id,
                    user_email=user_email,
                    role="user",
                    content=original_user_message
                )

                db.add_chat_message(
                    session_id=session.id,
                    agent_name=agent_name,
                    user_id=user_id,
                    user_email=user_email,
                    role="assistant",
                    content=sanitized_resp or "",
                    cost=metadata.get("cost_usd"),
                    context_used=context_used if context_used > 0 else None,
                    context_max=metadata.get("context_window") or 200000,
                    execution_time_ms=execution_time_ms
                )

                # Broadcast chat_session_id via WebSocket so frontend can update
                if _websocket_manager:
                    await _websocket_manager.broadcast(json.dumps({
                        "type": "chat_response_ready",
                        "execution_id": execution_id,
                        "agent_name": agent_name,
                        "chat_session_id": session.id,
                        "timestamp": datetime.utcnow().isoformat()
                    }))

                logger.debug(f"[Task Async] Saved to chat session {session.id} for agent '{agent_name}'")
            except Exception as e:
                logger.warning(f"[Task Async] Failed to save to chat session for agent '{agent_name}': {e}")

        # Complete activities
        await activity_service.complete_activity(
            activity_id=task_activity_id,
            status="completed",
            details={
                "cost_usd": metadata.get("cost_usd"),
                "execution_time_ms": execution_time_ms,
                "tool_count": len(response_data.get("execution_log", [])),
                "async_mode": True
            }
        )

        if collaboration_activity_id:
            await activity_service.complete_activity(
                activity_id=collaboration_activity_id,
                status="completed",
                details={
                    "response_length": len(response_data.get("response", "")),
                    "execution_time_ms": execution_time_ms,
                    "execution_id": execution_id
                }
            )

        logger.info(f"[Task Async] Completed background task for agent '{agent_name}', execution_id={execution_id}")

    except Exception as e:
        # Extract detailed error from HTTP response body if available
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                if "detail" in error_data:
                    error_msg = error_data["detail"]
            except Exception:
                if hasattr(e.response, 'text') and e.response.text:
                    error_msg = e.response.text[:500]
        logger.error(f"[Task Async] Background task failed for agent '{agent_name}': {error_msg}")

        # Update execution record with failure
        if execution_id:
            existing = db.get_execution(execution_id)
            if not existing or existing.status != "cancelled":
                db.update_execution_status(
                    execution_id=execution_id,
                    status="failed",
                    error=error_msg
                )

        # Complete activities with failure
        await activity_service.complete_activity(
            activity_id=task_activity_id,
            status="failed",
            error=error_msg
        )

        if collaboration_activity_id:
            await activity_service.complete_activity(
                activity_id=collaboration_activity_id,
                status="failed",
                error=error_msg
            )

    finally:
        # Release slot when task completes (CAPACITY-001)
        if slot_service and release_slot:
            await slot_service.release_slot(agent_name, execution_id)


@router.post("/{name}/task")
async def execute_parallel_task(
    name: str,
    request: ParallelTaskRequest,
    current_user: User = Depends(get_current_user),
    x_source_agent: Optional[str] = Header(None),
    x_via_mcp: Optional[str] = Header(None),
    x_mcp_key_id: Optional[str] = Header(None),
    x_mcp_key_name: Optional[str] = Header(None)
):
    """
    Execute a stateless task in parallel mode (no conversation context).

    Unlike /chat, this endpoint:
    - Does NOT use execution queue (parallel allowed)
    - Does NOT use --continue flag (stateless)
    - Each call is independent and can run concurrently

    Use this for:
    - Agent delegation from orchestrators
    - Batch processing without context pollution
    - Parallel task execution

    Note: Does NOT update conversation history or session state.
    Executions are saved to the database for history tracking.
    """
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(status_code=503, detail="Agent is not running")

    # Determine execution source for logging
    if x_source_agent:
        source = ExecutionSource.AGENT
        triggered_by = "agent"
    else:
        source = ExecutionSource.USER
        triggered_by = "manual"

    # Create execution record in database (persisted task history)
    execution = db.create_task_execution(
        agent_name=name,
        message=request.message,
        triggered_by=triggered_by,
        source_user_id=current_user.id,
        source_user_email=current_user.email or current_user.username,
        source_agent_name=x_source_agent,
        source_mcp_key_id=x_mcp_key_id,
        source_mcp_key_name=x_mcp_key_name,
        model_used=request.model
    )
    execution_id = execution.id if execution else None

    # Broadcast collaboration event if this is agent-to-agent communication
    # Track collaboration activity FIRST (belongs to source agent) - mirrors /api/chat pattern
    collaboration_activity_id = None
    if x_source_agent:
        await broadcast_collaboration_event(
            source_agent=x_source_agent,
            target_agent=name,
            action="parallel_task"
        )

        # Track agent collaboration activity (belongs to source agent for Dashboard arrows)
        collaboration_activity_id = await activity_service.track_activity(
            agent_name=x_source_agent,  # Activity belongs to source agent (the caller)
            activity_type=ActivityType.AGENT_COLLABORATION,
            user_id=current_user.id,
            triggered_by="agent",
            related_execution_id=execution_id,  # Database execution ID for structured queries
            details={
                "source_agent": x_source_agent,
                "target_agent": name,
                "action": "parallel_task",
                "message_preview": request.message[:100],
                "execution_id": execution_id,  # Also in details for WebSocket events
                "parallel_mode": True
            }
        )

    # Async mode: acquire slot here, spawn background task which releases it
    if request.async_mode:
        slot_service = get_slot_service()
        max_parallel_tasks = db.get_max_parallel_tasks(name)
        slot_acquired = await slot_service.acquire_slot(
            agent_name=name,
            execution_id=execution_id or f"temp-{datetime.utcnow().timestamp()}",
            max_parallel_tasks=max_parallel_tasks,
            message_preview=request.message[:100] if request.message else ""
        )

        if not slot_acquired:
            if execution_id:
                db.update_execution_status(
                    execution_id=execution_id,
                    status="failed",
                    error=f"Agent at capacity ({max_parallel_tasks}/{max_parallel_tasks} parallel tasks running)"
                )
            raise HTTPException(
                status_code=429,
                detail=f"Agent '{name}' is at capacity ({max_parallel_tasks} parallel tasks). Try again later."
            )

        # Track parallel task activity (belongs to target agent)
        task_activity_id = await activity_service.track_activity(
            agent_name=name,
            activity_type=ActivityType.CHAT_START,
            user_id=current_user.id,
            triggered_by=triggered_by,
            parent_activity_id=collaboration_activity_id,
            related_execution_id=execution_id,
            details={
                "message_preview": request.message[:100],
                "source_agent": x_source_agent,
                "parallel_mode": True,
                "async_mode": True,
                "model": request.model,
                "timeout_seconds": request.timeout_seconds,
                "execution_id": execution_id
            }
        )

        # Update execution status to "running"
        if execution_id:
            db.update_execution_status(execution_id=execution_id, status="running")

        # Spawn background task (slot will be released when task completes)
        asyncio.create_task(
            _execute_task_background(
                agent_name=name,
                request=request,
                execution_id=execution_id,
                task_activity_id=task_activity_id,
                collaboration_activity_id=collaboration_activity_id,
                x_source_agent=x_source_agent,
                release_slot=True,  # CAPACITY-001: Release slot when background task completes
                user_id=current_user.id,  # THINK-001: Pass user context for session persistence
                user_email=current_user.email or current_user.username
            )
        )

        # Return immediately with execution_id for polling
        logger.info(f"[Task Async] Started background task for agent '{name}', execution_id={execution_id}")
        return {
            "status": "accepted",
            "execution_id": execution_id,
            "agent_name": name,
            "message": "Task accepted. Poll GET /api/agents/{name}/executions/{execution_id} for results.",
            "async_mode": True
        }

    # ---- Sync mode: delegate to TaskExecutionService (EXEC-024) ----
    task_execution_service = get_task_execution_service()
    result = await task_execution_service.execute_task(
        agent_name=name,
        message=request.message,
        triggered_by=triggered_by,
        source_user_id=current_user.id,
        source_user_email=current_user.email or current_user.username,
        source_agent_name=x_source_agent,
        source_mcp_key_id=x_mcp_key_id,
        source_mcp_key_name=x_mcp_key_name,
        model=request.model,
        timeout_seconds=request.timeout_seconds or 900,
        resume_session_id=request.resume_session_id,
        allowed_tools=request.allowed_tools,
        system_prompt=request.system_prompt,
        execution_id=execution_id,
    )

    # Complete collaboration activity based on result
    if collaboration_activity_id:
        await activity_service.complete_activity(
            activity_id=collaboration_activity_id,
            status="completed" if result.status == "success" else "failed",
            details={
                "response_length": len(result.response),
                "execution_id": execution_id,
            },
            error=result.error if result.status == "failed" else None,
        )

    # Handle failure — translate to HTTP errors
    if result.status == "failed":
        if "at capacity" in (result.error or ""):
            raise HTTPException(
                status_code=429,
                detail=f"Agent '{name}' is at capacity. Try again later."
            )
        elif "timed out" in (result.error or ""):
            raise HTTPException(
                status_code=504,
                detail=result.error
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=result.error or "Failed to execute task. The agent may be unavailable."
            )

    # Build response from service result
    response_data = result.raw_response

    # Persist to chat session if requested (for authenticated Chat tab)
    if request.save_to_session:
        try:
            if request.create_new_session:
                session = db.create_new_chat_session(
                    agent_name=name,
                    user_id=current_user.id,
                    user_email=current_user.email or current_user.username
                )
            else:
                session = db.get_or_create_chat_session(
                    agent_name=name,
                    user_id=current_user.id,
                    user_email=current_user.email or current_user.username
                )

            original_user_message = request.user_message or request.message

            db.add_chat_message(
                session_id=session.id,
                agent_name=name,
                user_id=current_user.id,
                user_email=current_user.email or current_user.username,
                role="user",
                content=original_user_message
            )

            db.add_chat_message(
                session_id=session.id,
                agent_name=name,
                user_id=current_user.id,
                user_email=current_user.email or current_user.username,
                role="assistant",
                content=result.response,
                cost=result.cost,
                context_used=result.context_used,
                context_max=result.context_max,
            )

            response_data["chat_session_id"] = session.id
            logger.debug(f"[Task] Saved to chat session {session.id} for agent '{name}'")
        except Exception as e:
            logger.warning(f"[Task] Failed to save to chat session for agent '{name}': {e}")

    # Add database execution ID to response for frontend tracking
    response_data["task_execution_id"] = execution_id

    return response_data


@router.get("/{name}/chat/history")
async def get_agent_chat_history(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """Get agent's conversation history."""
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(
            status_code=503,
            detail="Agent UI not enabled for this agent"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://agent-{name}:8000/api/chat/history",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        import logging
        logging.getLogger("trinity.errors").error(f"Failed to get chat history for {name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to get chat history"
        )


@router.delete("/{name}/chat/history")
async def reset_agent_chat_history(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """Reset/clear agent's conversation history (start a new session)."""
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(
            status_code=503,
            detail="Agent is not running"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://agent-{name}:8000/api/chat/history",
                timeout=10.0
            )
            # Agent may not implement this endpoint yet
            if response.status_code == 405:
                # Clear activity instead as a fallback
                await client.delete(
                    f"http://agent-{name}:8000/api/activity",
                    timeout=10.0
                )
                return {"status": "reset", "message": "Session activity cleared"}
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        import logging
        logging.getLogger("trinity.errors").error(f"Failed to reset chat history for {name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to reset chat history"
        )


@router.get("/{name}/chat/session")
async def get_agent_chat_session(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """Get agent's current session info including context usage."""
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Agent is not running"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://agent-{name}:8000/api/chat/session",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        import logging
        logging.getLogger("trinity.errors").error(f"Failed to get session info for {name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to get session info"
        )


# Activity Monitoring Routes

@router.get("/{name}/activity")
async def get_agent_activity(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """Get session activity for real-time monitoring."""
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        return {
            "status": "idle",
            "active_tool": None,
            "tool_counts": {},
            "timeline": [],
            "totals": {
                "calls": 0,
                "duration_ms": 0,
                "started_at": None
            }
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://agent-{name}:8000/api/activity",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        return {
            "status": "idle",
            "active_tool": None,
            "tool_counts": {},
            "timeline": [],
            "totals": {
                "calls": 0,
                "duration_ms": 0,
                "started_at": None
            }
        }


@router.get("/{name}/activity/{tool_id}")
async def get_agent_activity_detail(
    name: str,
    tool_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get full details for a specific tool call."""
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Agent is not running"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://agent-{name}:8000/api/activity/{tool_id}",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        import logging
        logging.getLogger("trinity.errors").error(f"Failed to get activity detail for {name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to get activity detail"
        )


@router.delete("/{name}/activity")
async def clear_agent_activity(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """Clear session activity (called when starting a new session)."""
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        return {
            "status": "cleared",
            "message": "Agent is not running - nothing to clear"
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://agent-{name}:8000/api/activity",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        import logging
        logging.getLogger("trinity.errors").error(f"Failed to clear activity for {name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to clear activity"
        )


# Model Routes

@router.get("/{name}/model")
async def get_agent_model(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """Get agent's current model configuration."""
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Agent is not running"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://agent-{name}:8000/api/model",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        import logging
        logging.getLogger("trinity.errors").error(f"Failed to get model info for {name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to get model info"
        )


@router.put("/{name}/model")
async def set_agent_model(
    name: str,
    request: ModelChangeRequest,
    current_user: User = Depends(get_current_user)
):
    """Set agent's model for subsequent messages."""
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Agent is not running"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://agent-{name}:8000/api/model",
                json={"model": request.model},
                timeout=10.0
            )
            response.raise_for_status()

            return response.json()
    except httpx.HTTPError as e:
        import logging
        logging.getLogger("trinity.errors").error(f"Failed to set model for {name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to set model"
        )


# Persistent Chat History Routes

@router.get("/{name}/chat/history/persistent")
async def get_persistent_chat_history(
    name: str,
    limit: int = 100,
    user_filter: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Get persistent chat history from database.

    This returns messages across all sessions, persisted in the database.
    Unlike /chat/history which returns only the current container session.

    Parameters:
    - limit: Maximum number of messages to return (default 100)
    - user_filter: If true, only show current user's messages (default false, shows all users for agent owners)
    """
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Determine if user should see all messages or just their own
    # Agent owners can see all messages, others only see their own
    user_id_filter = None
    if user_filter or current_user.role != "admin":
        # For non-admins, always filter to their own messages unless they're the owner
        # (Owner check would require checking agent_ownership table)
        user_id_filter = current_user.id

    messages = db.get_agent_chat_history(
        agent_name=name,
        user_id=user_id_filter,
        limit=limit
    )

    return {
        "agent_name": name,
        "message_count": len(messages),
        "messages": [msg.model_dump() for msg in messages]
    }


@router.get("/{name}/chat/sessions")
async def get_agent_chat_sessions(
    name: str,
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all chat sessions for an agent.

    Returns session metadata including message counts, costs, and timestamps.
    Non-admin users only see their own sessions.

    Parameters:
    - status: Filter by session status ('active' or 'closed')
    """
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Non-admins only see their own sessions
    user_id_filter = None if current_user.role == "admin" else current_user.id

    sessions = db.get_agent_chat_sessions(
        agent_name=name,
        user_id=user_id_filter,
        status=status
    )

    return {
        "agent_name": name,
        "session_count": len(sessions),
        "sessions": [session.model_dump() for session in sessions]
    }


@router.get("/{name}/chat/sessions/{session_id}")
async def get_chat_session_detail(
    name: str,
    session_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific chat session, including all messages.

    Parameters:
    - limit: Maximum number of messages to return (default 100)
    """
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    session = db.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Verify session belongs to this agent
    if session.agent_name != name:
        raise HTTPException(status_code=403, detail="Session does not belong to this agent")

    # Non-admins can only see their own sessions
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this session")

    messages = db.get_chat_messages(session_id, limit=limit)

    return {
        "session": session.model_dump(),
        "message_count": len(messages),
        "messages": [msg.model_dump() for msg in messages]
    }


@router.post("/{name}/chat/sessions/{session_id}/close")
async def close_chat_session(
    name: str,
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Close a chat session (marks it as closed but keeps the history)."""
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    session = db.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Verify session belongs to this agent and user
    if session.agent_name != name:
        raise HTTPException(status_code=403, detail="Session does not belong to this agent")

    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this session")

    success = db.close_chat_session(session_id)

    if success:
        return {"status": "closed", "session_id": session_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to close session")


# ============================================================================
# Execution Termination Routes
# ============================================================================

@router.post("/{name}/executions/{execution_id}/terminate")
async def terminate_agent_execution(
    name: str,
    execution_id: str,
    task_execution_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Terminate a running execution on an agent.

    Proxies the termination request to the agent container and clears
    the execution queue state if successful.

    Args:
        name: Agent name
        execution_id: The execution ID to terminate (from process registry)
        task_execution_id: Optional database execution ID to update status
    """
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(status_code=503, detail="Agent is not running")

    try:
        # Proxy termination request to agent container
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"http://agent-{name}:8000/api/executions/{execution_id}/terminate"
            )

        result = response.json()

        # Handle different termination outcomes
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Execution not found in agent")

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=result.get("detail", "Termination failed")
            )

        # Clear queue state if termination succeeded
        if result.get("status") in ["terminated", "already_finished"]:
            queue = get_execution_queue()
            await queue.force_release(name)
            logger.info(f"[Terminate] Released queue for agent '{name}' after terminating execution {execution_id}")

            # Update database execution record if provided
            if task_execution_id:
                db.update_execution_status(
                    execution_id=task_execution_id,
                    status="cancelled",
                    error="Execution terminated by user"
                )
                logger.info(f"[Terminate] Updated database execution {task_execution_id} to cancelled")

        # Track termination activity
        await activity_service.track_activity(
            agent_name=name,
            activity_type=ActivityType.EXECUTION_CANCELLED,
            user_id=current_user.id,
            triggered_by="user",
            related_execution_id=task_execution_id,
            details={
                "execution_id": execution_id,
                "task_execution_id": task_execution_id,
                "status": result.get("status"),
                "returncode": result.get("returncode")
            }
        )

        return result

    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to agent '{name}'"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout connecting to agent '{name}'"
        )


@router.get("/{name}/executions/running")
async def get_agent_running_executions(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get list of running executions on an agent.

    Returns execution IDs, start times, and metadata for running processes.
    """
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        return {"executions": []}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"http://agent-{name}:8000/api/executions/running"
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        return {"executions": []}


# ============================================================================
# Live Execution Streaming Routes
# ============================================================================

@router.get("/{name}/executions/{execution_id}/stream")
async def stream_execution_log(
    name: str,
    execution_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Stream execution log entries via Server-Sent Events (SSE).

    Proxies the SSE stream from the agent container to the frontend.
    Validates user access before starting the stream.

    SSE Event format:
    - data: JSON-encoded log entry from Claude Code
    - Final message: {"type": "stream_end"}

    Use this endpoint for live monitoring of running executions.
    """
    container = get_agent_container(name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    if container.status != "running":
        raise HTTPException(status_code=503, detail="Agent is not running")

    async def proxy_stream():
        """Proxy SSE stream from agent container."""
        agent_url = f"http://agent-{name}:8000/api/executions/{execution_id}/stream"
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", agent_url) as response:
                    if response.status_code == 404:
                        # Execution not found - send error and close
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Execution not found'})}\n\n"
                        yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                        return

                    if response.status_code != 200:
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Agent returned {response.status_code}'})}\n\n"
                        yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                        return

                    # Stream through data from agent
                    async for chunk in response.aiter_text():
                        yield chunk
        except httpx.ConnectError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to connect to agent'})}\n\n"
            yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
        except Exception as e:
            logger.error(f"[Stream] Error streaming from agent {name}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"

    return StreamingResponse(
        proxy_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
