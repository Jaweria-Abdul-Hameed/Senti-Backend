from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db, Conversation, User
from schemas import ConversationCreateRequest, ConversationOut
from security import get_current_user

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


def _get_owned_conversation(conversation_id: int, user: User, db: Session) -> Conversation:
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if convo.user_id != user.id:
        # 404 rather than 403 here on purpose — don't confirm to a caller
        # that a conversation id belonging to someone else even exists.
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.post("", response_model=ConversationOut)
def create_conversation(
    body: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convo = Conversation(user_id=current_user.id, title=body.title or "New Reflection")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.get("", response_model=list[ConversationOut])
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(desc(Conversation.created_at))
        .all()
    )


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_conversation(conversation_id, current_user, db)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convo = _get_owned_conversation(conversation_id, current_user, db)
    db.delete(convo)
    db.commit()
