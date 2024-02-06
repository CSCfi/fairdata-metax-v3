from typing import List

from django.conf import settings
from django.core.mail import EmailMessage


def send_mail(subject: str, body: str, recipients: List[str], reply_to: str = None) -> int:
    """Send an email with METAX_EMAIL_SENDER as the sender."""
    email = EmailMessage(
        subject=subject,
        body=body,
        to=recipients,
        from_email=settings.METAX_EMAIL_SENDER,
        reply_to=[reply_to],
    )
    email.send()
