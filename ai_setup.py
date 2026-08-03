# # """
# # This is the single wiring point for SENTI's "brain."
# #
# # Today the chain is [GeminiProvider, HeuristicFallbackProvider] — same
# # priority order as the old SentiRepository.getSentiReply(): try Gemini,
# # fall back to the local heuristic if it fails or no key is configured.
# #
# # When you're ready to plug in something new:
# #
# #     from ai import ChatEngine, GeminiProvider, HeuristicFallbackProvider
# #     from ai.my_rnn_provider import MyRnnProvider   # <-- your new file
# #
# #     _chat_engine = ChatEngine([
# #         MyRnnProvider(),            # tried first
# #         GeminiProvider(),           # falls back to this
# #         HeuristicFallbackProvider() # last-resort, never fails
# #     ])
# #
# # Nothing in routers/chat.py, database.py, or the Android client needs to
# # change for that swap — this is the entire integration point.
# # """
# #
# # from functools import lru_cache
# #
# # from ai import ChatEngine, GeminiProvider, HeuristicFallbackProvider
#
# """
# This is the single wiring point for SENTI's "brain."
#
# Chain Priority:
# 1. HybridProvider (LSTM Emotion Classifier + Gemini Context)
# 2. GeminiProvider (Direct Gemini API fallback)
# 3. HeuristicFallbackProvider (Last-resort local fallback)
# """
#
# """
# This is the single wiring point for SENTI's "brain."
#
# Chain Priority:
# 1. HybridProvider (LSTM Emotion Classifier + Gemini Context)
# 2. GeminiProvider (Direct Gemini API fallback)
# 3. HeuristicFallbackProvider (Last-resort local fallback)
# """
#
# # from functools import lru_cache
# # import logging
# # from pathlib import Path
# #
# # from ai import (
# #     ChatEngine,
# #     GeminiProvider,
# #     HeuristicFallbackProvider,
# #     HybridProvider,
# # )
# # from ai.lstm_provider import EmotionClassifier
# #
# # logger = logging.getLogger(__name__)
# #
# # # Root directory where senti_emotion_lstm.keras and senti_tokenizer.pkl reside
# # BASE_DIR = Path(__file__).resolve().parent
# #
# #
# # @lru_cache
# # def get_chat_engine() -> ChatEngine:
# #     providers = []
# #
# #     # 1. Attempt to load Hybrid Provider (LSTM + Gemini)
# #     try:
# #         model_path = BASE_DIR / "senti_emotion_lstm.keras"
# #         tokenizer_path = BASE_DIR / "senti_tokenizer.pkl"
# #
# #         classifier = EmotionClassifier(
# #             model_path=str(model_path),
# #             tokenizer_path=str(tokenizer_path),
# #         )
# #         providers.append(HybridProvider(classifier))
# #         logger.info("HybridProvider initialized successfully with LSTM model.")
# #     except Exception as err:
# #         logger.warning(
# #             f"Skipping HybridProvider due to missing or invalid model artifacts: {err}"
# #         )
# #
# #     # 2. Gemini Direct Fallback
# #     providers.append(GeminiProvider())
# #
# #     # 3. Last-Resort Safety Fallback
# #     providers.append(HeuristicFallbackProvider())
# #
# #     return ChatEngine(providers)
# #
# # @lru_cache
# # def get_chat_engine() -> ChatEngine:
# #     return ChatEngine([
# #         GeminiProvider(),
# #         HeuristicFallbackProvider(),
# #     ])
#
#
# # from functools import lru_cache
# # import logging
# # from pathlib import Path
# #
# # from ai import (
# #     ChatEngine,
# #     HeuristicFallbackProvider,
# #     LocalLSTMProvider,
# # )
# # from ai.lstm_provider import EmotionClassifier
# #
# # logger = logging.getLogger(__name__)
# #
# # BASE_DIR = Path(__file__).resolve().parent
# #
# #
# # @lru_cache
# # def get_chat_engine() -> ChatEngine:
# #     providers = []
# #
# #     # 1. Local LSTM Provider (Runs fully locally)
# #     try:
# #         model_path = BASE_DIR / "senti_emotion_lstm.keras"
# #         tokenizer_path = BASE_DIR / "senti_tokenizer.pkl"
# #
# #         classifier = EmotionClassifier(
# #             model_path=str(model_path),
# #             tokenizer_path=str(tokenizer_path),
# #         )
# #         providers.append(LocalLSTMProvider(classifier))
# #         logger.info("LocalLSTMProvider initialized successfully with LSTM model.")
# #     except Exception as err:
# #         logger.warning(
# #             f"Skipping LocalLSTMProvider due to missing/invalid model artifacts: {err}"
# #         )
# #
# #     # 2. Safety Fallback (If Keras model fails to load)
# #     providers.append(HeuristicFallbackProvider())
# #
# #     return ChatEngine(providers)
#
# # """
# # This is the single wiring point for SENTI's "brain."
# #
# # Chain priority (first one that succeeds wins -- see ai/engine.py):
# #
# #   1. HybridProvider          -- local LSTM scores the message (Fear/Sadness/
# #                                  Anger/Joy/Love/Surprise, 0-100), those scores
# #                                  get dropped into a system prompt, and Gemini
# #                                  writes the reply text around them. This is
# #                                  the "system prompt, not fine-tuning" approach
# #                                  -- no model weights change, Gemini just gets
# #                                  told what the classifier already found.
# #   2. GeminiProvider          -- if the LSTM model failed to load (missing
# #                                  .keras/.pkl files) OR its own classification
# #                                  call throws, fall back to asking Gemini to
# #                                  both estimate emotions AND write the reply
# #                                  in one shot.
# #   3. HeuristicFallbackProvider -- if Gemini is unreachable/misconfigured too
# #                                  (e.g. bad/missing GEMINI_API_KEY -> 403),
# #                                  this is the local keyword-based fallback.
# #                                  It never raises, so ChatEngine always has
# #                                  something to return.
# #
# # To add a new brain later:
# #     from ai.my_rnn_provider import MyRnnProvider
# #     providers = [MyRnnProvider(), HybridProvider(classifier), GeminiProvider(), HeuristicFallbackProvider()]
# # Nothing in routers/chat.py, database.py, or the Android client needs to change for that swap.
# # """
# #
# # from functools import lru_cache
# # import logging
# # from pathlib import Path
# #
# # from ai import (
# #     ChatEngine,
# #     GeminiProvider,
# #     HeuristicFallbackProvider,
# #     HybridProvider,
# # )
# # from ai.lstm_provider import EmotionClassifier
# #
# # logger = logging.getLogger(__name__)
# #
# # # Root directory where senti_emotion_lstm.keras and senti_tokenizer.pkl live.
# # BASE_DIR = Path(__file__).resolve().parent
# #
# #
# # @lru_cache
# # def get_chat_engine() -> ChatEngine:
# #     providers = []
# #
# #     # 1. Hybrid: LSTM emotion scores + Gemini reply generation.
# #     try:
# #         model_path = BASE_DIR / "senti_emotion_lstm.keras"
# #         tokenizer_path = BASE_DIR / "senti_tokenizer.pkl"
# #
# #         classifier = EmotionClassifier(
# #             model_path=str(model_path),
# #             tokenizer_path=str(tokenizer_path),
# #         )
# #         providers.append(HybridProvider(classifier))
# #         logger.info("HybridProvider initialized (LSTM model + tokenizer loaded).")
# #     except Exception as err:
# #         logger.warning("Skipping HybridProvider -- LSTM model/tokenizer failed to load: %s", err)
# #
# #     # 2. Gemini direct fallback (self-estimates emotions if LSTM is unavailable).
# #     providers.append(GeminiProvider())
# #
# #     # 3. Last-resort local fallback -- never fails.
# #     providers.append(HeuristicFallbackProvider())
# #
# #     logger.info("Chat engine provider chain: %s", [p.name for p in providers])
# #     return ChatEngine(providers)
#
#
# """
# This is the single wiring point for SENTI's "brain."
#
# Chain priority (first one that succeeds wins -- see ai/engine.py):
#
#   1. HybridProvider           -- local LSTM scores the message (Fear/Sadness/
#                                   Anger/Joy/Love/Surprise, 0-100). Those real
#                                   scores get used no matter what happens next:
#                                     - if Gemini is reachable, Gemini writes the
#                                       reply text around them (the "system
#                                       prompt, not fine-tuning" approach -- no
#                                       model weights change, Gemini just gets
#                                       told what the classifier already found).
#                                     - if Gemini fails for any reason (missing/
#                                       bad key, 403, quota, network), the reply
#                                       text is generated locally from the same
#                                       template bank HeuristicFallbackProvider
#                                       uses -- but the emotion scores are still
#                                       the real LSTM output, never discarded.
#                                   This only fails (and falls through to #2)
#                                   if the LSTM classification step itself throws.
#   2. GeminiProvider           -- only reached if the LSTM model/tokenizer
#                                   failed to load at startup. Asks Gemini to
#                                   both estimate emotions AND write the reply
#                                   in one shot, since there's no local
#                                   classifier available in this path.
#   3. HeuristicFallbackProvider -- last resort if both of the above fail
#                                   (e.g. LSTM didn't load AND Gemini is also
#                                   unreachable). Pure local keyword-based
#                                   fallback. It never raises, so ChatEngine
#                                   always has something to return.
#
# To add a new brain later:
#     from ai.my_rnn_provider import MyRnnProvider
#     providers = [MyRnnProvider(), HybridProvider(classifier), GeminiProvider(), HeuristicFallbackProvider()]
# Nothing in routers/chat.py, database.py, or the Android client needs to change for that swap.
# """
#
# from functools import lru_cache
# import logging
# from pathlib import Path
#
# from ai import (
#     ChatEngine,
#     GeminiProvider,
#     HeuristicFallbackProvider,
#     HybridProvider,
# )
# from ai.lstm_provider import EmotionClassifier
#
# logger = logging.getLogger(__name__)
#
# # Root directory where senti_emotion_lstm.keras and senti_tokenizer.pkl live.
# BASE_DIR = Path(__file__).resolve().parent
#
#
# @lru_cache
# def get_chat_engine() -> ChatEngine:
#     providers = []
#
#     # 1. Hybrid: real LSTM emotion scores every time, Gemini for reply text
#     #    when available, local template reply when it isn't.
#     try:
#         model_path = BASE_DIR / "senti_emotion_lstm.keras"
#         tokenizer_path = BASE_DIR / "senti_tokenizer.pkl"
#
#         classifier = EmotionClassifier(
#             model_path=str(model_path),
#             tokenizer_path=str(tokenizer_path),
#         )
#         providers.append(HybridProvider(classifier))
#         logger.info("HybridProvider initialized (LSTM model + tokenizer loaded).")
#     except Exception as err:
#         logger.warning("Skipping HybridProvider -- LSTM model/tokenizer failed to load: %s", err)
#
#     # 2. Gemini direct fallback (self-estimates emotions if LSTM is unavailable).
#     providers.append(GeminiProvider())
#
#     # 3. Last-resort local fallback -- never fails.
#     providers.append(HeuristicFallbackProvider())
#
#     logger.info("Chat engine provider chain: %s", [p.name for p in providers])
#     return ChatEngine(providers)

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