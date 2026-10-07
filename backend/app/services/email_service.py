import abc
import json
import logging
import re
import smtplib
import threading
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to_email: str
    subject: str
    html_body: str
    text_body: str
    from_email: Optional[str] = None


class BaseEmailProvider(abc.ABC):
    @abc.abstractmethod
    def send(self, message: EmailMessage) -> bool:
        """Send an email message."""
        pass


class TestEmailProvider(BaseEmailProvider):
    """In-memory provider for automated tests and local verification without real external network dispatch."""

    def __init__(self):
        self.sent_emails: List[EmailMessage] = []

    def send(self, message: EmailMessage) -> bool:
        self.sent_emails.append(message)
        logger.info(f"[TestEmailProvider] Recorded email to {message.to_email}: {message.subject}")
        return True

    def clear(self):
        self.sent_emails.clear()


class SMTPProvider(BaseEmailProvider):
    """Transactional email provider using standard SMTP/TLS (supporting ports 587, 465, 25)."""

    def send(self, message: EmailMessage) -> bool:
        if not settings.SMTP_HOST:
            logger.error("[SMTPProvider] SMTP_HOST not configured. Email dispatch aborted.")
            raise RuntimeError("SMTP email provider is not configured. Please set SMTP_HOST in environment variables.")

        from_addr = message.from_email or settings.EMAIL_FROM
        mime_msg = MIMEMultipart("alternative")
        mime_msg["Subject"] = message.subject
        mime_msg["From"] = from_addr
        mime_msg["To"] = message.to_email

        part1 = MIMEText(message.text_body, "plain", "utf-8")
        part2 = MIMEText(message.html_body, "html", "utf-8")
        mime_msg.attach(part1)
        mime_msg.attach(part2)

        try:
            # Port 465 uses SSL directly (SMTPS); Port 587/25 uses STARTTLS
            if settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                if settings.SMTP_TLS:
                    server.starttls()

            with server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(from_addr, [message.to_email], mime_msg.as_string())
            logger.info(f"[SMTPProvider] Successfully dispatched email to recipient")
            return True
        except Exception as exc:
            # Never log SMTP passwords or raw email tokens
            logger.error("[SMTPProvider] Failed to dispatch email: %s", type(exc).__name__)
            raise RuntimeError(f"SMTP delivery failed: {type(exc).__name__}")


def parse_sender_info(raw_sender: Optional[str], default_name: str = "NEST") -> tuple[str, str]:
    """Extract (email, name) from sender string which may be 'Name <email>' or just 'email'."""
    if not raw_sender:
        return ("", default_name)
    cleaned = raw_sender.strip().strip("'\"")
    if "<" in cleaned and ">" in cleaned:
        name_part = cleaned.split("<")[0].strip().strip("'\"")
        email_part = cleaned.split("<")[1].split(">")[0].strip()
        return (email_part, name_part or default_name)
    return (cleaned, default_name)


class BrevoProvider(BaseEmailProvider):
    """Transactional email provider via Brevo (formerly Sendinblue) v3 REST API."""

    def send(self, message: EmailMessage) -> bool:
        api_key = settings.BREVO_API_KEY
        if not api_key:
            err_msg = "Brevo provider selected, but BREVO_API_KEY is not configured in environment variables."
            logger.error("[BrevoProvider] %s", err_msg)
            raise RuntimeError(err_msg)

        sender_email, parsed_name = parse_sender_info(
            message.from_email or settings.EMAIL_FROM,
            default_name=settings.EMAIL_FROM_NAME or "NEST",
        )
        sender_name = settings.EMAIL_FROM_NAME or parsed_name or "NEST"

        if not sender_email:
            err_msg = "Brevo email dispatch failed: EMAIL_FROM is not configured."
            logger.error("[BrevoProvider] %s", err_msg)
            raise RuntimeError(err_msg)

        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "NEST-Platform/1.0",
        }
        payload = {
            "sender": {
                "name": sender_name,
                "email": sender_email,
            },
            "to": [
                {"email": message.to_email}
            ],
            "subject": message.subject,
            "htmlContent": message.html_body,
        }
        if message.text_body:
            payload["textContent"] = message.text_body

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_bytes = resp.read()
                resp_json = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
                msg_id = resp_json.get("messageId") or resp_json.get("id")
                if 200 <= resp.status < 300:
                    logger.info(f"[BrevoProvider] Dispatched email (Brevo MessageId: {msg_id})")
                    return True
                logger.error(f"[BrevoProvider] Unexpected status {resp.status}")
                raise RuntimeError(f"Brevo API returned unexpected status {resp.status}")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            logger.error(f"[BrevoProvider] HTTP error {exc.code}")
            try:
                err_json = json.loads(err_body)
                brevo_msg = err_json.get("message") or err_json.get("code") or "Dispatch rejected by provider"
            except Exception:
                brevo_msg = "Email dispatch rejected by provider"
            # Never leak tokens or credentials
            raise RuntimeError(f"Email delivery error ({exc.code}): {brevo_msg}")
        except Exception as exc:
            logger.error("[BrevoProvider] Failed to send email: %s", type(exc).__name__)
            raise RuntimeError(f"Email delivery failed: {type(exc).__name__}")


class ResendProvider(BaseEmailProvider):
    """Transactional email provider via Resend HTTP REST API."""

    def send(self, message: EmailMessage) -> bool:
        api_key = settings.EMAIL_API_KEY or settings.RESEND_API_KEY
        if not api_key:
            err_msg = "Resend provider selected, but RESEND_API_KEY is not configured in environment variables."
            logger.error("[ResendProvider] %s", err_msg)
            raise RuntimeError(err_msg)

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "NEST-Platform/1.0",
        }
        sender = message.from_email or settings.EMAIL_FROM
        payload = {
            "from": sender,
            "to": [message.to_email],
            "subject": message.subject,
            "html": message.html_body,
            "text": message.text_body,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_bytes = resp.read()
                resp_json = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
                msg_id = resp_json.get("id")
                if 200 <= resp.status < 300:
                    logger.info(f"[ResendProvider] Dispatched email (Resend ID: {msg_id})")
                    return True
                logger.error(f"[ResendProvider] Unexpected status {resp.status}")
                raise RuntimeError(f"Resend API returned unexpected status {resp.status}")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            logger.error(f"[ResendProvider] HTTP error {exc.code}")
            try:
                err_json = json.loads(err_body)
                resend_msg = err_json.get("message") or err_json.get("name") or "Dispatch rejected by provider"
            except Exception:
                resend_msg = "Email dispatch rejected by provider"

            # Check for Resend testing domain sandbox restriction:
            # When using onboarding@resend.dev without a verified domain, Resend rejects any recipient
            # other than the registered account owner with:
            # "You can only send testing emails to your own email address (owner@example.com)..."
            if exc.code == 403 and "to your own email address" in resend_msg:
                owner_match = re.search(r"\(([^)]+@[^)]+)\)", resend_msg)
                sandbox_owner = owner_match.group(1) if owner_match else None
                if sandbox_owner and sandbox_owner.lower() != message.to_email.lower():
                    logger.warning(
                        "[ResendProvider] Resend sandbox restriction active (no verified domain). "
                        "Redirecting verification email for '%s' to sandbox owner '%s'.",
                        message.to_email,
                        sandbox_owner,
                    )
                    sandbox_payload = {
                        "from": sender,
                        "to": [sandbox_owner],
                        "subject": f"[Sandbox for {message.to_email}] {message.subject}",
                        "html": (
                            f"<div style='background:#fef3c7;border:1px solid #f59e0b;padding:12px;border-radius:8px;margin-bottom:16px;font-size:13px;color:#92400e;'>"
                            f"<strong>Resend Testing Sandbox Notice:</strong> This email was originally addressed to <code>{message.to_email}</code>. "
                            f"Because the Resend account is using the sandbox domain (<code>onboarding@resend.dev</code>), Resend only delivers to your account owner address."
                            f"</div>"
                        ) + message.html_body,
                        "text": f"[Sandbox Notice: Intended recipient: {message.to_email}]\n\n" + message.text_body,
                    }
                    sandbox_data = json.dumps(sandbox_payload).encode("utf-8")
                    sandbox_req = urllib.request.Request(url, data=sandbox_data, headers=headers, method="POST")
                    try:
                        with urllib.request.urlopen(sandbox_req, timeout=10) as s_resp:
                            if 200 <= s_resp.status < 300:
                                s_bytes = s_resp.read()
                                s_json = json.loads(s_bytes.decode("utf-8")) if s_bytes else {}
                                logger.info(
                                    "[ResendProvider] Dispatched sandbox email to %s (Resend ID: %s)",
                                    sandbox_owner,
                                    s_json.get("id"),
                                )
                                return True
                    except Exception as s_exc:
                        logger.error("[ResendProvider] Failed sandbox fallback send: %s", type(s_exc).__name__)

            # Never leak tokens or credentials
            raise RuntimeError(f"Email delivery error ({exc.code}): {resend_msg}")
        except Exception as exc:
            logger.error("[ResendProvider] Failed to send email: %s", type(exc).__name__)
            raise RuntimeError(f"Email delivery failed: {type(exc).__name__}")


class SendGridProvider(BaseEmailProvider):
    """Transactional email provider via SendGrid v3 Mail API."""

    def send(self, message: EmailMessage) -> bool:
        if not settings.EMAIL_API_KEY:
            logger.warning("[SendGridProvider] EMAIL_API_KEY not configured. Dispatch skipped.")
            return False

        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {settings.EMAIL_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "personalizations": [{"to": [{"email": message.to_email}]}],
            "from": {"email": message.from_email or settings.EMAIL_FROM},
            "subject": message.subject,
            "content": [
                {"type": "text/plain", "value": message.text_body},
                {"type": "text/html", "value": message.html_body},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    logger.info(f"[SendGridProvider] Dispatched email to {message.to_email}")
                    return True
                return False
        except Exception as exc:
            logger.error(f"[SendGridProvider] Failed to send to {message.to_email}: {exc}")
            raise


# Singleton instance of test provider for inspection in tests
test_email_provider = TestEmailProvider()


def get_email_provider() -> BaseEmailProvider:
    """Factory to retrieve configured email provider based on environment and settings."""
    provider_type = settings.EMAIL_PROVIDER.lower().strip()

    if settings.ENVIRONMENT == "production" and provider_type == "test":
        raise RuntimeError("Insecure configuration: TestEmailProvider cannot be used in production environment.")

    if provider_type == "test":
        return test_email_provider
    elif provider_type == "brevo":
        return BrevoProvider()
    elif provider_type == "resend":
        return ResendProvider()
    elif provider_type == "sendgrid":
        return SendGridProvider()
    elif provider_type == "smtp":
        # If SMTP is selected but no host configured in dev/test, fallback cleanly to test provider
        if not settings.SMTP_HOST and settings.ENVIRONMENT != "production":
            return test_email_provider
        return SMTPProvider()
    else:
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(f"Unsupported EMAIL_PROVIDER '{provider_type}' in production.")
        return test_email_provider


def render_verification_email(name: str, verification_url: str, expire_hours: int = 24) -> tuple[str, str]:
    """Generate HTML and plain text email content for email verification."""
    subject = "Verify your email address — NEST"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify your email address — NEST</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    <!-- Header -->
    <tr>
      <td style="padding: 32px 32px 24px; background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%); text-align: center;">
        <h1 style="margin: 0; color: #ffffff; font-size: 26px; font-weight: 700; letter-spacing: -0.5px;">NEST</h1>
        <p style="margin: 4px 0 0; color: #ccfbf1; font-size: 14px;">Find Your People. Find Your Place.</p>
      </td>
    </tr>
    <!-- Body -->
    <tr>
      <td style="padding: 32px;">
        <h2 style="margin: 0 0 16px; font-size: 20px; font-weight: 600; color: #0f172a;">Welcome to NEST, {name}!</h2>
        <p style="margin: 0 0 20px; font-size: 15px; line-height: 1.6; color: #334155;">
          Thank you for creating an account on NEST. To protect our community and ensure all participants are real people with verified mailboxes, please confirm your email address.
        </p>
        <!-- CTA Button -->
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin: 28px 0;">
          <tr>
            <td align="center">
              <a href="{verification_url}" target="_blank" style="display: inline-block; padding: 14px 32px; background-color: #0d9488; color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; border-radius: 10px; box-shadow: 0 2px 4px rgba(13, 148, 136, 0.3);">
                Verify Email Address
              </a>
            </td>
          </tr>
        </table>
        <p style="margin: 0 0 12px; font-size: 13px; line-height: 1.5; color: #64748b;">
          If the button above does not work, copy and paste this verification link into your browser:
        </p>
        <p style="margin: 0 0 24px; font-size: 12px; line-height: 1.4; color: #0d9488; word-break: break-all; background-color: #f1f5f9; padding: 12px; border-radius: 8px;">
          {verification_url}
        </p>
        <p style="margin: 0; font-size: 13px; color: #94a3b8; line-height: 1.5;">
          This verification link is single-use and will expire in <strong>{expire_hours} hours</strong>.<br>
          If you did not register for an account on NEST, please disregard this email.
        </p>
      </td>
    </tr>
    <!-- Footer -->
    <tr>
      <td style="padding: 20px 32px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8;">
        © {settings.PROJECT_NAME}. Built with privacy and trust.
      </td>
    </tr>
  </table>
</body>
</html>
"""

    text_content = f"""Welcome to NEST, {name}!

Please verify your email address to activate your NEST account and participate in your local community:

{verification_url}

This link is single-use and will expire in {expire_hours} hours.

If you did not register for an account on NEST, please ignore this email.
"""

    return html_content, text_content


def send_verification_email(to_email: str, name: str, verification_url: str) -> bool:
    """Compose and send verification email using the configured email provider."""
    html_body, text_body = render_verification_email(
        name=name,
        verification_url=verification_url,
        expire_hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
    )
    message = EmailMessage(
        to_email=to_email,
        subject="Verify your email address — NEST",
        html_body=html_body,
        text_body=text_body,
    )
    provider = get_email_provider()
    return provider.send(message)


def render_nearby_request_email(
    helper_name: str,
    request_title: str,
    coarse_location: str,
    category: str,
    request_url: str,
) -> tuple[str, str]:
    """Render notification email for an eligible helper when a new request is posted nearby."""
    subject = "New request near you — NEST"
    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>New request near you — NEST</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    <tr>
      <td style="padding: 28px 32px; background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%); text-align: center;">
        <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">NEST</h1>
        <p style="margin: 4px 0 0; color: #ccfbf1; font-size: 13px;">Find Your People. Find Your Place.</p>
      </td>
    </tr>
    <tr>
      <td style="padding: 32px;">
        <h2 style="margin: 0 0 12px; font-size: 18px; color: #0f172a;">Hello {helper_name},</h2>
        <p style="margin: 0 0 20px; font-size: 14px; line-height: 1.6; color: #334155;">
          A newcomer in your area has posted a community request that matches your skills.
        </p>
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; margin-bottom: 24px;">
          <p style="margin: 0 0 8px; font-size: 14px; font-weight: 600; color: #0f172a;">"{request_title}"</p>
          <div style="font-size: 13px; color: #64748b; line-height: 1.5;">
            <span><strong>Category:</strong> {category}</span><br>
            <span><strong>Approximate Area:</strong> {coarse_location}</span>
          </div>
        </div>
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin: 24px 0;">
          <tr>
            <td align="center">
              <a href="{request_url}" target="_blank" style="display: inline-block; padding: 12px 28px; background-color: #0d9488; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 600; border-radius: 8px;">
                View Request on NEST
              </a>
            </td>
          </tr>
        </table>
        <p style="margin: 0; font-size: 12px; color: #94a3b8; line-height: 1.5;">
          No exact private home coordinates are ever shared. You received this notification because your helper profile indicates availability in this neighborhood.
        </p>
      </td>
    </tr>
    <tr>
      <td style="padding: 16px 32px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8;">
        © {settings.PROJECT_NAME}. Community safety & privacy first.
      </td>
    </tr>
  </table>
</body>
</html>"""
    text_body = f"""Hello {helper_name},

A newcomer in your area has posted a community request matching your profile:

"{request_title}"
Category: {category}
Area: {coarse_location}

View this request on NEST:
{request_url}

No exact private home coordinates are shared.
"""
    return html_body, text_body


def render_new_message_email(
    recipient_name: str,
    sender_name: str,
    message_preview: str,
    conversation_url: str,
) -> tuple[str, str]:
    """Render notification email when a user receives a new message while offline."""
    subject = f"You have a new message on NEST from {sender_name}"
    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>New Message on NEST</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    <tr>
      <td style="padding: 28px 32px; background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%); text-align: center;">
        <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">NEST</h1>
        <p style="margin: 4px 0 0; color: #ccfbf1; font-size: 13px;">Find Your People. Find Your Place.</p>
      </td>
    </tr>
    <tr>
      <td style="padding: 32px;">
        <h2 style="margin: 0 0 12px; font-size: 18px; color: #0f172a;">Hello {recipient_name},</h2>
        <p style="margin: 0 0 16px; font-size: 14px; line-height: 1.6; color: #334155;">
          <strong>{sender_name}</strong> sent you a message on NEST while you were away:
        </p>
        <div style="background-color: #f1f5f9; border-left: 4px solid #0d9488; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px; font-size: 14px; color: #1e293b; font-style: italic;">
          "{message_preview}"
        </div>
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin: 24px 0;">
          <tr>
            <td align="center">
              <a href="{conversation_url}" target="_blank" style="display: inline-block; padding: 12px 28px; background-color: #0d9488; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 600; border-radius: 8px;">
                Reply on NEST
              </a>
            </td>
          </tr>
        </table>
        <p style="margin: 0; font-size: 12px; color: #94a3b8; line-height: 1.5;">
          To preserve personal privacy, keep communications within NEST.
        </p>
      </td>
    </tr>
    <tr>
      <td style="padding: 16px 32px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8;">
        © {settings.PROJECT_NAME}. Community safety & privacy first.
      </td>
    </tr>
  </table>
</body>
</html>"""
    text_body = f"""Hello {recipient_name},

{sender_name} sent you a message on NEST:

"{message_preview}"

Open your conversation on NEST:
{conversation_url}
"""
    return html_body, text_body


def render_connection_event_email(
    recipient_name: str,
    event_title: str,
    event_message: str,
    action_url: str,
    action_label: str = "Open NEST",
) -> tuple[str, str]:
    """Render notification email for lifecycle events like connection requested or accepted."""
    subject = f"{event_title} — NEST"
    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{event_title} — NEST</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    <tr>
      <td style="padding: 28px 32px; background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%); text-align: center;">
        <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">NEST</h1>
        <p style="margin: 4px 0 0; color: #ccfbf1; font-size: 13px;">Find Your People. Find Your Place.</p>
      </td>
    </tr>
    <tr>
      <td style="padding: 32px;">
        <h2 style="margin: 0 0 12px; font-size: 18px; color: #0f172a;">Hello {recipient_name},</h2>
        <p style="margin: 0 0 20px; font-size: 14px; line-height: 1.6; color: #334155;">
          {event_message}
        </p>
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin: 24px 0;">
          <tr>
            <td align="center">
              <a href="{action_url}" target="_blank" style="display: inline-block; padding: 12px 28px; background-color: #0d9488; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 600; border-radius: 8px;">
                {action_label}
              </a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
    <tr>
      <td style="padding: 16px 32px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8;">
        © {settings.PROJECT_NAME}. Community safety & privacy first.
      </td>
    </tr>
  </table>
</body>
</html>"""
    text_body = f"""Hello {recipient_name},

{event_message}

View on NEST:
{action_url}
"""
    return html_body, text_body


def dispatch_email_async(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    idempotency_key: str,
    recipient_id: uuid.UUID,
    notification_type: str,
    metadata_payload: Optional[dict] = None,
) -> None:
    """
    Asynchronously and idempotently deliver an email notification without blocking caller.
    Records delivery state in email_notifications table.
    """
    def _worker():
        from app.db.database import SessionLocal
        from app.models.email_notification import EmailNotification, EmailDeliveryStatus
        db = SessionLocal()
        try:
            # Check idempotency: if record already exists, skip sending
            existing = (
                db.query(EmailNotification)
                .filter(EmailNotification.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                if existing.status in [EmailDeliveryStatus.SENT.value, EmailDeliveryStatus.SKIPPED_ONLINE.value]:
                    logger.info(f"[EmailService] Idempotent skip for key: {idempotency_key}")
                    return
                record = existing
            else:
                record = EmailNotification(
                    idempotency_key=idempotency_key,
                    recipient_id=recipient_id,
                    recipient_email=to_email,
                    notification_type=notification_type,
                    subject=subject,
                    status=EmailDeliveryStatus.PENDING.value,
                    metadata_payload=metadata_payload or {},
                )
                db.add(record)
                db.commit()
                db.refresh(record)

            # Dispatch email through configured provider
            msg = EmailMessage(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            provider = get_email_provider()
            success = provider.send(msg)

            if success:
                record.status = EmailDeliveryStatus.SENT.value
                record.sent_at = datetime.now(timezone.utc)
                record.error_message = None
                db.commit()
                logger.info(f"[EmailService] Successfully delivered email {notification_type} to {to_email}")
            else:
                record.status = EmailDeliveryStatus.FAILED.value
                record.error_message = "Provider returned false without exception"
                db.commit()
        except Exception as exc:
            logger.warning(f"[EmailService] Delivery failed for {notification_type} to {to_email}: {exc}")
            try:
                if 'record' in locals():
                    record.status = EmailDeliveryStatus.FAILED.value
                    record.error_message = str(exc)[:1000]
                    db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

