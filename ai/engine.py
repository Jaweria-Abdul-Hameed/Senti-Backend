"""
ChatEngine — the orchestrator that used to be scattered inline inside
SentiRepository.getSentiReply(). All it does is walk a list of AIProvider
instances in order and return the first one that succeeds, logging (never
crashing) on every failure along the way.

Current chain (see ai_setup.py): [HybridProvider, GeminiProvider, HeuristicFallbackProvider]

Later, this is where a real agent goes. Three ways to grow it, in order of
how much you want to change:

  1. New leaf provider (easiest): write ai/my_rnn_provider.py implementing
     AIProvider, then in ai_setup.py add it to the provider list.
     Nothing else changes — not the router, not the DB layer, not Android.

  2. Real ReAct / LangGraph agent (workflow.md §3): write a provider whose
     generate_reply() invokes a LangGraph graph instead of a single model
     call (it can still call query_nearby_clinics() as a tool node internally).
     It's still just one AIProvider from ChatEngine's point of view.

  3. Swap the WRI/distress math (workflow.md §3.1): that logic lives in
     `evaluate_distress()` below, deliberately kept out of any single
     provider so it applies no matter which brain produced the reply.
"""

import logging

from .base import AIProvider, AIProviderError, ChatTurn, StructuredReply

logger = logging.getLogger("senti.ai_engine")

# Matches the > 89 threshold from SentiViewModel.sendMessage() in the original Kotlin app.
DISTRESS_THRESHOLD = 89


class ChatEngine:
    def __init__(self, providers: list[AIProvider]):
        if not providers:
            raise ValueError("ChatEngine needs at least one provider")
        self.providers = providers

    async def get_reply(self, user_message: str, history: list[ChatTurn]) -> tuple[StructuredReply, str]:
        """Returns (reply, name_of_provider_that_answered).

        The reported name prefers reply.provider_used when a provider sets
        it (e.g. HybridProvider distinguishing "LSTM scores + Gemini reply"
        from "LSTM scores + local template reply") — falling back to the
        provider's static .name otherwise. This is read off the returned
        StructuredReply object, not shared instance state, so it's safe
        under concurrent requests even though providers are reused
        singletons (see ai_setup.py's @lru_cache).
        """
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                reply = await provider.generate_reply(user_message, history)
                name = reply.provider_used or provider.name
                return reply, name
            except Exception as e:  # noqa: BLE001 — any provider failure just moves to the next one
                last_error = e
                logger.warning("AI provider '%s' failed, trying next: %s", provider.name, e)
                continue
        # Should be unreachable in practice since HeuristicFallbackProvider never raises,
        # but fail loudly rather than silently if every provider in the chain does.
        raise AIProviderError(f"All AI providers in the chain failed. Last error: {last_error}")


def evaluate_distress(emotions: dict) -> bool:
    """
    DEPRECATED — this is the old flat check (Sadness/Anger/Fear individually
    > 89) that only looked at one class in isolation with no reasoning over
    the rest of the distribution or the message itself.

    Superseded by ai.distress_agent.evaluate_distress(emotions, user_message),
    an async ReAct-style (reason, then act) escalation decision that
    considers the whole emotion distribution and the message content, with
    this same >89 check kept only as its last-resort fallback if the
    reasoning call itself fails. routers/chat.py calls that version now.
    Left here only so nothing that imports this old name breaks.
    """
    return any(emotions.get(k, 0) > 89 for k in ("Sadness", "Anger", "Fear"))