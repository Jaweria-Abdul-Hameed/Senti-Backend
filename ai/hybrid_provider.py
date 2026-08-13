"""
ai/hybrid_provider.py

Two-step flow, but the two steps are independent of each other:
    1. EmotionClassifier (LSTM) scores the message -> emotion dict.
       This is the part that MUST succeed for HybridProvider to be
       considered "working" — if this fails, we raise AIProviderError and
       let ChatEngine fall through to GroqProvider / HeuristicFallback.
    2. Groq writes the reply text using those scores as context.
       If this step fails (bad key, rate limit, network, whatever), we
       don't discard the LSTM's output — we keep the real emotion scores
       and generate the reply text locally instead, via the same template
       bank HeuristicFallbackProvider uses. So a Groq outage degrades
       *only* the reply wording, never the emotion scores.

This means the real LSTM model is used on every request as long as it
loaded successfully at startup, regardless of whether Groq is reachable.

Uses AsyncGroq (not the sync Groq client) so this doesn't block the event
loop inside an `async def`.
"""

import json
import logging
import os

from groq import AsyncGroq

from .base import AIProvider, AIProviderError, ChatTurn, StructuredReply, warn_if_key_looks_wrong
from .heuristic_provider import pick_reply_for_emotions
from .lstm_provider import EmotionClassifier

logger = logging.getLogger("senti.ai.hybrid")

SYSTEM_PROMPT_TEMPLATE = """You are SENTI, an empathetic AI well-being coach.
A classifier has already analyzed the user's message and detected this emotional signal (0-100 scale, independent per emotion):
{emotion_context}

Important — read this carefully: the classifier was only trained on six emotions (Sadness, Joy, Love, Anger, Fear, Surprise). It has no "neutral" option, so for a mundane, factual, or emotionally flat message (e.g. "what time is it", "I went to the store today", small talk) it is still forced to spread probability across those six labels — it will sometimes assign a moderate or even high score to one of them even though the message doesn't actually carry that emotion. Do not treat these scores as ground truth.

Read the user's actual message and the conversation history yourself, then decide:
- If the message genuinely and clearly carries one of the six emotions, respond to that emotion — use the scores as supporting signal, not the sole basis.
- If the message reads as neutral, factual, a simple question, or otherwise emotionally flat — even if the classifier assigned a real score to one of the six labels (like one for each -- or one specific one has a very high rating) — treat it as neutral. Reply in a calm, natural, conversational tone. Do not invent or project an emotion onto the user that isn't actually there just because the classifier suggested one.
- You have full authority to override the classifier's label whenever your own reading of the text disagrees with it. Trust your own judgment of the message over the raw numbers.

Write a supportive, stigma-free, compassionate reply that responds to what the user actually said and how they actually seem to feel — not a hedge, and not a validation of a mislabeled emotion.

Return your response strictly in this JSON format:
{{
  "reply": "Your supportive message text goes here."
}}
Ensure you ONLY return valid JSON. Do not include any markdown format or backticks."""


class HybridProvider(AIProvider):
    name = "hybrid_lstm_groq"

    def __init__(self, classifier: EmotionClassifier, api_key: str | None = None, timeout: float = 30.0):
        self.classifier = classifier
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.timeout = timeout
        warn_if_key_looks_wrong(self.api_key, self.name)

    def _has_real_key(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("MY_") and self.api_key != "placeholder"

    async def generate_reply(self, user_message: str, history: list[ChatTurn]) -> StructuredReply:
        # Step 1 — LSTM emotion scoring. This is the part that must succeed
        # for HybridProvider to count as "working" at all.
        try:
            emotions = await self.classifier.classify(user_message)
        except Exception as e:  # noqa: BLE001
            raise AIProviderError(f"Emotion classification failed: {e}") from e

        # Step 2 — Groq writes the reply text around those scores. Any
        # failure here (no key, bad key, rate limit, network) falls back
        # to a local template reply for the SAME real scores instead of
        # raising — the LSTM's output is never thrown away because of a
        # Groq-side problem.
        if not self._has_real_key():
            logger.warning("No Groq API key configured — using local template reply for LSTM scores.")
            return StructuredReply(
                reply=pick_reply_for_emotions(emotions),
                emotions=emotions,
                provider_used="hybrid_lstm_local_template",
            )

        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        emotion_context = ", ".join(f"{k}: {v}" for k, v in emotions.items())
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(emotion_context=emotion_context)

        prompt_lines = [f"{turn.sender.upper()}: {turn.text}" for turn in history[-5:]]
        prompt_lines.append(f"USER: {user_message}")
        full_prompt = "\n".join(prompt_lines)

        try:
            client = AsyncGroq(api_key=self.api_key, timeout=self.timeout)
            completion = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            text = completion.choices[0].message.content
            cleaned = text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            reply_text = parsed["reply"]
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Groq reply generation failed (%s) — falling back to a local template reply "
                "for the LSTM's real emotion scores instead of discarding them.",
                e,
            )
            return StructuredReply(
                reply=pick_reply_for_emotions(emotions),
                emotions=emotions,
                provider_used="hybrid_lstm_local_template",
            )

        return StructuredReply(reply=reply_text, emotions=emotions, provider_used="hybrid_lstm_groq")