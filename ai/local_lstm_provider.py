"""
ai/local_lstm_provider.py

Pure local provider -- zero external API calls. Uses ONLY the local LSTM
model to return emotion probabilities. No reply text is generated here
(HybridProvider handles reply text, either via Gemini or the local
template bank) -- this exists as a diagnostic / offline tool for when you
want to sanity-check the model's scores in isolation, with nothing else
in the loop.

Not part of the default chain in ai_setup.py.
"""

from .base import AIProvider, AIProviderError, ChatTurn, StructuredReply
from .lstm_provider import EmotionClassifier


class LocalLSTMProvider(AIProvider):
    name = "local_lstm_only"

    def __init__(self, classifier: EmotionClassifier):
        self.classifier = classifier

    async def generate_reply(self, user_message: str, history: list[ChatTurn]) -> StructuredReply:
        try:
            # EmotionClassifier.classify() already returns 0-100 scores in
            # Senti's canonical EMOTION_CLASSES order -- keep that
            # convention here so this provider's output is interchangeable
            # with every other provider's (HybridProvider, GeminiProvider,
            # Heuristic all return 0-100 too). Do NOT rescale to 0-1 here,
            # or emotion_scores in the DB/API response will be inconsistent
            # depending on which provider happened to answer.
            emotions = await self.classifier.classify(user_message)
        except Exception as e:  # noqa: BLE001
            raise AIProviderError(f"Local LSTM classification failed: {e}") from e

        return StructuredReply(
            reply="Emotion classification complete. (local_lstm_only provider does not generate reply text)",
            emotions=emotions,
        )

