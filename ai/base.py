"""
The plug-and-play seam.

Every "brain" SENTI can talk to — the keyword heuristic today, Gemini today,
and whatever you swap in later (a fine-tuned LLM, your own RNN classifier,
a LangGraph ReAct agent) — implements this one interface. Nothing else in
the backend needs to know or care which provider answered the question.

To add a new brain later:
    1. Create a new file in ai/, subclass AIProvider, implement generate_reply().
    2. Add one line to the provider chain in ai_setup.py that builds ChatEngine.
That's the entire integration surface — routers/chat.py never changes.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("senti.ai")


def looks_like_plausible_api_key(key: str, prefixes: tuple[str, ...], min_len: int = 20) -> bool:
    """
    Cheap sanity check, not a real validation — the only way to actually
    confirm a key works is to call the API. This just catches the "pasted
    the wrong thing entirely" class of bug (random tokens, placeholders,
    empty strings, a key copied from the wrong provider) before it burns
    a request. Generic across providers -- pass the prefix(es) that
    provider's real keys start with, e.g. ("gsk_",) for Groq.
    """
    return bool(key) and key.startswith(prefixes) and len(key) >= min_len


def warn_if_key_looks_wrong(
    key: str,
    provider_name: str,
    prefixes: tuple[str, ...] = ("gsk_",),
    hint: str = "a Groq key (starts with 'gsk_', from https://console.groq.com/keys)",
) -> None:
    """
    Defaults to Groq's key shape since that's SENTI's current provider.
    Callers wrapping a different provider (e.g. a future re-add of Gemini)
    should pass their own `prefixes` / `hint`.
    """
    if key and not looks_like_plausible_api_key(key, prefixes):
        logger.warning(
            "[%s] API key doesn't look like %s. Got something starting "
            "with %r instead.",
            provider_name,
            hint,
            key[:6] + "..." if len(key) > 6 else key,
        )


# The 6 emotion classes tracked everywhere in SENTI (matches the Kotlin app).
EMOTION_CLASSES = ["Fear", "Sadness", "Anger", "Joy", "Love", "Surprise"]


@dataclass
class ChatTurn:
    """One turn of prior conversation, passed in as context."""
    sender: str  # "user" or "senti"
    text: str


@dataclass
class StructuredReply:
    """What every provider must hand back, regardless of how it got there."""
    reply: str
    emotions: dict = field(default_factory=lambda: {k: 0 for k in EMOTION_CLASSES})
    # Optional, finer-grained label than the provider's own `.name` — e.g.
    # HybridProvider sets this to say whether the reply text itself came
    # from Gemini or from the local template, even though the emotion
    # scores came from the LSTM either way. ChatEngine prefers this over
    # provider.name when it's set. Leave unset for providers that don't
    # need the distinction (Gemini-only, heuristic-only, etc).
    provider_used: Optional[str] = None


class AIProviderError(Exception):
    """Raised when a provider fails to produce a reply — triggers fallback to the next one in the chain."""


class AIProvider(ABC):
    """Base class for any SENTI response engine."""

    name: str = "base"

    @abstractmethod
    async def generate_reply(self, user_message: str, history: list[ChatTurn]) -> StructuredReply:
        """
        user_message: the newest thing the user typed.
        history: up to the last 5 turns of conversation, oldest first
                 (this is the same sliding-window contract described in workflow.md §5).

        Must raise AIProviderError (or let any exception propagate) on failure —
        ChatEngine catches it and moves on to the next provider in the chain.
        """
        raise NotImplementedError