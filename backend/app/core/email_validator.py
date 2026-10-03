import re
from typing import Set

# RFC 5322 compatible email regex for syntax validation
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_+-]+(?:\.[a-zA-Z0-9_+-]+)*@"
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

# Comprehensive list of known disposable, temporary, and burner email provider domains
DISPOSABLE_EMAIL_DOMAINS: Set[str] = {
    # Mailinator family & public inboxes
    "mailinator.com",
    "mailinater.com",
    "mailinator2.com",
    "suremail.info",
    "spamherelots.com",
    "binkmail.com",
    "safetymail.info",
    # Guerrilla Mail family
    "guerrillamail.com",
    "guerrillamailblock.com",
    "guerrillamail.biz",
    "guerrillamail.de",
    "guerrillamail.net",
    "guerrillamail.org",
    "guerrillamail.info",
    "sharklasers.com",
    "grr.la",
    "pokemail.net",
    "spam4.me",
    # 10 Minute Mail family
    "10minutemail.com",
    "10minutemail.net",
    "10minutemail.org",
    "10minute.email",
    "10minutemailbox.com",
    # Temp-Mail family
    "tempmail.com",
    "temp-mail.org",
    "temp-mail.io",
    "tempmail.net",
    "tempmailo.com",
    "tmail.ws",
    "tempail.com",
    # YOPmail family
    "yopmail.com",
    "yopmail.fr",
    "yopmail.net",
    "cool.fr.nf",
    "jetable.fr.nf",
    "courriel.fr.nf",
    "moncourrier.fr.nf",
    "monemail.fr.nf",
    "monmail.fr.nf",
    # TrashMail family
    "trashmail.com",
    "trashmail.net",
    "trashmail.me",
    # Burner / Throwaway services
    "throwawaymail.com",
    "throwaway.email",
    "burnermail.io",
    "burnermail.com",
    "dispostable.com",
    "maildrop.cc",
    "fakemailgenerator.com",
    "emailondeck.com",
    "mytemp.email",
    "generator.email",
    "getnada.com",
    "abovethecloud.com",
    "inboxbear.com",
    "mohmal.com",
    "nada.ltd",
    "dropmail.me",
    "crazymailing.com",
    "getairmail.com",
    "mailpoof.com",
    "zillamail.com",
    "harakirimail.com",
    "byom.de",
    "inboxkitten.com",
    "tempinbox.com",
    "dayrep.com",
    "teleworm.us",
    "rhyta.com",
    "armyspy.com",
    "cuvox.de",
    "fleckens.hu",
    "gustr.com",
    "jourrapide.com",
    "superrito.com",
}


def is_disposable_email(email: str) -> bool:
    """
    Check if the provided email domain is a known disposable or burner email service.
    Handles exact domain matches and subdomains (e.g., test.mailinator.com).
    """
    if not email or "@" not in email:
        return False

    parts = email.strip().lower().split("@")
    if len(parts) != 2:
        return False

    domain = parts[1].strip()
    if not domain:
        return False

    # Check direct domain match
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        return True

    # Check parent domain match for subdomains
    domain_parts = domain.split(".")
    for i in range(1, len(domain_parts) - 1):
        parent_domain = ".".join(domain_parts[i:])
        if parent_domain in DISPOSABLE_EMAIL_DOMAINS:
            return True

    return False


def validate_email_address(email: str, allow_disposable: bool = False) -> str:
    """
    Validate email address format, length, and disposable domain status.
    Returns normalized (lowercase, trimmed) email address.
    Raises ValueError on syntax invalidity or disposable domain usage.
    """
    if not email:
        raise ValueError("Email address cannot be empty.")

    cleaned = email.strip().lower()

    if len(cleaned) < 5 or len(cleaned) > 254:
        raise ValueError("Email address length must be between 5 and 254 characters.")

    if not EMAIL_REGEX.match(cleaned):
        raise ValueError("Invalid email address format.")

    if not allow_disposable and is_disposable_email(cleaned):
        raise ValueError(
            "Disposable or temporary email addresses are not permitted. "
            "Please use a standard personal, work, or university email address."
        )

    return cleaned
