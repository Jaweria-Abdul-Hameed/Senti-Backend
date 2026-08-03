# """
# email_service.py — actually sends the password-reset email.
#
# Previously routers/auth.py just logged the reset token to the server console
# (see the TODO that used to live there) — fine for typing the code into the
# app yourself during development, useless for a real user who forgot their
# password and can't see your terminal.
#
# This wires up real SMTP sending, using stdlib smtplib (no new dependency).
# Works with Gmail (via an "app password", not your real password), Outlook,
# or any other SMTP provider — just fill in the SMTP_* values in .env.
#
# Design choices:
#   - Never raises out of send_password_reset_email(). If SMTP isn't
#     configured, or sending fails for any reason (bad creds, network,
#     provider rate-limit), we log it and return False. The forgot-password
#     endpoint always returns the same generic "if that email is registered..."
#     response either way — so a broken mail server can't turn into a way to
#     fingerprint which emails exist, and can't crash the request.
#   - Runs synchronously. auth.py's forgot_password() is a plain `def`, not
#     `async def`, so FastAPI already runs it in a threadpool — a blocking
#     smtplib call here doesn't block the event loop.
# """
#
# import logging
# import os
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
#
# logger = logging.getLogger("senti.email")
#
#
# def _smtp_configured() -> bool:
#     return bool(os.getenv("SMTP_HOST")) and bool(os.getenv("SMTP_USER")) and bool(os.getenv("SMTP_PASSWORD"))
#
#
# def send_password_reset_email(to_email: str, reset_token: str) -> bool:
#     """
#     Sends the reset token as a code the user copies into the app's
#     "Reset Code" field on ForgotPasswordScreen. Returns True if the email
#     was actually handed off to the SMTP server, False otherwise (never
#     raises — see module docstring).
#
#     Note the token is a full signed JWT (long), not a cute 6-digit code —
#     that's intentional (it's the same token security.py's
#     verify_password_reset_token() checks), just less pretty to copy/paste.
#     If you want a short numeric code instead, that needs a separate
#     "store a hashed OTP + expiry in the DB" mechanism — a bigger change
#     than this file; ask if you want that built out.
#     """
#     if not _smtp_configured():
#         logger.warning(
#             "SMTP isn't configured (SMTP_HOST/SMTP_USER/SMTP_PASSWORD missing in .env) — "
#             "email NOT sent. Reset token for %s: %s",
#             to_email,
#             reset_token,
#         )
#         return False
#
#     host = os.getenv("SMTP_HOST", "")
#     port = int(os.getenv("SMTP_PORT", "587"))
#     user = os.getenv("SMTP_USER", "")
#     password = os.getenv("SMTP_PASSWORD", "")
#     from_email = os.getenv("SMTP_FROM_EMAIL", user)
#     use_tls = os.getenv("SMTP_USE_TLS", "true").lower() != "false"
#
#     subject = "Your SENTI password reset code"
#     body_text = (
#         "Someone (hopefully you) requested a password reset for your SENTI account.\n\n"
#         f"Your reset code:\n{reset_token}\n\n"
#         "Open the app, tap \"Forgot Password?\", and paste this code into the "
#         "\"Reset Code\" field along with your new password.\n\n"
#         "This code expires in 30 minutes. If you didn't request this, you can "
#         "safely ignore this email — your password won't change."
#     )
#
#     msg = MIMEMultipart()
#     msg["From"] = from_email
#     msg["To"] = to_email
#     msg["Subject"] = subject
#     msg.attach(MIMEText(body_text, "plain"))
#
# def send_welcome_email(to_email: str, username: str) -> bool:
#     """
#     Sends a signup confirmation email — "your Senti account is ready". This
#     is a courtesy confirmation, not a verification gate: it doesn't block
#     login and there's no "confirm your email" link to click, so a missing
#     SMTP config or a delivery failure must never affect signup itself.
#
#     Same never-raises contract as send_password_reset_email(): returns True
#     only if the message was actually handed off to the SMTP server.
#     """
#     if not _smtp_configured():
#         logger.warning(
#             "SMTP isn't configured (SMTP_HOST/SMTP_USER/SMTP_PASSWORD missing in .env) — "
#             "welcome email NOT sent to %s.",
#             to_email,
#         )
#         return False
#
#     host = os.getenv("SMTP_HOST", "")
#     port = int(os.getenv("SMTP_PORT", "587"))
#     user = os.getenv("SMTP_USER", "")
#     password = os.getenv("SMTP_PASSWORD", "")
#     from_email = os.getenv("SMTP_FROM_EMAIL", user)
#     use_tls = os.getenv("SMTP_USE_TLS", "true").lower() != "false"
#
#     subject = "Welcome to Senti"
#     body_text = (
#         f"Hi {username},\n\n"
#         "Your Senti account is set up and ready to go. Senti is your emotional "
#         "safe harbor — check in whenever you need to talk, reflect, or just "
#         "see how your week has been trending.\n\n"
#         "If you didn't create this account, you can ignore this email or "
#         "reach out to us so we can look into it.\n\n"
#         "— The Senti team"
#     )
#
#     msg = MIMEMultipart()
#     msg["From"] = from_email
#     msg["To"] = to_email
#     msg["Subject"] = subject
#     msg.attach(MIMEText(body_text, "plain"))
#
#     try:
#         with smtplib.SMTP(host, port, timeout=15) as server:
#             if use_tls:
#                 server.starttls()
#             server.login(user, password)
#             server.sendmail(from_email, [to_email], msg.as_string())
#         logger.info("Welcome email sent to %s", to_email)
#         return True
#     except Exception as e:  # noqa: BLE001 — never let a mail failure break signup
#         logger.error("Failed to send welcome email to %s: %s", to_email, e)
#         return False

"""
email_service.py — actually sends the password-reset email.

Previously routers/auth.py just logged the reset token to the server console
(see the TODO that used to live there) — fine for typing the code into the
app yourself during development, useless for a real user who forgot their
password and can't see your terminal.

This wires up real SMTP sending, using stdlib smtplib (no new dependency).
Works with Mailtrap, Gmail, Outlook, or any other SMTP provider — just fill in
the SMTP_* values in .env.

Design choices:
  - Never raises out of send_password_reset_email(). If SMTP isn't
    configured, or sending fails for any reason (bad creds, network,
    provider rate-limit), we log it and return False. The forgot-password
    endpoint always returns the same generic "if that email is registered..."
    response either way — so a broken mail server can't turn into a way to
    fingerprint which emails exist, and can't crash the request.
  - Runs synchronously. auth.py's forgot_password() is a plain `def`, not
    `async def`, so FastAPI already runs it in a threadpool — a blocking
    smtplib call here doesn't block the event loop.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("senti.email")


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST")) and bool(os.getenv("SMTP_USER")) and bool(os.getenv("SMTP_PASSWORD"))


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Sends the reset token as a code the user copies into the app's
    "Reset Code" field on ForgotPasswordScreen. Returns True if the email
    was actually handed off to the SMTP server, False otherwise (never
    raises — see module docstring).

    Note the token is a full signed JWT (long), not a cute 6-digit code —
    that's intentional (it's the same token security.py's
    verify_password_reset_token() checks), just less pretty to copy/paste.
    If you want a short numeric code instead, that needs a separate
    "store a hashed OTP + expiry in the DB" mechanism — a bigger change
    than this file; ask if you want that built out.
    """
    if not _smtp_configured():
        logger.warning(
            "SMTP isn't configured (SMTP_HOST/SMTP_USER/SMTP_PASSWORD missing in .env) — "
            "email NOT sent. Reset token for %s: %s",
            to_email,
            reset_token,
        )
        return False

    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "2525"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", user)
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() != "false"

    subject = "Your SENTI password reset code"
    body_text = (
        "Someone (hopefully you) requested a password reset for your SENTI account.\n\n"
        f"Your reset code:\n{reset_token}\n\n"
        "Open the app, tap \"Forgot Password?\", and paste this code into the "
        "\"Reset Code\" field along with your new password.\n\n"
        "This code expires in 30 minutes. If you didn't request this, you can "
        "safely ignore this email — your password won't change."
    )

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                server.starttls()
            server.login(user, password)
            server.sendmail(from_email, [to_email], msg.as_string())
        logger.info("Password reset email sent to %s", to_email)
        return True
    except Exception as e:  # noqa: BLE001 — never let a mail failure break the endpoint
        logger.error("Failed to send password reset email to %s: %s", to_email, e, exc_info=True)
        return False


def send_welcome_email(to_email: str, username: str) -> bool:
    """
    Sends a signup confirmation email — "your Senti account is ready". This
    is a courtesy confirmation, not a verification gate: it doesn't block
    login and there's no "confirm your email" link to click, so a missing
    SMTP config or a delivery failure must never affect signup itself.

    Same never-raises contract as send_password_reset_email(): returns True
    only if the message was actually handed off to the SMTP server.
    """
    if not _smtp_configured():
        logger.warning(
            "SMTP isn't configured (SMTP_HOST/SMTP_USER/SMTP_PASSWORD missing in .env) — "
            "welcome email NOT sent to %s.",
            to_email,
        )
        return False

    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "2525"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", user)
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() != "false"

    subject = "Welcome to Senti"
    body_text = (
        f"Hi {username},\n\n"
        "Your Senti account is set up and ready to go. Senti is your emotional "
        "safe harbor — check in whenever you need to talk, reflect, or just "
        "see how your week has been trending.\n\n"
        "If you didn't create this account, you can ignore this email or "
        "reach out to us so we can look into it.\n\n"
        "— The Senti team"
    )

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                server.starttls()
            server.login(user, password)
            server.sendmail(from_email, [to_email], msg.as_string())
        logger.info("Welcome email sent to %s", to_email)
        return True
    except Exception as e:  # noqa: BLE001 — never let a mail failure break signup
        logger.error("Failed to send welcome email to %s: %s", to_email, e, exc_info=True)
        return False