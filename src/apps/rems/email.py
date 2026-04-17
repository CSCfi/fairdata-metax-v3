import logging
from dataclasses import dataclass
from enum import Enum

from django.conf import settings

from apps.common.helpers import (
    deduplicate_list,
    format_exception,
    format_multiline,
    single_translation,
)
from apps.common.mail import send_mail
from apps.users.models import AdminOrganization

logger = logging.getLogger()


class Recipient(Enum):
    APPLICANT = "applicant"
    HANDLER = "handler"


class Event(Enum):
    SUBMITTED = "application.event/submitted"
    APPROVED = "application.event/approved"
    REJECTED = "application.event/rejected"
    RETURNED = "application.event/returned"
    CLOSED = "application.event/closed"
    REVOKED = "application.state/revoked"


@dataclass
class REMSEmail:
    recipients: list[Recipient]
    subject: str
    body: str


event_notification_labels = {
    Event.APPROVED: {
        "en": "approved",
        "fi": "hyväksytty",
    },
    Event.REJECTED: {
        "en": "rejected",
        "fi": "hylätty",
    },
    Event.RETURNED: {
        "en": "returned for changes",
        "fi": "palautettu muutoksia varten",
    },
    Event.CLOSED: {
        "en": "closed",
        "fi": "suljettu",
    },
    Event.REVOKED: {
        "fi": "peruttu",
        "en": "revoked",
    },
}


email_new_application = REMSEmail(
    recipients=[Recipient.HANDLER],
    subject=(
        "Uusi datan käyttöluvan pyyntö Fairdata Etsimestä / "
        "New Data Use Application from Fairdata Etsin"
    ),
    body=format_multiline(
        """
        Fairdata Etsimestä on saapunut uusi datan käyttöluvan pyyntö.
        {link_fi}

        Voit tarkastella kaikkia käyttöluvan pyyntöjä Qvaimen \\
        välilehdellä "Datan luvituksen hakemukset".
        –

        Tämä viesti on lähetetty organisaatiosi kuvailutietojen pääkäyttäjille (Qvain Adminit).

        Organisaatiosi pääkäyttäjät löytyvät täältä: {admin_organization_info_url}
        Jos haluat päivittää pääkäyttäjälistaa, \\
        olethan yhteydessä Fairdata-palvelun käyttäjätukeen: {fairdata_support_email}.

        -----------------

        A new data use application has been submitted via Fairdata Etsin.
        {link_en}

        You can view all applications on the "Data access applications" tab in Qvain.
        –

        This message has been sent to the Metadata Administrators \\
        (Qvain Admins) of your organization.

        You can find the list of Administrators here: {admin_organization_info_url}
        If you need to update your organization’s Administrators, \\
        please contact Fairdata Support at {fairdata_support_email}.
        """,
    ),
)

email_application_event = REMSEmail(
    recipients=[Recipient.APPLICANT],
    subject=(
        "Datan käyttöluvan pyyntösi on {event_label_fi} / Your data use request has been {event_label_en}"
    ),
    body=format_multiline(
        """
        Hei,

        Datan käyttöluvan pyyntösi Fairdata Etsimessä on {event_label_fi}.
        Pyyntöäsi käsitteli aineiston tietoihin merkityn organisaation Data Access Committee.

        Voit tarkastella päätöstä Etsimestä ko. aineiston lupapainikkeen takaa.

        {link_fi}

        –
        Hi,

        Your data use request submitted through Fairdata Etsin has now been {event_label_en}.
        The request was reviewed by the Data Access Committee of the organization identified in the dataset information.

        You can view the decision in Etsin via the dataset's "Ask for Access" button.

        {link_en}
        """
    ),
)


emails = {
    Event.SUBMITTED: email_new_application,
    Event.APPROVED: email_application_event,
    Event.REJECTED: email_application_event,
    Event.RETURNED: email_application_event,
    Event.CLOSED: email_application_event,
    Event.REVOKED: email_application_event,
}


def get_handler_emails(application: dict):
    from apps.rems.rems_service import REMSService

    # Use admin organization DAC email if it exists
    service = REMSService()
    dataset = service.get_application_dataset(application)
    if dataset and (admin_org_id := dataset.metadata_owner.admin_organization):
        if admin_org := AdminOrganization.objects.filter(id=admin_org_id).first():
            if dac_email := admin_org.dac_email:
                return [dac_email]

    # No DAC email address found, email individual handlers
    excluded = {"approver-bot", "rejecter-bot", settings.REMS_USER_ID}
    handlers = application["application/workflow"]["workflow.dynamic/handlers"]
    return [
        handler["email"]
        for handler in handlers
        if handler.get("email") and handler["userid"] not in excluded
    ]


def get_application_item_info(application: dict, lang: str) -> str:
    """Returns title and link for application.

    Applications in Metax REMS should have exactly one resource,
    so we simply ignore resources after the first one.
    """
    for resource in application["application/resources"]:
        parts = []
        if title := resource.get("catalogue-item/title"):
            parts.append(single_translation(title, lang))
        if infourl := resource.get("catalogue-item/infourl"):
            parts.append(f"({single_translation(infourl, lang)})")
        return " ".join(parts)
    return ""


def send_rems_application_email(application: dict, email: REMSEmail, event: Event):
    """Send message to dataset actors.

    Returns:
        The number of recipients.
    """

    recipients = []
    if Recipient.APPLICANT in email.recipients:
        recipients.append(application["application/applicant"]["email"])
    if Recipient.HANDLER in email.recipients:
        recipients.extend(get_handler_emails(application))
    recipients = deduplicate_list(recipients)

    link_en = ""
    link_fi = ""
    if info := get_application_item_info(application, "en"):
        link_en = f"Dataset: {info}"
    if info := get_application_item_info(application, "fi"):
        link_fi = f"Aineisto: {info}"

    event_label_en = ""
    event_label_fi = ""
    if labels := event_notification_labels.get(event):
        event_label_en = labels.get("en", "")
        event_label_fi = labels.get("fi", "")

    context = {
        "link_fi": link_fi,
        "link_en": link_en,
        "event_label_fi": event_label_fi,
        "event_label_en": event_label_en,
        "admin_organization_info_url": settings.REMS_ADMIN_ORGANIZATION_INFO_URL,
        "fairdata_support_email": settings.REMS_FAIRDATA_SUPPORT_EMAIL,
    }
    subject = email.subject.format(**context)
    body = email.body.format(**context)

    send_mail(subject=subject, body=body, recipients=recipients)


def send_emails_for_event(application: dict, event: Event):
    application_id = application["application/id"]
    try:
        if email := emails.get(event):
            send_rems_application_email(application, email, event)
    except Exception as e:
        msg = format_exception(e)
        logger.error(f"Error sending emails for {application_id=}, {event=}: {msg}")
