import abc
import json
import logging
import smtplib
import urllib.error
import urllib.request
from dataclasses import dataclass
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
