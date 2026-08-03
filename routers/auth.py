import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db, User
from email_service import send_password_reset_email, send_welcome_email
from rate_limit import limiter
from schemas import (
    SignUpRequest,
    LoginRequest,
    UserOut,
    TokenResponse,
    GoogleAuthRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from security import (
    create_access_token,
    create_password_reset_token,
    verify_password_reset_token,
    verify_google_id_token,
    get_current_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger("senti.auth")


@router.post("/signup", response_model=TokenResponse)
@limiter.limit("5/minute")
def signup(request: Request, body: SignUpRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        username=body.username,
        email=body.email,
        password_hash=pwd_context.hash(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Fire-and-forget: runs after the response is sent, so a slow or failing
    # mail server never delays or breaks account creation (see email_service's
    # docstring — send_welcome_email() never raises either).
    background_tasks.add_task(send_welcome_email, user.email, user.username)

    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash or not pwd_context.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/google", response_model=TokenResponse)
def google_auth(body: GoogleAuthRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Handles both "sign up with Google" and "log in with Google" in one call —
    same endpoint either way, since from the client's perspective it's just
    "continue with Google" and it shouldn't matter if this is their first
    time or their hundredth.
    """
    claims = verify_google_id_token(body.id_token)
    google_sub = claims["sub"]
    email = claims.get("email")
    name = claims.get("name") or (email.split("@")[0] if email else "Senti User")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # 1. Already linked by Google's stable id -> just log them in.
    user = db.query(User).filter(User.google_sub == google_sub).first()

    # 2. Not linked yet, but an account with this email already exists
    #    (e.g. they originally signed up with email+password) -> link it.
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_sub = google_sub
            db.commit()
            db.refresh(user)

    # 3. Brand new user entirely.
    if not user:
        user = User(username=name, email=email, password_hash=None, google_sub=google_sub)
        db.add(user)
        db.commit()
        db.refresh(user)
        background_tasks.add_task(send_welcome_email, user.email, user.username)

    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    # Always return the same generic response whether or not the email
    # exists — otherwise this endpoint becomes a way to enumerate which
    # emails have accounts.
    generic_response = MessageResponse(
        message="If that email is registered, a password reset link has been sent."
    )
    if not user:
        return generic_response

    reset_token = create_password_reset_token(user.id)
    sent = send_password_reset_email(user.email, reset_token)
    if not sent:
        # SMTP isn't configured or the send failed — email_service.py already
        # logged the token for local testing. Still return the same generic
        # response so this never becomes a way to enumerate accounts, and
        # never breaks the request just because mail delivery is down.
        logger.warning("Password reset email NOT delivered for %s — see email_service logs above.", user.email)
    return generic_response


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    user_id = verify_password_reset_token(body.token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = pwd_context.hash(body.new_password)
    db.commit()
    return MessageResponse(message="Password updated. You can log in with your new password now.")


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Replaces GET /users/{user_id} for the common case of "who am I" —
    derives identity from the token instead of trusting a path param."""
    return current_user
