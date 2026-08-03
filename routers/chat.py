# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
#
# from ai import ChatTurn
# from ai.distress_agent import evaluate_distress
# from ai_setup import get_chat_engine
# from database import get_db, Message, User
# from schemas import SendMessageRequest, SendMessageResponse
# from security import get_current_user
# from routers.conversations import _get_owned_conversation
#
# router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
#
#
# @router.post("/message", response_model=SendMessageResponse)
# async def send_message(
#     body: SendMessageRequest,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     convo = _get_owned_conversation(body.conversation_id, current_user, db)
#     if not body.text.strip():
#         raise HTTPException(status_code=400, detail="Message text cannot be blank")
#
#     # 1. Save the user's message first (same order as SentiViewModel.sendMessage()).
#     user_msg = Message(conversation_id=convo.id, sender="user", message_text=body.text)
#     db.add(user_msg)
#     db.commit()
#     db.refresh(user_msg)
#
#     # 2. Build the sliding window of recent turns (workflow.md §5), oldest first.
#     recent = (
#         db.query(Message)
#         .filter(Message.conversation_id == convo.id)
#         .order_by(Message.timestamp.desc())
#         .limit(5)
#         .all()
#     )
#     history = [ChatTurn(sender=m.sender, text=m.message_text) for m in reversed(recent)]
#
#     # 3. Run the provider chain (Hybrid LSTM -> Groq -> local heuristic fallback).
#     chat_engine = get_chat_engine()
#     reply, provider_name = await chat_engine.get_reply(body.text, history)
#
#     # 4. Save SENTI's reply with its emotion vector.
#     senti_msg = Message(
#         conversation_id=convo.id,
#         sender="senti",
#         message_text=reply.reply,
#         emotion_scores=reply.emotions,
#     )
#     db.add(senti_msg)
#     db.commit()
#     db.refresh(senti_msg)
#
#     # 5. ReAct-style reasoning step decides on escalation — see
#     #    ai/distress_agent.py for why this replaced the old flat >89 check.
#     distress, _reasoning_note = await evaluate_distress(reply.emotions, body.text)
#
#     return SendMessageResponse(
#         user_message=user_msg,
#         senti_message=senti_msg,
#         distress_triggered=distress,
#         ai_provider_used=provider_name,
#     )

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ai import ChatTurn
from ai.distress_agent import evaluate_distress
from ai_setup import get_chat_engine
from database import get_db, Message, User
from schemas import SendMessageRequest, SendMessageResponse
from security import get_current_user
from routers.conversations import _get_owned_conversation

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/message", response_model=SendMessageResponse)
async def send_message(
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convo = _get_owned_conversation(body.conversation_id, current_user, db)
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Message text cannot be blank")

    # 1. Save the user's message first (same order as SentiViewModel.sendMessage()).
    user_msg = Message(conversation_id=convo.id, sender="user", message_text=body.text)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 2. Build the sliding window of recent turns (workflow.md §5), oldest first.
    recent = (
        db.query(Message)
        .filter(Message.conversation_id == convo.id)
        .order_by(Message.timestamp.desc())
        .limit(5)
        .all()
    )
    history = [ChatTurn(sender=m.sender, text=m.message_text) for m in reversed(recent)]

    # 3. Run the provider chain (Hybrid LSTM -> Groq -> local heuristic fallback).
    chat_engine = get_chat_engine()
    reply, provider_name = await chat_engine.get_reply(body.text, history)

    # 3b. The classifier scores the USER's text, not SENTI's reply — so the
    #     emotion vector belongs on user_msg too. This is what insights.py's
    #     weekly-stability query actually reads (sender == "user" AND
    #     emotion_scores is not null); without this, that filter never
    #     matched anything and the Insights graph stayed empty forever.
    user_msg.emotion_scores = reply.emotions
    db.add(user_msg)

    # 4. Save SENTI's reply with its emotion vector (unchanged — still kept
    #    here too, since nothing that already reads it should have to change).
    senti_msg = Message(
        conversation_id=convo.id,
        sender="senti",
        message_text=reply.reply,
        emotion_scores=reply.emotions,
    )
    db.add(senti_msg)
    db.commit()
    db.refresh(senti_msg)

    # 5. ReAct-style reasoning step decides on escalation — see
    #    ai/distress_agent.py for why this replaced the old flat >89 check.
    distress, _reasoning_note = await evaluate_distress(reply.emotions, body.text)

    return SendMessageResponse(
        user_message=user_msg,
        senti_message=senti_msg,
        distress_triggered=distress,
        ai_provider_used=provider_name,
    )