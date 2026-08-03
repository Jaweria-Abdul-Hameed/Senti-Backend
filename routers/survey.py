from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db, SurveyResponse, User
from schemas import SurveyResponseRequest, SurveyResponseOut
from security import get_current_user

router = APIRouter(prefix="/api/v1/survey", tags=["survey"])


@router.post("", response_model=SurveyResponseOut)
def submit_survey(
    body: SurveyResponseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = SurveyResponse(user_id=current_user.id, survey_data=body.survey_data)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=list[SurveyResponseOut])
def list_survey_responses(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(SurveyResponse)
        .filter(SurveyResponse.user_id == current_user.id)
        .order_by(desc(SurveyResponse.timestamp))
        .all()
    )
