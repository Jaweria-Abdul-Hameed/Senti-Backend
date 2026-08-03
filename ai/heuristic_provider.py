"""
Local keyword-heuristic fallback, plus a shared reply-selection function.

pick_reply_for_emotions() is a straight line-for-line port of the reply
templates that used to live in SentiRepository.kt's `getSentiReply`
fallback branch — same score thresholds, same reply bank. It's factored
out here (rather than kept private to HeuristicFallbackProvider) so that
HybridProvider can reuse it too: when the LSTM has real emotion scores but
Gemini is unavailable, HybridProvider picks a template reply for those
*real* scores instead of discarding them and falling all the way down to
this provider's own (much cruder) keyword re-classification.

HeuristicFallbackProvider itself is always last in the chain: it never
fails, so ChatEngine always has something to fall back to even if the
LSTM model failed to load at startup.
"""

from .base import AIProvider, ChatTurn, StructuredReply


def pick_reply_for_emotions(emotions: dict) -> str:
    """
    Given a 0-100 emotion score dict (Fear/Sadness/Anger/Joy/Love/Surprise),
    return a supportive template reply. Same thresholds/copy as the
    original Kotlin fallback bank — just decoupled from *how* the scores
    were produced (keyword heuristic here, LSTM in HybridProvider).
    """
    fear = emotions.get("Fear", 0)
    sadness = emotions.get("Sadness", 0)
    anger = emotions.get("Anger", 0)
    joy = emotions.get("Joy", 0)
    love = emotions.get("Love", 0)

    if sadness > 80:
        return (
            "I hear how heavy things are right now. It takes a lot of strength to talk about "
            "these feelings. I'm right here with you—let's take it one gentle breath at a time. "
            "What specifically felt most heavy today?"
        )
    if fear > 80:
        return (
            "It sounds like you're experiencing a wave of anxiety. Please know that you are safe "
            "here. Let's do a quick breathing exercise together to help anchor your mind: inhale "
            "slowly... hold... exhale... You are not alone."
        )
    if anger > 80:
        return (
            "It's completely valid to feel angry when things are unfair or overwhelming. I'm a "
            "safe, non-judgmental space to release some of that tension. What triggered this "
            "frustration today?"
        )
    if joy > 70:
        return (
            "I'm absolutely thrilled to hear that! Celebrating these moments of joy is a "
            "beautiful way to nurture your well-being. Thank you for sharing this positive "
            "light with me!"
        )
    if love > 70:
        return (
            "Thank you so much for your kind words. Knowing I can support your well-being "
            "brings so much warmth. How else can I help anchor you today?"
        )
    return (
        "Thank you for sharing that with me. I'm here to listen, support, and help guide "
        "you toward calm. Can you tell me more about what's on your mind?"
    )


def classify_by_keywords(user_message: str) -> dict:
    """
    Crude keyword-based emotion scoring — only used when there is no real
    classifier available at all (LSTM model failed to load). Kept separate
    from pick_reply_for_emotions() so HybridProvider can skip this entirely
    and pass its real LSTM scores straight into the template picker above.
    """
    text = user_message.lower()

    fear, sadness, anger, joy, love, surprise = 10, 10, 5, 15, 5, 10

    if any(w in text for w in ["overwhelmed", "stress", "anxious", "scared", "afraid", "panic"]):
        fear += 75
        sadness += 35
    if any(w in text for w in ["sad", "unhappy", "depressed", "cry", "lonely", "hurt", "long day"]):
        sadness += 80
        fear += 20
    if any(w in text for w in ["angry", "furious", "mad", "hate", "annoyed", "irritated"]):
        anger += 85
        sadness += 15
    if any(w in text for w in ["happy", "joy", "glad", "excited", "good day", "great"]):
        joy += 80
        love += 20
        sadness = fear = anger = 0
    if any(w in text for w in ["love", "thank", "grateful", "appreciate", "kind"]):
        love += 85
        joy += 30
        sadness = fear = 0
    if any(w in text for w in ["surprise", "shock", "suddenly", "amazing"]):
        surprise += 75

    fear, sadness, anger, joy, love, surprise = (
        max(0, min(100, v)) for v in (fear, sadness, anger, joy, love, surprise)
    )

    return {
        "Fear": fear,
        "Sadness": sadness,
        "Anger": anger,
        "Joy": joy,
        "Love": love,
        "Surprise": surprise,
    }


class HeuristicFallbackProvider(AIProvider):
    name = "heuristic_fallback"

    async def generate_reply(self, user_message: str, history: list[ChatTurn]) -> StructuredReply:
        emotions = classify_by_keywords(user_message)
        return StructuredReply(reply=pick_reply_for_emotions(emotions), emotions=emotions)

