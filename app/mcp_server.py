"""MCP server for calm-buddy — anxiety support tools (stdio transport)."""

import json
from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("calm-buddy-tools")


# ── Tool 1: Grounding exercise steps ─────────────────────────────────────────
@mcp.tool()
def get_grounding_exercise(technique: str = "5-4-3-2-1") -> str:
    """Return step-by-step instructions for a CBT grounding technique.

    Args:
        technique: One of '5-4-3-2-1', 'box-breathing', 'body-scan'.

    Returns:
        JSON string with the exercise steps.
    """
    exercises = {
        "5-4-3-2-1": {
            "name": "5-4-3-2-1 Grounding",
            "purpose": "Anchor to the present moment using your senses.",
            "steps": [
                "👀 Name 5 things you can SEE around you.",
                "🤲 Name 4 things you can TOUCH — notice their texture.",
                "👂 Name 3 things you can HEAR right now.",
                "👃 Name 2 things you can SMELL (or like the smell of).",
                "👅 Name 1 thing you can TASTE.",
            ],
            "duration": "3-5 minutes",
        },
        "box-breathing": {
            "name": "Box Breathing (4-4-4-4)",
            "purpose": "Regulate your nervous system with controlled breath.",
            "steps": [
                "Breathe IN slowly for 4 counts.",
                "HOLD your breath for 4 counts.",
                "Breathe OUT slowly for 4 counts.",
                "HOLD empty for 4 counts.",
                "Repeat 4–6 times.",
            ],
            "duration": "2-4 minutes",
        },
        "body-scan": {
            "name": "Progressive Body Scan",
            "purpose": "Release physical tension held from anxiety.",
            "steps": [
                "Close your eyes and take 3 slow breaths.",
                "Focus on your feet — notice any tension, then release it.",
                "Move up to your calves and thighs — breathe into tension.",
                "Focus on your stomach — soften with each exhale.",
                "Notice your shoulders and neck — roll them gently.",
                "Relax your jaw, eyes, and forehead completely.",
            ],
            "duration": "5-10 minutes",
        },
    }
    result = exercises.get(technique, exercises["5-4-3-2-1"])
    return json.dumps(result, indent=2)


# ── Tool 2: Breathing pattern ─────────────────────────────────────────────────
@mcp.tool()
def get_breathing_pattern(pattern_type: str = "box") -> str:
    """Return a guided breathing pattern for anxiety relief.

    Args:
        pattern_type: One of 'box', '4-7-8', 'resonance', 'coherent'.

    Returns:
        JSON string with the breathing pattern details.
    """
    patterns = {
        "box": {
            "name": "Box Breathing",
            "in_count": 4, "hold_in": 4, "out_count": 4, "hold_out": 4,
            "cycles": 6,
            "tip": "Used by US Navy SEALs to stay calm under pressure.",
        },
        "4-7-8": {
            "name": "4-7-8 Relaxation Breath",
            "in_count": 4, "hold_in": 7, "out_count": 8, "hold_out": 0,
            "cycles": 4,
            "tip": "Especially effective before sleep or during panic.",
        },
        "resonance": {
            "name": "Resonance / Coherent Breathing",
            "in_count": 5, "hold_in": 0, "out_count": 5, "hold_out": 0,
            "cycles": 10,
            "tip": "Targets 0.1 Hz heart rate variability for calm focus.",
        },
        "coherent": {
            "name": "Coherent Breathing (6 breaths/min)",
            "in_count": 5, "hold_in": 0, "out_count": 5, "hold_out": 0,
            "cycles": 12,
            "tip": "Synchronizes heart, lungs, and blood pressure oscillations.",
        },
    }
    result = patterns.get(pattern_type, patterns["box"])
    return json.dumps(result, indent=2)


# ── Tool 3: Log anxiety trigger ───────────────────────────────────────────────
@mcp.tool()
def log_anxiety_trigger(
    trigger: str,
    intensity: int = 5,
    symptoms: str = "",
    timestamp: str = "",
) -> str:
    """Log an anxiety trigger event for pattern tracking.

    Args:
        trigger: Description of what triggered the anxiety.
        intensity: Anxiety intensity 1-10 (10 = most severe).
        symptoms: Comma-separated physical/emotional symptoms.
        timestamp: ISO timestamp; defaults to now if empty.

    Returns:
        JSON confirmation with the log entry.
    """
    intensity = max(1, min(10, intensity))
    ts = timestamp if timestamp else datetime.utcnow().isoformat()
    entry = {
        "logged_at": ts,
        "trigger": trigger,
        "intensity": intensity,
        "severity": (
            "mild" if intensity <= 3
            else "moderate" if intensity <= 6
            else "severe"
        ),
        "symptoms": [s.strip() for s in symptoms.split(",") if s.strip()],
        "advice": (
            "Try the 5-4-3-2-1 grounding technique."
            if intensity <= 5
            else "Consider box breathing + reach out to someone you trust."
        ),
    }
    return json.dumps({"status": "logged", "entry": entry}, indent=2)


# ── Tool 4: Crisis resources ──────────────────────────────────────────────────
@mcp.tool()
def get_crisis_resources(country: str = "US") -> str:
    """Return emergency mental health crisis resources.

    Args:
        country: ISO country code (US, UK, CA, AU, IN).

    Returns:
        JSON with hotlines and online resources for the given country.
    """
    resources = {
        "US": {
            "hotlines": [
                {"name": "988 Suicide & Crisis Lifeline", "number": "988", "available": "24/7"},
                {"name": "Crisis Text Line", "number": "Text HOME to 741741", "available": "24/7"},
                {"name": "NAMI Helpline", "number": "1-800-950-6264", "available": "Mon-Fri 10am-10pm ET"},
            ],
            "online": ["https://988lifeline.org", "https://www.crisistextline.org"],
        },
        "UK": {
            "hotlines": [
                {"name": "Samaritans", "number": "116 123", "available": "24/7"},
                {"name": "Crisis Text Line UK", "number": "Text SHOUT to 85258", "available": "24/7"},
            ],
            "online": ["https://www.samaritans.org"],
        },
        "CA": {
            "hotlines": [
                {"name": "Crisis Services Canada", "number": "1-833-456-4566", "available": "24/7"},
                {"name": "Kids Help Phone", "number": "1-800-668-6868", "available": "24/7"},
            ],
            "online": ["https://www.crisisservicescanada.ca"],
        },
        "AU": {
            "hotlines": [
                {"name": "Lifeline", "number": "13 11 14", "available": "24/7"},
                {"name": "Beyond Blue", "number": "1300 22 4636", "available": "24/7"},
            ],
            "online": ["https://www.lifeline.org.au"],
        },
        "IN": {
            "hotlines": [
                {"name": "iCall", "number": "9152987821", "available": "Mon-Sat 8am-10pm IST"},
                {"name": "Vandrevala Foundation", "number": "1860-2662-345", "available": "24/7"},
            ],
            "online": ["https://icallhelpline.org"],
        },
    }
    result = resources.get(country.upper(), resources["US"])
    result["message"] = (
        "You are not alone. Please reach out — trained counselors are ready to help."
    )
    return json.dumps(result, indent=2)


# ── Tool 5: Anxiety self-assessment ──────────────────────────────────────────
@mcp.tool()
def assess_anxiety_level(
    heart_racing: bool = False,
    breathing_fast: bool = False,
    feeling_dizzy: bool = False,
    extreme_fear: bool = False,
    chest_tightness: bool = False,
    shaking: bool = False,
    numbness: bool = False,
) -> str:
    """Assess anxiety severity from reported symptoms.

    Args:
        heart_racing: True if the user reports racing heart.
        breathing_fast: True if the user reports fast/shallow breathing.
        feeling_dizzy: True if the user reports dizziness.
        extreme_fear: True if the user reports feeling extreme fear.
        chest_tightness: True if the user reports chest tightness.
        shaking: True if the user reports trembling/shaking.
        numbness: True if the user reports numbness or tingling.

    Returns:
        JSON with severity level and recommended intervention.
    """
    panic_indicators = [heart_racing, breathing_fast, feeling_dizzy, extreme_fear, chest_tightness]
    somatic_indicators = [shaking, numbness]

    panic_count = sum(1 for s in panic_indicators if s)
    somatic_count = sum(1 for s in somatic_indicators if s)
    total = panic_count + somatic_count

    if total == 0:
        severity = "none"
        intervention = "grounding"
        message = "No significant symptoms detected. Practice daily mindfulness to stay resilient."
    elif total <= 2:
        severity = "mild"
        intervention = "grounding"
        message = "Mild anxiety. A grounding exercise should help you reset."
    elif total <= 4:
        severity = "moderate"
        intervention = "breathing"
        message = "Moderate anxiety. Let's focus on your breathing to calm your nervous system."
    else:
        severity = "severe"
        intervention = "crisis"
        message = "High anxiety / possible panic attack. I'm here with you. Let's get you support."

    return json.dumps({
        "severity": severity,
        "intervention": intervention,
        "message": message,
        "symptom_count": total,
    }, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
