import uuid
from typing import Tuple

from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.utils.translation import gettext as _
from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from simple_history.models import HistoricalRecords

from apps.common.helpers import single_translation
from apps.common.models import CustomSoftDeletableModel, SystemCreatorBaseModel
from apps.common.serializers.fields import MultiLanguageField


class ContractContact(models.Model):
    """Contract contact information (http://iow.csc.fi/ns/jhs#Yhteystiedot)
    name          http://iow.csc.fi/ns/jhs#nimi
    phone         http://iow.csc.fi/ns/jhs#puhelinnumero
    email         http://iow.csc.fi/ns/jhs#sahkopostiosoite
    """

    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=64, blank=True)
    contract = models.ForeignKey("Contract", related_name="contact", on_delete=models.CASCADE)

    class Meta:
        ordering = ["name", "email", "id"]


class ContractService(models.Model):
    """Contract related service: (http://iow.csc.fi/ns/tipa#Service)

    Attributes:
        identifier    http://purl.org/dc/terms/identifier
        name          http://purl.org/dc/terms/title
    """

    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)

    identifier = models.CharField(max_length=64)
    name = models.CharField(max_length=200)
    contract = models.ForeignKey(
        "Contract", related_name="related_service", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["name", "identifier"]


class Contract(SystemCreatorBaseModel, CustomSoftDeletableModel):
    """Preservation contract.

    Contract (http://iow.csc.fi/ns/mad#Contract) attributes:
       title                     http://purl.org/dc/terms/title
       contract_identifier       http://purl.org/dc/terms/identifier
       quota                     http://iow.csc.fi/ns/mad#quota
       validity                  http://iow.csc.fi/ns/mad#validity
       created                   http://purl.org/dc/terms/created
       modified                  http://purl.org/dc/terms/modified
       description               http://purl.org/dc/terms/description
       contact (one-to-many)         http://iow.csc.fi/ns/jhs#yhteystieto
       related_service (one-to-many) http://iow.csc.fi/ns/jhs#liittyy

    ResearchOrganization (http://iow.csc.fi/ns/tutkimus#Tutkimusorganisaatio) attributes:
       organization_identifier   http://iow.csc.fi/ns/tutkimus#tutkimusorganisaatiotunniste
       organization_name         http://iow.csc.fi/ns/jhs#nimi

    Validity ("http://iow.csc.fi/ns/mad#validity) attributes:
       validity_start_date       http://iow.csc.fi/ns/jhs#alkamispaivamaara
       validity_end_date         http://iow.csc.fi/ns/jhs#paattymispaivamaara

    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legacy_id = models.BigIntegerField(null=True, unique=True)

    contract_identifier = models.CharField(max_length=64)
    title = HStoreField(help_text='example: {"en":"title", "fi":"otsikko"}')
    description = HStoreField(
        help_text='example: {"en":"description", "fi":"kuvaus"}', null=True, blank=True
    )
    quota = models.BigIntegerField()
    created = models.DateTimeField()
    modified = models.DateTimeField()

    # Organization
    organization_identifier = models.CharField(max_length=200, null=True, blank=True)
    organization_name = models.CharField(max_length=200)

    # Validity
    validity_start_date = models.DateField()
    validity_end_date = models.DateField(blank=True, null=True)

    # Internal modification timestamps
    record_created = AutoCreatedField(_("created"))
    record_modified = AutoLastModifiedField(_("modified"))

    history = HistoricalRecords()

    class Meta:
        ordering = ["record_created", "id"]
        constraints = (
            models.UniqueConstraint(
                fields=["contract_identifier"],
                condition=models.Q(removed__isnull=True),
                name="%(app_label)s_%(class)s_unique_contract_identifier",
            ),
        )

    @classmethod
    def create_or_update_from_legacy(cls, legacy_contract: dict) -> Tuple["Contract", bool]:
        from apps.core.serializers.contract_serializers import LegacyContractSerializer

        serializer = LegacyContractSerializer(data=legacy_contract)
        serializer.is_valid(raise_exception=True)
        existing = Contract.all_objects.filter(
            legacy_id=serializer.validated_data.get("legacy_id")
        ).first()
        serializer.instance = existing
        return serializer.save(), not existing

    def to_legacy(self) -> dict:
        from apps.core.serializers.contract_serializers import LegacyContractSerializer

        serializer = LegacyContractSerializer(instance=self)
        return serializer.data
