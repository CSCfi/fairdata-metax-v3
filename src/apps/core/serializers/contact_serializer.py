from django.utils import timezone
from rest_framework import serializers

from apps.common.helpers import format_multiline
from apps.common.mail import send_mail
from apps.common.serializers.fields import ListValidChoicesField
from apps.core.models import Dataset, DatasetActor


class ContactResponseSerializer(serializers.Serializer):
    recipient_count = serializers.IntegerField(read_only=True)


class ContactRolesSerializer(serializers.Serializer):
    """Dataset role email information serializer.

    Serializes dataset instance into a dict of role to boolean mappings
    that tells if there exists one or more email addresses for a role.
    """

    def get_fields(self):
        return {role: serializers.BooleanField() for role, _ in DatasetActor.RoleChoices.choices}

    def to_representation(self, instance: Dataset):
        data = self.get_initial()
        for actor in instance.actors.all():
            if actor.get_email():
                for role in actor.roles:
                    data[role] = True

        return super().to_representation(instance=data)


class ContactSerializer(serializers.Serializer):
    """Send email to dataset actors with specific roles.

    Requires Dataset as "dataset" in context.
    """

    reply_to = serializers.EmailField()
    subject = serializers.CharField(min_length=1, max_length=255)
    body = serializers.CharField(min_length=1, max_length=2000)
    role = ListValidChoicesField(choices=DatasetActor.RoleChoices.choices)
    service = serializers.ChoiceField(choices=("etsin",))

    def get_recipients_for_role(self, dataset: Dataset, role: str):
        recipients = set()
        actors = dataset.actors.filter(roles__contains=[role])
        for actor in actors:
            if email := actor.get_email():
                recipients.add(email)
        return list(recipients)

    def get_message_body(
        self, dataset: Dataset, reply_to: str, user_subject: str, user_body: str
    ) -> str:
        """Create body for an email message to be sent.

        Arguments:
            persistent_identifier (str): Preferred identifier of dataset.
            user_email (str): The email of the sender.
            user_subject (str): Email subject.
            user_body (str): Email body.

        Returns:
            str: Email message body with all arguments.

        """
        now = timezone.now()
        identifier = dataset.persistent_identifier or dataset.id

        meta_en = format_multiline(
            """
            The message below was sent via Fairdata Etsin Service \\
            on {date:%B} {date.day}, {date.year}.
            It concerns a dataset with identifier "{identifier}".
            Original sender: {reply_to}.

            Note!
            This message was sent as a notification from the Etsin Service.
            Do not reply to the sender of this message but directly to the \\
            original sender's email: {reply_to}.
            """,
            date=now,
            identifier=identifier,
            reply_to=reply_to,
        )

        meta_fi = format_multiline(
            """
            Allaoleva viesti on lähetetty Fairdata Etsin -palvelun kautta \\
            {date.day}.{date.month}.{date.year}.
            Viesti koskee tutkimusaineistoa, jonka tunniste on "{identifier}".
            Alkuperäinen lähettäjä: {reply_to}.

            Huom!
            Tämän viestin lähetti Etsin-palvelu.
            Älä vastaa suoraan tämän viestin lähettäjälle, \\
            vaan alkuperäiselle viestin lähettäjälle: {reply_to}.
            """,
            date=now,
            identifier=identifier,
            reply_to=reply_to,
        )

        msg = "Subject / Aihe: {0}\nMessage / Viesti: {1}".format(user_subject, user_body)
        return "{0}\n--------------\n\n{1}\n--------------\n\n{2}".format(meta_en, meta_fi, msg)

    def get_message_subject(self):
        """Get email message subject."""
        return "Message from Etsin / Viesti Etsimestä"

    def save(self) -> int:
        """Send message to dataset actors.

        Returns:
            The number of recipients.
        """
        dataset = self.context["dataset"]
        reply_to = self.validated_data["reply_to"]
        subject = self.get_message_subject()
        body = self.get_message_body(
            dataset,
            reply_to=reply_to,
            user_subject=self.validated_data["subject"],
            user_body=self.validated_data["body"],
        )

        recipients = self.get_recipients_for_role(
            dataset=dataset, role=self.validated_data["role"]
        )

        send_mail(subject=subject, body=body, recipients=recipients, reply_to=reply_to)
        return len(recipients)
