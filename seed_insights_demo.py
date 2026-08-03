"""
seed_insights_demo.py — inserts backdated demo messages directly into the DB
so the Weekly Balance graph has multiple days of history for a presentation,
without touching the phone's clock (which wouldn't work anyway — timestamps
are set server-side, not client-side; see routers/chat.py).

SAFETY RULES baked in, on purpose:
  1. Only ever touches ONE account: the --email you pass in. Never scans or
     modifies any other user's data.
  2. NEVER writes anything dated today. Today's dot is left completely alone
     so your live "type a message, watch the dot move" demo still works
     exactly as it does now — this script only fills in the PAST 6 days of
     the 7-day window, never day 0.
  3. Idempotent: tags every message it creates with a "[seed]" marker in the
     conversation title so re-running the script doesn't pile up duplicate
     conversations — it reuses the same seeded conversation if one already
     exists for that user.
  4. Purely additive. Never deletes or updates any existing row.

Usage:
    python seed_insights_demo.py --email demo@example.com
    python seed_insights_demo.py --email demo@example.com --days 6 --messages-per-day 3
"""

import argparse
import datetime
import random
import sys

from database import SessionLocal, User, Conversation, Message

SEEDED_CONVO_TITLE = "[seed] Insights demo history"

# (text, emotion vector) pairs spanning a range of stability outcomes so the
# graph shows real up-and-down movement instead of a flat line. Vectors are
# in the same 0-100-ish scale the real classifier produces; keys match
# ai/base.py's EMOTION_CLASSES exactly.
SAMPLE_TURNS = [
    ("Feeling pretty good today, got a lot done.",
     {"Fear": 3, "Sadness": 2, "Anger": 1, "Joy": 78, "Love": 40, "Surprise": 5}),
    ("Work was stressful but I managed it okay.",
     {"Fear": 30, "Sadness": 20, "Anger": 15, "Joy": 35, "Love": 10, "Surprise": 5}),
    ("Had a rough night, couldn't sleep much.",
     {"Fear": 45, "Sadness": 55, "Anger": 10, "Joy": 5, "Love": 5, "Surprise": 2}),
    ("Spent time with friends, it really helped.",
     {"Fear": 2, "Sadness": 5, "Anger": 1, "Joy": 70, "Love": 65, "Surprise": 10}),
    ("Just an average day, nothing major happened.",
     {"Fear": 10, "Sadness": 10, "Anger": 5, "Joy": 30, "Love": 15, "Surprise": 5}),
    ("Feeling anxious about an upcoming deadline.",
     {"Fear": 60, "Sadness": 25, "Anger": 10, "Joy": 8, "Love": 5, "Surprise": 3}),
    ("Grateful for the small wins today.",
     {"Fear": 5, "Sadness": 5, "Anger": 2, "Joy": 60, "Love": 50, "Surprise": 8}),
]

SAMPLE_REPLIES = [
    "That sounds like it took real effort — good on you for pushing through.",
    "That's understandable, stress like that can build up fast.",
    "I'm sorry to hear that. Rough nights can make everything harder the next day.",
    "It's great that you have people you can lean on.",
    "Sounds like a steady, uneventful day — those matter too.",
    "Deadlines can be tough. What would help take some pressure off right now?",
    "It's good to notice the small wins, they add up.",
]


def seed(email: str, days: int, messages_per_day: int, dry_run: bool):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"No user found with email '{email}'. Aborting — refusing to guess.")
            sys.exit(1)

        today = datetime.date.today()
        if days < 1 or days > 6:
            print("--days must be between 1 and 6 (day 0 / today is never seeded).")
            sys.exit(1)

        convo = (
            db.query(Conversation)
            .filter(Conversation.user_id == user.id, Conversation.title == SEEDED_CONVO_TITLE)
            .first()
        )
        if convo is None:
            convo = Conversation(user_id=user.id, title=SEEDED_CONVO_TITLE)
            db.add(convo)
            db.flush()  # get convo.id without a full commit yet
            print(f"Created seeded conversation (id={convo.id}) for {email}.")
        else:
            print(f"Reusing existing seeded conversation (id={convo.id}) for {email}.")

        created = 0
        for day_offset in range(1, days + 1):  # 1..days -> NEVER 0 (today)
            day = today - datetime.timedelta(days=day_offset)
            for slot in range(messages_per_day):
                text, emotions = random.choice(SAMPLE_TURNS)
                reply_text = random.choice(SAMPLE_REPLIES)
                # Spread messages across the day (e.g. morning/afternoon/evening)
                # instead of stacking them all at midnight.
                hour = 9 + slot * (10 // max(messages_per_day, 1))
                ts = datetime.datetime.combine(day, datetime.time(hour=min(hour, 22), minute=random.randint(0, 59)))

                user_msg = Message(
                    conversation_id=convo.id,
                    sender="user",
                    message_text=text,
                    emotion_scores=emotions,
                    timestamp=ts,
                )
                senti_msg = Message(
                    conversation_id=convo.id,
                    sender="senti",
                    message_text=reply_text,
                    emotion_scores=emotions,
                    timestamp=ts + datetime.timedelta(seconds=20),
                )
                db.add(user_msg)
                db.add(senti_msg)
                created += 2

        if dry_run:
            print(f"[dry run] Would insert {created} messages across {days} past day(s). No changes committed.")
            db.rollback()
            return

        db.commit()
        print(f"Inserted {created} messages across {days} past day(s) for {email}.")
        print("Today's date was NOT touched — your live demo dot is untouched.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True, help="Email of the demo account to seed (only this account is touched).")
    parser.add_argument("--days", type=int, default=6, help="How many past days to backfill, 1-6. Default 6. Today is never touched.")
    parser.add_argument("--messages-per-day", type=int, default=2, help="How many user/senti turn pairs per day. Default 2.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without writing to the DB.")
    args = parser.parse_args()

    seed(args.email, args.days, args.messages_per_day, args.dry_run)