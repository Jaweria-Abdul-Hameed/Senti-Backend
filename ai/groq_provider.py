"""
ai/groq_provider.py
Direct-Groq fallback: used only if HybridProvider's LSTM step itself failed
(e.g. model/tokenizer missing at startup). Asks Groq to both estimate
emotions AND write the reply in one shot, since there's no local
classifier to supply real scores in this path.

Groq's Chat Completions API is OpenAI-compatible; the official `groq`
Python package wraps it. Using AsyncGroq (not the sync Groq client) so
this doesn't block the event loop inside an `async def`.
"""

import json
import os

from groq import AsyncGroq

from .base import AIProvider, AIProviderError, ChatTurn, StructuredReply, warn_if_key_looks_wrong

SYSTEM_PROMPT = """You are SENTI, an empathetic AI well-being coach. Analyze the user's input, generate a highly supportive, stigma-free, and compassionate reply.
Also estimate probability scores (0 to 100) for these 6 primary emotions representing the user's conversational state:
- Fear
- Sadness
- Anger
- Joy
- Love
- Surprise

Return your response strictly in the following JSON format:
{
  "reply": "Your supportive message text goes here.",
  "emotions": {
    "Fear": 10,
    "Sadness": 40,
    "Anger": 0,
    "Joy": 10,
    "Love": 0,
    "Surprise": 0
  }
}
Ensure you ONLY return valid JSON. Do not include any markdown format or backticks."""


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.timeout = timeout
        warn_if_key_looks_wrong(self.api_key, self.name)

    def _has_real_key(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("MY_") and self.api_key != "placeholder"

    async def generate_reply(self, user_message: str, history: list[ChatTurn]) -> StructuredReply:
        if not self._has_real_key():
            raise AIProviderError("No Groq API key configured")

        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        prompt_lines = [f"{turn.sender.upper()}: {turn.text}" for turn in history[-5:]]
        prompt_lines.append(f"USER: {user_message}")
        full_prompt = "\n".join(prompt_lines)

        try:
            client = AsyncGroq(api_key=self.api_key, timeout=self.timeout)
            completion = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            text = completion.choices[0].message.content
            cleaned = text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            return StructuredReply(reply=parsed["reply"], emotions=parsed["emotions"])
        except Exception as e:
            raise AIProviderError(f"Groq request failed: {e}") from e