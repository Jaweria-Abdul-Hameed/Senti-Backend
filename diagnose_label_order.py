"""
diagnose_label_order_v2.py

Same idea as diagnose_label_order.py, but with several longer, conversational,
first-person sentences per emotion (the kind of thing a real Senti user
would actually type) instead of one tweet-style line each. This gives a much
clearer picture of real-world accuracy per class, and prints a confusion
summary so you can see exactly which emotions get confused with which.

Run from your backend root (same folder as senti_emotion_lstm.keras /
senti_tokenizer.pkl):
    python diagnose_label_order_v2.py
"""

import pickle
import re
import string
from collections import defaultdict

from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

from ai.lstm_provider import MODEL_LABEL_ORDER  # the current (possibly-wrong) mapping

MAX_LEN = 50

# 6 longer, conversational, app-realistic sentences per emotion — closer to
# what someone actually types into a well-being chat app than a tweet is.
TEST_SENTENCES = {
    "Sadness": [
        "I've been feeling really down lately and I don't know why.",
        "Everything just feels heavy and pointless right now.",
        "I cried myself to sleep again last night.",
        "I miss how things used to be, it makes me so sad.",
        "I feel so alone even when I'm surrounded by people.",
        "Nothing seems to bring me joy anymore, I just feel empty.",
    ],
    "Joy": [
        "I got the job offer today and I can't stop smiling!",
        "Spending time with my family this weekend made me so happy.",
        "I feel amazing today, everything is going right for once.",
        "I'm so proud of myself for finishing that project.",
        "Life feels really good right now, I'm grateful for everything.",
        "I laughed so hard today my cheeks still hurt.",
    ],
    "Love": [
        "I love spending every moment with my partner, they mean the world to me.",
        "My best friend has been there for me through everything, I love her so much.",
        "I feel so much love and warmth when I'm with my family.",
        "I adore my dog, he's the best part of my day.",
        "I care about you more than words can say.",
        "Being around people I love makes everything feel okay.",
    ],
    "Anger": [
        "I am so frustrated with my coworker, they never listen to me.",
        "It makes me furious when people don't keep their promises.",
        "I'm sick and tired of being treated like this.",
        "I wanted to scream when he canceled on me again last minute.",
        "This whole situation is making my blood boil.",
        "I'm so annoyed, nothing has gone right today.",
    ],
    "Fear": [
        "I'm really overwhelmed and anxious about my exam tomorrow.",
        "I'm scared something bad is going to happen to my family.",
        "My chest gets tight and I can't breathe when I think about the future.",
        "I feel a bit overwhelmed today, can you help me unwind?",
        "I'm so nervous about the interview, I can't stop shaking.",
        "I keep worrying that everyone is going to leave me.",
    ],
    "Surprise": [
        "I can't believe my friends threw me a surprise party!",
        "Wow, I did not expect to get accepted, this is shocking.",
        "I was totally caught off guard when she showed up unannounced.",
        "I never saw that plot twist coming, I'm stunned.",
        "I'm speechless, I didn't expect this news at all.",
        "That was such an unexpected turn of events, I'm amazed.",
    ],
}

_lemmatizer = WordNetLemmatizer()
_stop_words = set(stopwords.words("english"))


def _transform_data(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"<.*?>", " ", text)
    text = "".join(ch for ch in text if ch not in string.punctuation)
    words = text.split()
    words = [_lemmatizer.lemmatize(w) for w in words if w not in _stop_words]
    return " ".join(words)


def main():
    print("Loading model and tokenizer...")
    model = load_model("senti_emotion_lstm.keras")
    with open("senti_tokenizer.pkl", "rb") as f:
        tokenizer = pickle.load(f)

    print(f"Using MODEL_LABEL_ORDER from ai/lstm_provider.py: {MODEL_LABEL_ORDER}\n")

    # confusion[expected][predicted] = count
    confusion = defaultdict(lambda: defaultdict(int))
    correct_counts = defaultdict(int)
    total_counts = defaultdict(int)

    for expected_emotion, sentences in TEST_SENTENCES.items():
        print(f"--- {expected_emotion} ---")
        for sentence in sentences:
            cleaned = _transform_data(sentence)
            seq = tokenizer.texts_to_sequences([cleaned])
            padded = pad_sequences(seq, maxlen=MAX_LEN, padding="post", truncating="post")
            probs = model.predict(padded, verbose=0)[0]

            winning_index = int(probs.argmax())
            predicted_emotion = MODEL_LABEL_ORDER[winning_index]
            confidence = float(probs[winning_index])

            total_counts[expected_emotion] += 1
            confusion[expected_emotion][predicted_emotion] += 1
            mark = "OK" if predicted_emotion == expected_emotion else "WRONG"
            if predicted_emotion == expected_emotion:
                correct_counts[expected_emotion] += 1

            print(f"  [{mark:5}] predicted={predicted_emotion:9} (conf={confidence:.2f})  '{sentence}'")
        print()

    print("=" * 70)
    print("PER-CLASS ACCURACY (on these realistic app-style sentences):")
    for emotion in TEST_SENTENCES:
        correct = correct_counts[emotion]
        total = total_counts[emotion]
        print(f"  {emotion:9}: {correct}/{total} correct ({100 * correct / total:.0f}%)")

    print("\nCONFUSION SUMMARY (expected -> what it actually got predicted as):")
    for emotion in TEST_SENTENCES:
        preds = confusion[emotion]
        breakdown = ", ".join(f"{pred}={count}" for pred, count in sorted(preds.items(), key=lambda kv: -kv[1]))
        print(f"  {emotion:9} -> {breakdown}")
    print("=" * 70)


if __name__ == "__main__":
    main()