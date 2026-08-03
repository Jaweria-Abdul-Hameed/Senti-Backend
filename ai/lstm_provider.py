# """
# ai/lstm_provider.py
#
# Wraps the trained emotion-classification model (senti_emotion_lstm.keras +
# senti_tokenizer.pkl, produced by train_emotion_lstm_fixed.py) as a
# classifier that other providers can call.
#
# This deliberately does NOT implement AIProvider / generate_reply() on its
# own. Per the "just emotion classification" decision, this model never
# writes user-facing reply text — it only scores emotions. HybridProvider
# (below) is the thing that satisfies the AIProvider contract by combining
# this classifier's output with Gemini's reply generation.
#
# Model inference is CPU-bound (no I/O), so per rules.md §3.2 it's offloaded
# to a thread executor rather than blocking the event loop — a single
# forward pass is a few ms, but under load that still adds up if it's
# inline in the request coroutine.
# """
#
# import asyncio
# import pickle
# import re
# import string
# from pathlib import Path
#
# from keras.models import load_model
# from keras.preprocessing.sequence import pad_sequences
# from nltk.corpus import stopwords
# from nltk.stem import WordNetLemmatizer
#
# from .base import EMOTION_CLASSES
#
# MAX_LEN = 50
#
# # Must match LABEL_NAMES in train_emotion_lstm_fixed.py — this is the
# # model's output index order, which is NOT the same as Senti's
# # EMOTION_CLASSES order. Verify this against your actual dataset's label
# # encoding before trusting it.
# MODEL_LABEL_ORDER = ["Sadness", "Joy", "Love", "Anger", "Fear", "Surprise"]
#
# _lemmatizer = WordNetLemmatizer()
# _stop_words = set(stopwords.words("english"))
#
#
# def _transform_data(text: str) -> str:
#     """Must exactly match the preprocessing used at training time."""
#     text = text.lower()
#     text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
#     text = re.sub(r"<.*?>", " ", text)
#     text = "".join(ch for ch in text if ch not in string.punctuation)
#     words = text.split()
#     words = [_lemmatizer.lemmatize(w) for w in words if w not in _stop_words]
#     return " ".join(words)
#
#
# class EmotionClassifier:
#     """Loads once at startup, reused across requests."""
#
#     def __init__(self, model_path: str = "senti_emotion_lstm.keras", tokenizer_path: str = "senti_tokenizer.pkl"):
#         model_file = Path(model_path)
#         tokenizer_file = Path(tokenizer_path)
#         if not model_file.exists() or not tokenizer_file.exists():
#             raise FileNotFoundError(
#                 f"Missing model artifacts: expected {model_file} and {tokenizer_file}. "
#                 "Run train_emotion_lstm_fixed.py and copy both files next to the backend."
#             )
#         self.model = load_model(model_file)
#         with open(tokenizer_file, "rb") as f:
#             self.tokenizer = pickle.load(f)
#
#     def _classify_sync(self, text: str) -> dict:
#         cleaned = _transform_data(text)
#         seq = self.tokenizer.texts_to_sequences([cleaned])
#         padded = pad_sequences(seq, maxlen=MAX_LEN, padding="post", truncating="post")
#         probs = self.model.predict(padded, verbose=0)[0]  # softmax over 6 classes, sums to ~1
#
#         by_model_order = {MODEL_LABEL_ORDER[i]: float(probs[i]) * 100 for i in range(len(MODEL_LABEL_ORDER))}
#         # Re-key into Senti's canonical EMOTION_CLASSES order.
#         return {k: round(by_model_order[k], 1) for k in EMOTION_CLASSES}
#
#     async def classify(self, text: str) -> dict:
#         """Non-blocking: runs the CPU-bound forward pass in a thread executor."""
#         loop = asyncio.get_running_loop()
#         return await loop.run_in_executor(None, self._classify_sync, text)

"""
ai/lstm_provider.py

Wraps the trained emotion-classification model (senti_emotion_lstm.keras +
senti_tokenizer.pkl, produced by train_emotion_lstm_fixed.py) as a
classifier that other providers can call.

This deliberately does NOT implement AIProvider / generate_reply() on its
own. Per the "just emotion classification" decision, this model never
writes user-facing reply text — it only scores emotions. HybridProvider
(below) is the thing that satisfies the AIProvider contract by combining
this classifier's output with Gemini's reply generation.

Model inference is CPU-bound (no I/O), so per rules.md §3.2 it's offloaded
to a thread executor rather than blocking the event loop — a single
forward pass is a few ms, but under load that still adds up if it's
inline in the request coroutine.
"""

import asyncio
import pickle
import re
from pathlib import Path

from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences
from nltk.stem import WordNetLemmatizer

from .base import EMOTION_CLASSES

MAX_LEN = 50

# Verified empirically against the live model (diagnose_label_order.py /
# diagnose_label_order_v2.py): Sadness, Joy, Anger, and Fear each land on
# their expected index with high confidence across a range of test
# sentences. Love and Surprise are real weak spots in the model itself
# (likely due to being the two smallest classes in the training data,
# 34,554 and 14,972 rows vs. 141,067 for Joy) — that's a model-accuracy
# problem to fix via retraining/rebalancing, not a label-order problem.
MODEL_LABEL_ORDER = ["Sadness", "Joy", "Love", "Anger", "Fear", "Surprise"]

_lemmatizer = WordNetLemmatizer()


def _transform_data(text: str) -> str:
    """Must exactly match the preprocessing used at training time
    (train_emotion_lstm_fixed.py's transform_data). Critically, this does
    NOT drop stopwords — the training script deliberately keeps them
    ("DO NOT drop stop words! Keep the sequence natural for the LSTM."),
    since NLTK's English stopword list includes negation words (no, not,
    nor, don't, won't, isn't...) whose removal silently flips the meaning
    of a sentence before the model ever sees it, and shifts every
    downstream token's position in the sequence besides. A prior version
    of this function stripped stopwords here while training didn't,
    which was a real train/inference mismatch bug.
    """
    text = text.lower()
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    words = text.split()
    words = [_lemmatizer.lemmatize(w) for w in words]
    return " ".join(words)


class EmotionClassifier:
    """Loads once at startup, reused across requests."""

    def __init__(self, model_path: str = "senti_emotion_lstm.keras", tokenizer_path: str = "senti_tokenizer.pkl"):
        model_file = Path(model_path)
        tokenizer_file = Path(tokenizer_path)
        if not model_file.exists() or not tokenizer_file.exists():
            raise FileNotFoundError(
                f"Missing model artifacts: expected {model_file} and {tokenizer_file}. "
                "Run train_emotion_lstm_fixed.py and copy both files next to the backend."
            )
        self.model = load_model(model_file)
        with open(tokenizer_file, "rb") as f:
            self.tokenizer = pickle.load(f)

    def _classify_sync(self, text: str) -> dict:
        cleaned = _transform_data(text)
        seq = self.tokenizer.texts_to_sequences([cleaned])
        padded = pad_sequences(seq, maxlen=MAX_LEN, padding="post", truncating="post")
        probs = self.model.predict(padded, verbose=0)[0]  # softmax over 6 classes, sums to ~1

        by_model_order = {MODEL_LABEL_ORDER[i]: float(probs[i]) * 100 for i in range(len(MODEL_LABEL_ORDER))}
        # Re-key into Senti's canonical EMOTION_CLASSES order.
        return {k: round(by_model_order[k], 1) for k in EMOTION_CLASSES}

    async def classify(self, text: str) -> dict:
        """Non-blocking: runs the CPU-bound forward pass in a thread executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._classify_sync, text)
