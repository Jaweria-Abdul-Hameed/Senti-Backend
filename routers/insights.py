"""
routers/insights.py — powers the "Weekly Balance" graph on the Insights &
Profile screen. That graph used to be entirely hardcoded (a fixed set of
Bezier points, "Stability score: 84%" as a literal string). This computes
a real number from the six-class emotion vector already stored on every
user message (Message.emotion_scores — see the LSTM classifier in
ai/lstm_provider.py).
"""

import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db, Message, Conversation, User
from schemas import WeeklyStabilityOut
from security import get_current_user

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


def _stability_from_scores(scores: dict) -> float:
    """Heuristic 0-100 'stability' score from the 6-class emotion vector.
    Joy/Love pull it up, Fear/Sadness/Anger pull it down. Surprise is left
    out — it isn't inherently positive or negative, so it's not evidence
    either way. This is a simple, explainable heuristic, not a clinical
    measure; it exists to give the user a rough trend line, not a
    diagnosis."""
    positive = scores.get("Joy", 0) + scores.get("Love", 0)
    negative = scores.get("Fear", 0) + scores.get("Sadness", 0) + scores.get("Anger", 0)
    return max(0.0, min(100.0, 50 + (positive - negative) / 2))


@router.get("/weekly", response_model=list[WeeklyStabilityOut])
def weekly_stability(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=6)

    messages = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.user_id == current_user.id,
            Message.sender == "user",
            Message.emotion_scores.isnot(None),
            Message.timestamp >= datetime.datetime.combine(start, datetime.time.min),
        )
        .all()
    )

    by_day: dict[datetime.date, list[float]] = {start + datetime.timedelta(days=i): [] for i in range(7)}
    for m in messages:
        day = m.timestamp.date()
        if day in by_day:
            by_day[day].append(_stability_from_scores(m.emotion_scores))

    result = []
    for i in range(7):
        day = start + datetime.timedelta(days=i)
        day_scores = by_day[day]
        avg = round(sum(day_scores) / len(day_scores), 1) if day_scores else None
        result.append(
            WeeklyStabilityOut(
                date=day.isoformat(),
                day_label=day.strftime("%a"),
                stability=avg,
                message_count=len(day_scores),
            )
        )
    return result