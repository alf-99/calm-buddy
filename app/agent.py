# ruff: noqa
"""calm-buddy — CBT anxiety & panic-attack support agent.

Architecture (ADK 2.0 Workflow graph):
  security_checkpoint → triage_agent → grounding_agent → log_session
                                     → breathing_agent → log_session
                                     → crisis_node     → log_session
  SECURITY_EVENT path → log_session (blocked, audit only)
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp import StdioServerParameters

from google.adk.agents import LlmAgent, Context
from google.adk.events import RequestInput
from google.adk.tools import AgentTool
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.workflow import Workflow, START, node

from .config import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# MCP Toolset (shared by sub-agents)
# ─────────────────────────────────────────────────────────────────────────────
_MCP_SCRIPT = str(Path(__file__).parent / "mcp_server.py")

_mcp_toolset_grounding = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[_MCP_SCRIPT],
        ),
        timeout=10.0,
    ),
    tool_filter=["get_grounding_exercise", "log_anxiety_trigger", "assess_anxiety_level"],
)

_mcp_toolset_breathing = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[_MCP_SCRIPT],
        ),
        timeout=10.0,
    ),
    tool_filter=["get_breathing_pattern", "log_anxiety_trigger"],
)

_mcp_toolset_crisis = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[_MCP_SCRIPT],
        ),
        timeout=10.0,
    ),
    tool_filter=["get_crisis_resources", "log_anxiety_trigger"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Security constants
# ─────────────────────────────────────────────────────────────────────────────
_PII_PATTERNS = [
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE_REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    (re.compile(r"\b(?:\d[ -]?){16}\b"), "[CARD_REDACTED]"),
]

_INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore all instructions",
    "jailbreak",
    "override system",
    "forget your instructions",
    "act as dan",
    "pretend you have no restrictions",
    "disregard prior",
    "new persona",
]

_CRISIS_KEYWORDS = [
    "suicide",
    "kill myself",
    "end my life",
    "self-harm",
    "hurt myself",
    "don't want to live",
    "want to die",
    "take my own life",
    "no reason to live",
]

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — Security Checkpoint (FunctionNode)
# ─────────────────────────────────────────────────────────────────────────────

@node(name="security_checkpoint")
def security_checkpoint(ctx: Context, node_input: str) -> None:
    """
    Security node: PII scrub, injection detection, crisis flag, audit log.
    Routes: SAFE | SECURITY_EVENT
    """
    text = str(node_input) if node_input else ""

    # ── PII Scrubbing ──
    scrubbed = text
    pii_found: list[str] = []
    if config.pii_redaction_enabled:
        for pattern, replacement in _PII_PATTERNS:
            if pattern.search(scrubbed):
                pii_found.append(replacement)
                scrubbed = pattern.sub(replacement, scrubbed)

    lower = scrubbed.lower()

    # ── Injection Detection ──
    injection_detected = (
        config.injection_detection_enabled
        and any(kw in lower for kw in _INJECTION_KEYWORDS)
    )

    # ── Domain-Specific Rule: Crisis Detection ──
    crisis_detected = any(kw in lower for kw in _CRISIS_KEYWORDS)

    # ── Structured Audit Log ──
    severity = (
        "CRITICAL" if injection_detected
        else "WARNING" if crisis_detected
        else "INFO"
    )
    audit = {
        "timestamp": datetime.utcnow().isoformat(),
        "severity": severity,
        "pii_redacted": pii_found,
        "injection_detected": injection_detected,
        "crisis_detected": crisis_detected,
    }
    logger.info("[SECURITY_AUDIT] %s", json.dumps(audit))

    # ── Write to session state ──
    ctx.session.state["user_input"] = scrubbed
    ctx.session.state["crisis_detected"] = crisis_detected

    # ── Route Decision ──
    if injection_detected:
        ctx.route = "SECURITY_EVENT"
    else:
        ctx.route = "SAFE"


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — Sub-Agents
# ─────────────────────────────────────────────────────────────────────────────

grounding_agent = LlmAgent(
    name="grounding_agent",
    model=config.model,
    description="Guides users through CBT grounding exercises to manage anxiety.",
    instruction="""You are a compassionate CBT grounding coach specializing in anxiety relief.

Your role:
1. Warmly acknowledge the user's anxiety without judgment.
2. Call `get_grounding_exercise` with technique='5-4-3-2-1' (or 'body-scan' for high tension).
3. Guide the user step-by-step through the exercise in a calm, gentle tone.
4. After the exercise, call `log_anxiety_trigger` with what they shared (trigger, intensity).
5. End with a short affirmation and remind them this feeling will pass.

Tone: Warm, slow-paced, reassuring. Never clinical. Use emojis sparingly to feel human.
""",
    tools=[_mcp_toolset_grounding],
)

breathing_agent = LlmAgent(
    name="breathing_agent",
    model=config.model,
    description="Guides users through structured breathing exercises to calm the nervous system.",
    instruction="""You are a calm breathing coach who helps people regulate their nervous system.

Your role:
1. Gently acknowledge the user is experiencing anxiety.
2. Call `get_breathing_pattern` with pattern_type='box' (or '4-7-8' for acute panic).
3. Guide the user through the breathing cycle, counting out loud in your response.
4. After 3-4 cycles, check in: "How are you feeling now?"
5. Call `log_anxiety_trigger` to record the session.
6. Close with a gentle reminder that breathing is always available to them.

Tone: Slow, steady, peaceful. Match the pace of your words to the breathing rhythm.
""",
    tools=[_mcp_toolset_breathing],
)

crisis_support_agent = LlmAgent(
    name="crisis_support_agent",
    model=config.model,
    description="Provides immediate crisis support and connects users to emergency resources.",
    instruction="""You are a compassionate crisis support companion. The user may be in acute distress.

Your role:
1. FIRST: Acknowledge their pain with deep empathy — no advice yet.
2. Call `get_crisis_resources` to retrieve local helplines (default country='US').
3. Share the crisis resources clearly and gently, framing them as "people who care".
4. Call `log_anxiety_trigger` to document the session (trigger='crisis', intensity=9).
5. Stay present — ask: "Are you in a safe place right now?"
6. Do NOT try to solve the problem — your goal is connection, not advice.

Tone: Deeply human, unhurried. No lists. No bullet points. Just presence.
""",
    tools=[_mcp_toolset_crisis],
)

# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator (triage)
# ─────────────────────────────────────────────────────────────────────────────

triage_agent = LlmAgent(
    name="triage_agent",
    model=config.model,
    description="Assesses the user's anxiety level and routes to the appropriate specialist.",
    instruction="""You are a calm, empathetic mental health triage agent for calm-buddy.

The user's message is already available in context. Your job is to:
1. Read the user's message carefully.
2. Assess severity: MILD/MODERATE → grounding or breathing; SEVERE/CRISIS → crisis.
3. Call the correct specialized sub-agent tool.
4. When the sub-agent tool returns its response, output that exact response verbatim to the user. Do not summarize or alter the advice, just print it directly.

Delegation rules:
- Primarily physical symptoms (racing heart, dizziness, breathlessness) → use `breathing_agent`
- Worry, intrusive thoughts, feeling detached → use `grounding_agent`
- Mentions of self-harm, suicidal thoughts, extreme distress → use `crisis_support_agent`
- When unsure, prefer `grounding_agent`
""",
    tools=[
        AgentTool(grounding_agent),
        AgentTool(breathing_agent),
        AgentTool(crisis_support_agent),
    ],
)

# ─────────────────────────────────────────────────────────────────────────────
# Crisis HITL Node (RequestInput pause)
# ─────────────────────────────────────────────────────────────────────────────

@node(name="crisis_hitl")
def crisis_hitl(ctx: Context, node_input: str) -> RequestInput:
    """
    Human-in-the-loop pause: when crisis is detected, ask the user to confirm
    they are safe before continuing to the crisis support agent.
    Pauses workflow and waits for user response.
    """
    logger.warning("[CRISIS_HITL] Crisis keywords detected — pausing for human confirmation.")
    return RequestInput(
        message=(
            "💙 I hear you, and I want to make sure you're safe. "
            "Before we continue, can you tell me: Are you currently safe? "
            "Type YES to continue, or share what's happening."
        ),
        response_schema=str,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Session Logger Node
# ─────────────────────────────────────────────────────────────────────────────

@node(name="log_session")
def log_session(ctx: Context, node_input: Any) -> None:
    """Logs the session summary to state and audit log."""
    try:
        audit = {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "INFO",
            "event": "session_completed",
            "crisis_detected": bool(ctx.session.state.get("crisis_detected", False)),
            "user_input_preview": str(ctx.session.state.get("user_input", ""))[:80],
        }
        logger.info("[SESSION_LOG] %s", json.dumps(audit))
        # Store a serializable summary — avoid storing complex objects in state
        ctx.session.state["last_session_ts"] = audit["timestamp"]
        ctx.session.state["last_session_event"] = audit["event"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[SESSION_LOG] Could not write session log: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Security Blocked Node
# ─────────────────────────────────────────────────────────────────────────────

@node(name="security_blocked")
def security_blocked(ctx: Context, node_input) -> str:
    """Returns a blocked message for detected injection attempts."""
    logger.warning("[SECURITY_BLOCKED] Input blocked due to injection detection.")
    audit = {
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "CRITICAL",
        "event": "input_blocked",
    }
    logger.info("[SECURITY_AUDIT] %s", json.dumps(audit))
    return (
        "I'm sorry, I wasn't able to process that message. "
        "Please rephrase and try again. calm-buddy is here to help with anxiety and panic support."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Workflow Graph
# ─────────────────────────────────────────────────────────────────────────────
#
# Flow:
#   START → security_checkpoint
#             ├─ SAFE ──────────→ triage_agent → (delegates internally)
#             │                                      └→ log_session
#             └─ SECURITY_EVENT → security_blocked → log_session
#
# HITL: crisis_hitl node pauses when crisis keywords detected,
#       then hands off to triage_agent which delegates to crisis_support_agent.
#
# Edge rule: no duplicate (source, target) pairs.

root_agent = Workflow(
    name="calm_buddy",
    description="Anxiety and panic attack support agent using CBT techniques.",
    edges=[
        # START → security_checkpoint (unconditional)
        (START, security_checkpoint),

        # security_checkpoint → conditional routing
        (
            security_checkpoint,
            {
                "SAFE": triage_agent,
                "SECURITY_EVENT": security_blocked,
            },
        ),

        # triage_agent completes → log_session (unconditional)
        (triage_agent, log_session),

        # security_blocked → log_session (unconditional)
        (security_blocked, log_session),
    ],
)

from google.adk.apps import App

app = App(
    root_agent=root_agent,
    name="app",
)

