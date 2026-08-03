# SENTI Backend (FastAPI)

This replaces the on-device Room DB + direct Gemini call in the Kotlin app with a
server the Android app talks to over HTTP. Run this in PyCharm; run the Android
app in Android Studio; they talk over `http://<your-ip>:8000`.

## What moved where

| Old Kotlin piece | New home |
|---|---|
| `SentiEntities.kt` (Room `@Entity`s) | `database.py` (SQLAlchemy models) |
| `SentiDao.kt` / `SentiDatabase.kt` | `database.py` + routers (SQLAlchemy queries) |
| `SentiRepository.insertUser/login` | `routers/auth.py` |
| `SentiRepository` conversation queries | `routers/conversations.py` |
| `SentiRepository.getMessagesForConversation` | `routers/messages.py` |
| `SentiRepository.getSentiReply()` (Gemini call + heuristic fallback) | `ai/gemini_provider.py` + `ai/heuristic_provider.py`, orchestrated by `ai/engine.py` |
| `SentiViewModel.sendMessage()`'s distress check (`> 89`) | `ai/engine.py::evaluate_distress()` |
| `BuildConfig.GEMINI_API_KEY` (baked into the APK) | `GEMINI_API_KEY` env var, server-side only |

Nothing about the actual behavior changed — same trigger words, same score
weights, same reply text, same Gemini system prompt, same 89% threshold. It's
a relocation, not a rewrite of the logic itself.

## The plug-and-play part

Everything AI-related implements one interface (`ai/base.py::AIProvider`):

```python
class AIProvider(ABC):
    async def generate_reply(self, user_message: str, history: list[ChatTurn]) -> StructuredReply:
        ...
```

`ai_setup.py` is the **only file you touch** to change SENTI's brain later:

```python
def get_chat_engine() -> ChatEngine:
    return ChatEngine([
        GeminiProvider(),
        HeuristicFallbackProvider(),
    ])
```

`ChatEngine` tries each provider in order and uses the first one that
succeeds. To add your fine-tuned model, your own RNN classifier, or a real
LangGraph ReAct agent later:

1. Create `ai/your_thing_provider.py`, subclass `AIProvider`, implement
   `generate_reply()`.
2. Add it to the list in `ai_setup.py` — first in the list = tried first.

`routers/chat.py`, the database layer, and the Android client never need to
change for that swap.

## Endpoints

```
POST   /api/v1/auth/signup                        {username, email, password}
POST   /api/v1/auth/login                         {email, password}
GET    /api/v1/auth/users/{user_id}

POST   /api/v1/conversations                      {user_id, title?}
GET    /api/v1/conversations?user_id=...
GET    /api/v1/conversations/{id}
DELETE /api/v1/conversations/{id}

GET    /api/v1/conversations/{id}/messages

POST   /api/v1/chat/message                       {conversation_id, text}
       -> {user_message, senti_message, distress_triggered, ai_provider_used}

POST   /api/v1/survey                             {user_id, survey_data}
GET    /api/v1/survey?user_id=...

GET    /health
```

Interactive docs at `/docs` once it's running.

## Running it (PyCharm or terminal)

```bash
python -m venv venv
source venv/bin/activate        # or venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env
# edit .env: set GEMINI_API_KEY (same key you had in the Android .env),
# and DATABASE_URL if your Postgres isn't the localhost default.

createdb senti_db                # if it doesn't exist yet
python seed_db.py                # optional: loads the same test data your seed script always did

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` matters if you're hitting this from an Android emulator or a
physical device — `127.0.0.1` on the phone isn't your dev machine. From the
Android emulator specifically, your dev machine's `localhost` is
`10.0.2.2`; from a real device on the same Wi-Fi, use your machine's LAN IP.

## What didn't move (on purpose)

This backend mirrors the app's *current* logic, not the aspirational
architecture in `constraints.md`/`workflow.md` (SQLCipher, JWT rotation,
anonymous UUIDs, PostGIS clinic routing, prompt-injection sanitization,
etc.). Those are real gaps against the source-of-truth docs, worth closing
before this goes anywhere near production — but they're a separate piece of
work from "move the existing logic off the phone," which is what this does.

## Not done yet: the Android side

The Kotlin app still writes to Room and calls Gemini directly. To finish the
migration, `SentiRepository.kt` needs to become a Retrofit client against the
endpoints above instead of a Room+Gemini wrapper — happy to do that pass
next; wanted to get the backend in your hands first since that's what you
asked for.
"# Senti-Backend" 
