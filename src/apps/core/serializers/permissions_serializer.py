import logging

from rest_framework import serializers

from apps.common.helpers import format_multiline, single_translation
from apps.common.mail import send_mail
from apps.common.serializers.serializers import CommonModelSerializer, StrictSerializer
from apps.core.models import Dataset
from apps.core.models.catalog_record import DatasetPermissions
from apps.users.models import MetaxUser
from apps.users.sso_client import SSOClient

logger = logging.getLogger(__file__)


class ShareMessageSerializer(StrictSerializer):
    """Serializer for emails about shared dataset."""

    content = serializers.CharField(
        max_length=2000,
        required=False,
        allow_null=True,
        help_text="Optional content provided by user.",
    )
    service = serializers.ChoiceField(choices=("qvain",))

    def get_message_body(
        self,
        dataset: Dataset,
        sender: MetaxUser,
        recipient: MetaxUser,
        user_body: str,
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
        identifier = dataset.id

        if not user_body:
            user_body = ""
        content_sep_en = "\n\nMessage:\n" if user_body else ""
        content_sep_fi = "\n\nViesti:\n" if user_body else ""
        qvain_url = f"https://qvain.fairdata.fi/dataset/{identifier}"

        title = dataset.title
        title_en = single_translation(title, "en")
        title_fi = single_translation(title, "fi")

        msg_en = format_multiline(
            """
            User {sender} has given you ({recipient}) editing rights in Fairdata Qvain, \\
            dataset "{title}".

            {qvain_url}{content_sep}{content}
            """,
            sender=sender.username,
            recipient=recipient.username,
            title=title_en,
            content_sep=content_sep_en,
            content=user_body,
            qvain_url=qvain_url,
        )

        msg_fi = format_multiline(
            """
            Käyttäjä {sender} on antanut Fairdata Qvaimessa \\
            sinulle ({recipient}) muokkausoikeuden aineistoon "{title}".

            {qvain_url}{content_sep}{content}
            """,
            sender=sender.username,
            recipient=recipient.username,
            title=title_fi,
            content_sep=content_sep_fi,
            content=user_body,
            qvain_url=qvain_url,
        )

        return f"{msg_en}\n--------------\n\n{msg_fi}"

    def get_message_subject(self):
        """Get email message subject."""
        return (
            "You have new editing rights in Fairdata Qvain / "
            "Sinulla on uusi muokkausoikeus Qvaimessa"
        )

    def save(self, dataset: Dataset, sender: MetaxUser, recipient: MetaxUser) -> int:
        """Send message to dataset actors.

        Returns:
            The number of recipients.
        """
        subject = self.get_message_subject()
        body = self.get_message_body(
            dataset,
            sender=sender,
            recipient=recipient,
            user_body=self.validated_data.get("content"),
        )

        return send_mail(subject=subject, body=body, recipients=[recipient.email])


class DatasetPermissionsUserModelSerializer(CommonModelSerializer):
    """Serializer for users in DatasetPermissions."""

    share_message = ShareMessageSerializer(
        write_only=True, required=False, help_text="Send a message on successful share."
    )

    class Meta:
        model = MetaxUser
        fields = (
            "username",
            "fairdata_username",
            "first_name",
            "last_name",
            "email",
            "share_message",
        )
        extra_kwargs = {field: {"read_only": True} for field in fields if field != "username"}
        extra_kwargs["username"] = {"validators": []}

    def save(self, **kwargs):
        validated_data = {**self.validated_data, **kwargs}
        return self.create(validated_data)

    def create(self, validated_data):
        dataset: Dataset = validated_data.get("dataset")  # Dataset should be provided to save()
        if not dataset:
            raise ValueError("Missing dataset")
        permissions = dataset.permissions
        permissions.set_context_dataset(dataset)
        username = validated_data.get("username")
        created = False
        try:
            self.instance, created = SSOClient().get_or_create_user(username)
        except MetaxUser.DoesNotExist:
            raise serializers.ValidationError(
                {"username": f"User with username '{username}' does not exist"}
            )

        if not created:
            if self.instance in permissions.creators:
                raise serializers.ValidationError(
                    {"username": f"User '{username}' is a creator of the dataset."}
                )
            if permissions.editors.contains(self.instance):
                raise serializers.ValidationError(
                    {"username": f"User '{username}' is already an editor of the dataset."}
                )

        # Add user to editors list and send message
        self.send_message(validated_data)
        permissions.editors.add(self.instance)
        return self.instance

    def update(self, instance, validated_data):
        raise NotImplementedError("Update not supported")

    def send_message(self, validated_data):
        """Send "dataset shared" email to user."""
        if message := validated_data.get("share_message"):
            recipient = self.instance
            if not recipient.email:
                logger.warning(f"No email for user {recipient.username}, not sending message")
                return
            dataset = self.context["dataset"]
            sender = self.context["request"].user
            serializer = self.fields["share_message"]
            serializer._validated_data = message
            serializer.save(dataset=dataset, sender=sender, recipient=recipient)


class DatasetPermissionsSerializer(CommonModelSerializer):
    creators = DatasetPermissionsUserModelSerializer(many=True, read_only=True)
    editors = DatasetPermissionsUserModelSerializer(many=True, read_only=True)

    def create(self, validated_data):
        raise NotImplementedError("Serializer is read-only.")

    def update(self, instance: DatasetPermissions, validated_data):
        raise NotImplementedError("Serializer is read-only.")

    class Meta:
        model = DatasetPermissions
        fields = ["creators", "editors"]
