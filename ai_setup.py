"""
This is the single wiring point for SENTI's "brain."

Chain priority (first one that succeeds wins -- see ai/engine.py):

  1. HybridProvider           -- local LSTM scores the message (Fear/Sadness/
                                  Anger/Joy/Love/Surprise, 0-100). Those real
                                  scores get used no matter what happens next:
                                    - if Groq is reachable, Groq writes the
                                      reply text around them (the "system
                                      prompt, not fine-tuning" approach -- no
                                      model weights change, Groq just gets
                                      told what the classifier already found).
                                    - if Groq fails for any reason (missing/
                                      bad key, rate limit, network), the
                                      reply text is generated locally from
                                      the same template bank
                                      HeuristicFallbackProvider uses -- but
                                      the emotion scores are still the real
                                      LSTM output, never discarded.
                                  This only fails (and falls through to #2)
                                  if the LSTM classification step itself throws.
  2. GroqProvider             -- only reached if the LSTM model/tokenizer
                                  failed to load at startup. Asks Groq to
                                  both estimate emotions AND write the reply
                                  in one shot, since there's no local
                                  classifier available in this path.
  3. HeuristicFallbackProvider -- last resort if both of the above fail
                                  (e.g. LSTM didn't load AND Groq is also
                                  unreachable). Pure local keyword-based
                                  fallback. It never raises, so ChatEngine
                                  always has something to return.

To add a new brain later:
    from ai.my_rnn_provider import MyRnnProvider
    providers = [MyRnnProvider(), HybridProvider(classifier), GroqProvider(), HeuristicFallbackProvider()]
Nothing in routers/chat.py, database.py, or the Android client needs to change for that swap.
"""

from functools import lru_cache
import logging
from pathlib import Path

from ai import (
    ChatEngine,
    GroqProvider,
    HeuristicFallbackProvider,
    HybridProvider,
)
from ai.lstm_provider import EmotionClassifier

logger = logging.getLogger(__name__)

# Root directory where senti_emotion_lstm.keras and senti_tokenizer.pkl live.
BASE_DIR = Path(__file__).resolve().parent


@lru_cache
def get_chat_engine() -> ChatEngine:
    providers = []

    # 1. Hybrid: real LSTM emotion scores every time, Groq for reply text
    #    when available, local template reply when it isn't.
    try:
        model_path = BASE_DIR / "senti_emotion_lstm.keras"
        tokenizer_path = BASE_DIR / "senti_tokenizer.pkl"

        classifier = EmotionClassifier(
            model_path=str(model_path),
            tokenizer_path=str(tokenizer_path),
        )
        providers.append(HybridProvider(classifier))
        logger.info("HybridProvider initialized (LSTM model + tokenizer loaded).")
    except Exception as err:
        logger.warning("Skipping HybridProvider -- LSTM model/tokenizer failed to load: %s", err)

    # 2. Groq direct fallback (self-estimates emotions if LSTM is unavailable).
    providers.append(GroqProvider())

    # 3. Last-resort local fallback -- never fails.
    providers.append(HeuristicFallbackProvider())

    logger.info("Chat engine provider chain: %s", [p.name for p in providers])
    return ChatEngine(providers)