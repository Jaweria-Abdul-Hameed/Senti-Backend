"""
ai/distress_agent.py

Replaces the old flat check ("is Sadness/Anger/Fear individually > 89?")
with a two-step ReAct-style (Reason + Act) escalation decision, per
workflow.md §3.1's note that the WRI/distress math should grow into
something richer than a bare number.

Why not just keep tuning the number?
-------------------------------------------------------------------------
A softmax percentage from a 6-class LSTM classifier isn't a validated
clinical instrument (unlike, say, a PHQ-9 score) — there's no published
literature that says "89% is the correct cutoff" for a classifier like
this one, and it would be dishonest to claim otherwise. What the crisis-
detection literature does support is:
  - favor high sensitivity over precision — missing a real crisis is far
    costlier than a false alarm, so production systems often run at
    surprisingly *aggressive* probability thresholds; the mental-health
    crisis-chat NLP system in Swaminathan et al. 2023 (npj Digital
    Medicine) used a probability threshold of 0.01, not 0.5 or higher.
  - use tiered risk stratification with a human-in-the-loop-informed cost
    ratio (crisis / high / moderate / low), not a single binary cutoff.
  - reserve the most restrictive/attention-grabbing action (full crisis
    mode, handoff, session termination) for the clearest cases, and use
    a lighter-touch response for ambiguous ones (see the "emergency mode"
    proposal in recent LLM-based crisis-risk-detection work).

So instead of trying to defend one magic number, this module uses the
numeric score two ways:
  1. As a cheap triage GATE (`SCREEN_GATE`) that decides whether it's even
     worth spending an LLM call reasoning about escalation. Below the
     gate, we already know this isn't a crisis-shaped message.
  2. Above the gate, an LLM reasons over the *whole* emotion distribution
     (not just one class in isolation) and decides whether this looks
     like it's exceeded ordinary conversational support and needs to be
     routed to crisis resources — this is the "89% fear/anger with the
     rest thin" pattern in the product brief: a concentrated, dominant
     signal is a stronger indicator than the raw percentage alone.

SCREEN_GATE stays at the same 89 the original Kotlin code used, but its
role changed: it's no longer the decision, just the "is it worth asking"
threshold before the reasoning step. If the LLM call fails for any reason
(no key, network, bad output), we fall back to the raw >=89 check so a
Groq outage can never silently turn off the safety net.
"""

import json
import logging
import os

from groq import AsyncGroq

from .base import EMOTION_CLASSES, warn_if_key_looks_wrong

logger = logging.getLogger("senti.ai.distress")

# Cheap pre-filter only — see module docstring. Not itself a diagnostic cutoff.
SCREEN_GATE = 89

REASONING_SYSTEM_PROMPT = """You are a triage reasoning module inside a mental well-being chat app called SENTI. You do NOT write user-facing replies — your only job is to decide whether a user's message has exceeded what a supportive chatbot conversation can safely handle, and should instead be routed to crisis support resources (a "Get Support" popup showing nearby help and hotlines).

You will be given:
- The user's latest message
- An emotion classifier's output: percentage scores (0-100, roughly summing to 100) across Fear, Sadness, Anger, Joy, Love, Surprise

Reason step by step (your "thought"), then decide on one action:
- "continue_conversation": within the scope of an empathetic chat companion, even if the person is upset, sad, or venting.
- "escalate_to_crisis_support": the message and/or the emotional signal indicates a level of acute distress (e.g. dominant Fear/Sadness/Anger with little else present, self-harm or suicidal language, expressions of hopelessness or being unsafe) that is beyond conversational support and warrants surfacing real-world crisis resources.

Consider the SHAPE of the distribution, not just one number in isolation — e.g. a single emotion at ~89% with everything else near-zero indicates a much more acute, singular state than the same number alongside other significant emotions. Also weigh the actual message content; a classifier score alone is never fully reliable.

Bias toward escalating when genuinely unsure — a false alarm just shows someone a "would you like support?" popup they can dismiss, but a missed crisis has real cost.

Return ONLY valid JSON, no markdown, in exactly this shape:
{"thought": "one or two sentences of reasoning", "action": "continue_conversation" or "escalate_to_crisis_support", "confidence": 0-100}"""


def _has_real_key(api_key: str) -> bool:
    return bool(api_key) and not api_key.startswith("MY_") and api_key != "placeholder"


def _numeric_fallback(emotions: dict) -> bool:
    """The original flat check — used only if the reasoning step can't run at all."""
    return any(emotions.get(k, 0) > SCREEN_GATE for k in ("Sadness", "Anger", "Fear"))


async def evaluate_distress(emotions: dict, user_message: str) -> tuple[bool, str]:
    """
    Returns (should_escalate, reasoning_note). reasoning_note is for server-side
    logging/debugging only — never surfaced to the client (constraints.md-style
    privacy: don't ship raw model reasoning about someone's mental state to
    their own device where a screenshot could leak it out of context).
    """
    # 1. Cheap gate: don't spend an LLM call on messages nowhere near this territory.
    if not any(emotions.get(k, 0) > SCREEN_GATE - 20 for k in ("Sadness", "Anger", "Fear")):
        return False, "below screening gate — not evaluated"

    api_key = os.getenv("GROQ_API_KEY", "")
    warn_if_key_looks_wrong(api_key, "distress_agent")
    if not _has_real_key(api_key):
        escalate = _numeric_fallback(emotions)
        return escalate, "no Groq key configured — used numeric fallback"

    emotion_context = ", ".join(f"{k}: {emotions.get(k, 0)}" for k in EMOTION_CLASSES)
    user_prompt = f'User message: "{user_message}"\nEmotion classifier output: {emotion_context}'

    try:
        client = AsyncGroq(api_key=api_key, timeout=15.0)
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        completion = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": REASONING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,  # low — this is a safety decision, not a creative one
        )
        text = completion.choices[0].message.content
        cleaned = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)
        action = parsed.get("action")
        thought = parsed.get("thought", "")

        if action not in ("continue_conversation", "escalate_to_crisis_support"):
            raise ValueError(f"Unexpected action from reasoning step: {action!r}")

        escalate = action == "escalate_to_crisis_support"
        logger.info("Distress reasoning: action=%s confidence=%s thought=%s", action, parsed.get("confidence"), thought)
        return escalate, thought

    except Exception as e:  # noqa: BLE001 — any failure here falls back, never crashes the chat request
        logger.warning("Distress reasoning step failed (%s) — using numeric fallback.", e)
        return _numeric_fallback(emotions), f"reasoning step failed ({e}) — used numeric fallback"
