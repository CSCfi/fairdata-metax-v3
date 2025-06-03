import uuid

from django.db import models

from apps.common.models import AbstractBaseModel


class EntityType(models.TextChoices):
    ORGANIZATION = "organization"
    USER = "user"
    FORM = "form"
    WORKFLOW = "workflow"
    LICENSE = "license"
    RESOURCE = "resource"
    CATALOGUE_ITEM = "catalogue-item"
    APPLICATION = "application"
    ENTITLEMENT = "entitlement"


# Entities that don't have Django models in Metax
unmanaged_entities = {EntityType.APPLICATION, EntityType.ENTITLEMENT}


class REMSEntity(AbstractBaseModel):
    """Generic REMS entity model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(blank=True, null=True)  # Metax key to the rems entity e.g. dataset.id
    rems_id = models.IntegerField()  # Internal id of entity in REMS
    rems_id_field = "id"  # Name of id field in REMS requests
    entity_type: EntityType

    class Meta(AbstractBaseModel.Meta):
        abstract = True
        constraints = [
            # Key should be unique among non-removed entities
            models.UniqueConstraint(
                fields=["key"],
                condition=models.Q(removed__isnull=True),
                name="%(app_label)s_%(class)s_unique_key",
            ),
        ]

    def __str__(self):
        return f"{self.entity_type}:{self.key} rems_id={self.rems_id}"


class REMSUser(REMSEntity):
    """REMS User

    User has:
    - id (set by Metax, some ids like "approve-bot" have a special meaning)
    - name
    - email
    - organizations (optional)
    """

    rems_id = models.CharField()  # User id, e.g. "owner"
    rems_id_field = "userid"
    entity_type = EntityType.USER


class REMSOrganization(REMSEntity):
    """REMS Organization

    Organization has:
    - id (set by Metax)
    - short name (en, fi)
    - name (en, fi)
    - owners (optional list of owner users)
    """

    rems_id = models.CharField()  # Organization identifier, e.g. "csc"
    rems_id_field = "organization/id"
    entity_type = EntityType.ORGANIZATION


class REMSWorkflow(REMSEntity):
    """REMS Workflow

    Workflow has:
    - organization
    - title (not visible to applicants)
    - workflow type
    - handlers (list of users who handle applications, may be "approve-bot" to approve automatically)
    - forms (optional, applies to all catalogue items using workflow)
    - licenses (optional, applies to all catalogue items using workflow)
    - anonymized handling flag (enable to hide name and email of handlers)
    """

    entity_type = EntityType.WORKFLOW
    metax_organization = models.CharField(
        null=True, blank=True
    )  # Id of the organization the workflow belongs to in Metax, not the REMS organization


class REMSForm(REMSEntity):
    """REMS Form

    Form has:
    - organization
    - title (en, fi)
    - fields
    """

    entity_type = EntityType.FORM


class REMSLicense(REMSEntity):
    """REMS License

    License has:
    - organization
    - license type (link, text, attachment)
    - localizations (en, fi)
      - title text
      - text content (or link to license text)
      - attachment (when type is attachment)
    """

    entity_type = EntityType.LICENSE
    custom_license_dataset = models.ForeignKey(
        "core.Dataset",
        related_name="custom_rems_licenses",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    is_data_access_terms = models.BooleanField(
        default=False, help_text="True when license is generated from data_access_terms."
    )


class REMSResource(REMSEntity):
    """REMS Resource

    Resource has:
    - organization
    - resource identifier (e.g. dataset id)
    - licenses (optional)
    """

    entity_type = EntityType.RESOURCE


class REMSCatalogueItem(REMSEntity):
    """REMS Catalogue item

    Applications are made for catalogue items. A catalogue item has:
    - organization
    - workflow
    - resource
    - localization dictionary
    - form (optional)
    """

    entity_type = EntityType.CATALOGUE_ITEM
