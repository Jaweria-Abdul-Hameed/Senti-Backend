from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db, Message, User
from schemas import MessageOut
from security import get_current_user
from routers.conversations import _get_owned_conversation

router = APIRouter(prefix="/api/v1/conversations", tags=["messages"])


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Raises 404 if this conversation doesn't exist or isn't the caller's —
    # same ownership check used everywhere else, so you can't page through
    # someone else's messages just by guessing conversation ids.
    _get_owned_conversation(conversation_id, current_user, db)
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.asc())
        .all()
    )
