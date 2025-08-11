from dataclasses import dataclass
import logging
import traceback
from typing import TYPE_CHECKING, Iterable, List, Optional


from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from rest_framework import serializers

from apps.rems.types import ApplicationBase, ApplicationLicenseData, LicenseType
from apps.common.helpers import single_translation
from apps.common.locks import lock_rems_publish
from apps.rems.models import (
    EntityType,
    REMSCatalogueItem,
    REMSEntity,
    REMSForm,
    REMSLicense,
    REMSOrganization,
    REMSResource,
    REMSUser,
    REMSWorkflow,
)
from apps.rems.rems_session import REMSSession
from apps.users.models import MetaxUser

if TYPE_CHECKING:
    from apps.core.models import Dataset, DatasetLicense


logger = logging.getLogger(__name__)


class REMSOperation(models.TextChoices):
    create = "create"  # create new entity (archive old if any)
    edit = "edit"  # update existing entity (allowed only for some fields)
    keep = "keep"  # use old entity as-is


class REMSService:
    """REMS service."""

    def __init__(self):
        self.organization = settings.REMS_ORGANIZATION_ID
        self.session = REMSSession()

    def get_entity_data(self, entity: REMSEntity) -> dict:
        """Get data of an entity from REMS."""
        if entity.entity_type == EntityType.USER:
            raise ValueError(f"Not supported for {entity.entity_type=}")

        resp = self.session.get(f"/api/{entity.entity_type}s/{entity.rems_id}")
        return resp.json()

    def archive_entity(self, entity: REMSEntity):
        """Archive entity in REMS and soft delete it in Metax."""
        entity_type = entity.entity_type
        if entity.entity_type == EntityType.USER:
            raise ValueError(f"Not supported for {entity_type=}")

        logger.info(f"Archiving REMS entity {entity}")
        if entity.entity_type == EntityType.RESOURCE:
            # All linked catalogue items need to be archived before archiving resource.
            logger.info("Archiving related REMS catalogue items")
            resid = self.get_entity_data(entity)["resid"]
            self.archive_catalogue_items_by_resid(resid)
        elif entity.entity_type == EntityType.LICENSE:
            # TODO: Figure out what to do if a reference license changes
            if dataset := getattr(entity, "custom_license_dataset", None):
                # Linked catalogue item needs to be archived before archiving license.
                logger.info("Archiving related REMS resources")
                self.archive_resources_by_resid(str(dataset.id))

        # Disabling hides an item from applicants.
        # Archiving also hides it in the administration view.
        self.session.put(
            f"/api/{entity_type}s/enabled",
            json={entity.rems_id_field: entity.rems_id, "enabled": False},
        )
        self.session.put(
            f"/api/{entity_type}s/archived",
            json={entity.rems_id_field: entity.rems_id, "archived": True},
        )
        if not entity._state.adding:  # Don't try to delete temporary entities
            entity.delete(soft=True)

    def archive_catalogue_items_by_resid(self, resid):
        """Archive catalogue items by resid."""
        # The resource parameter for this query is the resid value, not the internal REMS id.
        item_data = self.session.get(
            "/api/catalogue-items", params={"resource": resid, "archived": "false"}
        ).json()
        for val in item_data:
            item = REMSCatalogueItem.objects.filter(rems_id=val["id"]).first()
            if not item:
                # Temporary entities, not saved to DB
                item = REMSCatalogueItem(rems_id=val["id"])
            self.archive_entity(item)

    def archive_resources_by_resid(self, resid: str):
        """Archive resources and linked catalogue items by resid."""
        # Linked catalogue item needs to be archived before archiving resource.
        item_data = self.session.get(
            "/api/resources", params={"resid": resid, "archived": "false"}
        ).json()
        for val in item_data:
            resource = REMSResource.objects.filter(rems_id=val["id"]).first()
            if not resource:
                # Temporary entities, not saved to DB
                resource = REMSResource(rems_id=val["id"])
            self.archive_entity(resource)

    def create_user(self, userid: str, name: str, email: Optional[str]) -> REMSEntity:
        """Create or update user."""
        self.session.post(
            "/api/users/create",  # Updates user if user already exists
            json={"userid": userid, "name": name, "email": email},
        )
        entity, _ = REMSUser.objects.get_or_create(key=userid, rems_id=userid)
        return entity

    def create_organization(self, organization_id: str, short_name: dict, name: dict):
        """Create or update organization."""
        data = {
            "organization/id": organization_id,
            "organization/name": name,
            "organization/short-name": short_name,
        }

        # Check if organization with specified id already exists
        exists = (
            self.session.get(
                f"/api/organizations/{organization_id}", json=data, allow_notfound=True
            ).status_code
            == 200
        )

        if exists:
            self.session.put("/api/organizations/edit", json=data)
        else:
            self.session.post("/api/organizations/create", json=data)
        entity, _ = REMSOrganization.objects.get_or_create(
            key=organization_id, rems_id=organization_id
        )
        return entity

    def get_default_organization_data(self):
        return {"organization/id": self.organization}

    def get_workflow_operation(self, new: dict, entity: REMSWorkflow) -> REMSOperation:
        """Determine what needs to be to catalogue item to get it match the new values."""
        if not entity:
            return REMSOperation.create  # Create new entity

        old_value = self.get_entity_data(entity)
        entity_data = {
            "type": old_value["workflow"]["type"],
            "organization": {"organization/id": old_value["organization"]["organization/id"]},
            "handlers": [handler["userid"] for handler in old_value["workflow"]["handlers"]],
            "title": old_value["title"],
            "forms": old_value["workflow"].get("forms", []),
        }

        if (
            new["type"] != entity_data["type"]
            or new["organization"] != entity_data["organization"]
            or new.get("forms", []) != entity_data["forms"]
        ):
            return REMSOperation.create  # Create new item, archive old
        if entity_data["title"] != new["title"] or set(entity_data["handlers"]) != set(
            new["handlers"]
        ):
            return REMSOperation.edit  # Update title and handlers
        return REMSOperation.keep  # No changes, use existing item

    def create_workflow(
        self,
        key: str,
        title: str,
        handlers: List[str],
        forms: List[REMSForm] = [],
        metax_organization: Optional[
            str
        ] = None,  # Organization id in Metax, not the REMS organization
    ) -> REMSWorkflow:
        """Create or update REMS workflow."""
        entity = REMSWorkflow.objects.filter(key=key).first()
        data = {
            # "anonymize-handling": True, # enable to hide who handled application
            # Default workflow: Handlers can approve/deny applications by themselves.
            "type": "workflow/default",
            "organization": self.get_default_organization_data(),
            "handlers": handlers,  # list of userids, approve-bot for autoapprove
            "title": title,  # Not visible to users who apply
        }
        if forms:
            data["forms"] = [{"form/id": form.rems_id for form in forms}]

        op = self.get_workflow_operation(new=data, entity=entity)
        if op == REMSOperation.keep:
            return entity  # Reuse existing workflow

        if op == REMSOperation.edit:
            # Some workflow values can be edited, mainly title and handlers
            data["id"] = entity.rems_id
            data.pop("type", None)
            data.pop("organization", None)
            self.session.put("/api/workflows/edit", json=data)
            entity.refresh_from_db()
            return entity

        # Create new workflow
        if entity:
            self.archive_entity(entity)
        workflow = self.session.post("/api/workflows/create", json=data).json()
        entity = REMSWorkflow.objects.create(
            key=key, rems_id=workflow["id"], metax_organization=metax_organization
        )
        return entity

    def get_license_type(
        self, url: Optional[str] = None, description: Optional[dict] = None
    ) -> LicenseType:
        """Return license type based on input data."""
        if url and not description:
            return LicenseType.link
        if description and not url:
            return LicenseType.text
        raise ValueError("Expected exactly one of 'url' or 'description' to be set")

    def create_license(
        self,
        key: str,
        title: dict,
        url: Optional[str] = None,
        description: Optional[dict] = None,
        custom_license_dataset: Optional["Dataset"] = None,
        is_data_access_terms: bool = False,
    ):
        """Create REMS license."""
        license_type = self.get_license_type(url=url, description=description)

        entity_data = None
        entity = REMSLicense.objects.filter(key=key).first()
        if entity:
            value = self.get_entity_data(entity)
            entity_data = {
                "licensetype": value["licensetype"],
                "organization": {"organization/id": value["organization"]["organization/id"]},
                "localizations": value["localizations"],
            }

        data = {
            "licensetype": license_type,
            "organization": self.get_default_organization_data(),
        }

        if license_type == LicenseType.link:
            title_languages = list(title.keys())
            data["localizations"] = {
                lang: {"title": title[lang], "textcontent": url} for lang in title_languages
            }
        elif license_type == LicenseType.text:
            description_languages = list(description.keys())
            data["localizations"] = {
                lang: {"title": single_translation(title, lang), "textcontent": description[lang]}
                for lang in description_languages
            }

        if data == entity_data:
            return entity

        if entity:
            self.archive_entity(entity)

        lic = self.session.post("/api/licenses/create", json=data).json()
        entity = REMSLicense.objects.create(
            key=key,
            rems_id=lic["id"],
            custom_license_dataset=custom_license_dataset,
            is_data_access_terms=is_data_access_terms,
        )
        return entity

    def create_license_from_dataset_license(self, dataset: "Dataset", license: "DatasetLicense"):
        is_reference_license = True
        custom_license_dataset = None
        description = None
        title = license.reference.pref_label
        url = license.reference.url
        if license.title or license.description or license.custom_url:
            is_reference_license = False

        if license.title:
            title = license.title

        if license.custom_url:  # User custom url instead of reference url
            url = license.custom_url

        if license.description:  # Use description instead of url
            url = None
            description = license.description

        if is_reference_license:
            # Use common key for identical reference licenses
            key = f"reference-license-{url}"
        else:
            # License has custom data, use per-dataset licenses
            key = f"dataset-{dataset.id}-license-{license.id}"
            custom_license_dataset = dataset

        return self.create_license(
            key=key,
            url=url or None,
            description=description or None,
            title=title,
            custom_license_dataset=custom_license_dataset,
        )

    def create_license_from_data_access_terms(self, dataset: "Dataset", terms: dict):
        key = f"dataset-{dataset.id}-access-terms"
        title = {"en": "Terms for data access", "fi": "Käyttöluvan ehdot"}
        return self.create_license(
            key=key,
            title=title,
            description=terms,
            custom_license_dataset=dataset,
            is_data_access_terms=True,
        )

    def get_license_ids(self, licenses: List[REMSLicense]):
        ids = []
        for lic in licenses:
            if lic.entity_type != EntityType.LICENSE:
                raise ValueError(f"Invalid EntityType for license: {lic.entity_type}")
            ids.append(lic.rems_id)
        return ids

    def create_resource(
        self, key: str, identifier: str, licenses: List[REMSLicense]
    ) -> REMSResource:
        """Create or update REMS resource."""
        entity_data = None
        entity = REMSResource.objects.filter(key=key).first()
        if entity:
            value = self.get_entity_data(entity)
            entity_data = {
                "resid": value["resid"],
                "organization": {"organization/id": value["organization"]["organization/id"]},
                "licenses": [lic["id"] for lic in value["licenses"]],
            }

        data = {
            "resid": identifier,
            "organization": self.get_default_organization_data(),
            "licenses": self.get_license_ids(licenses),
        }
        if data == entity_data:
            return entity

        if entity:
            self.archive_entity(entity)

        resource = self.session.post("/api/resources/create", json=data).json()
        entity = REMSResource.objects.create(
            key=key,
            rems_id=resource["id"],
        )
        return entity

    def get_catalogue_item_operation(self, new: dict, entity: REMSCatalogueItem) -> REMSOperation:
        """Determine what needs to be to catalogue item to get it match the new values."""
        if not entity:
            return REMSOperation.create  # Create new entity

        old_value = self.get_entity_data(entity)

        # Resource id works differently on creation vs getting an existing item
        # In POST /api/catalogue-items
        # - resid is resource.id
        #
        # In GET /api/catalogue-items/{item-id}
        # - resid is resource.resid (string assigned by Metax)
        # - resource-id is resource.id
        if (
            new["resid"] != old_value["resource-id"]
            or new["wfid"] != old_value["wfid"]
            or new.get("form") != old_value.get("form")
        ):
            return REMSOperation.create  # Create new item, archive old
        if new["localizations"] != old_value["localizations"]:
            return REMSOperation.edit  # Update localizations
        return REMSOperation.keep  # No changes, use existing item

    def create_catalogue_item(
        self,
        key: str,
        resource: REMSResource,
        workflow: REMSWorkflow,
        localizations: dict,
        form: Optional[REMSForm] = None,
    ):
        """Create or update catalogue item."""
        item = REMSCatalogueItem.objects.filter(key=key).first()
        data = {
            "resid": resource.rems_id,
            "wfid": workflow.rems_id,
            "organization": self.get_default_organization_data(),
            "localizations": localizations,
        }
        if form:
            data["form"] = form.rems_id

        op = self.get_catalogue_item_operation(data, item)
        if op == REMSOperation.keep:
            return item  # No changes, keep existing entity

        if op == REMSOperation.edit:
            # Edits an existing catalogue item.
            # Localizations can be modified even if applications exist
            data.pop("resid")
            data.pop("wfid")
            data.pop("form", None)
            self.session.put(
                "/api/catalogue-items/edit",
                json={"id": item.rems_id, **data},
            )
            item.refresh_from_db()
            return item

        if item:
            self.archive_entity(item)

        # New catalogue item needs to be created
        resp_item = self.session.post("/api/catalogue-items/create", json=data).json()
        new_id = resp_item["id"]

        return REMSCatalogueItem.objects.create(key=key, rems_id=new_id)

    def list_catalogue_items(self):
        resp = self.session.get(f"{self.base_url}/api/catalogue-items")
        return resp.json()

    def get_dataset_localizations(self, dataset: "Dataset"):
        """Get localizations for dataset."""
        # TODO: Handle missing en?
        localizations = {}
        localizations["en"] = {
            "title": dataset.title.get("en"),
            "infourl": f"https://{settings.ETSIN_URL}/dataset/{dataset.id}",
        }
        if dataset.title.get("fi"):
            localizations["fi"] = {
                "title": dataset.title.get("fi"),
                "infourl": f"https://{settings.ETSIN_URL}/dataset/{dataset.id}",
            }
        return localizations

    def get_dataset(self, dataset: "Dataset") -> Optional[REMSCatalogueItem]:
        dataset_key = self.get_dataset_key(dataset)
        return REMSCatalogueItem.objects.filter(key=dataset_key).first()

    def get_dataset_key(self, dataset: "Dataset") -> str:
        return f"dataset-{dataset.id}"

    def archive_unused_custom_licenses(
        self, dataset: "Dataset", used_licenses: Iterable[REMSLicense]
    ):
        """Archive custom REMS licenses that are no longer used in the dataset."""
        unused_licenses = dataset.custom_rems_licenses(manager="all_objects").exclude(
            rems_id__in=[l.rems_id for l in used_licenses]
        )
        for lic in unused_licenses:
            if not lic.removed:
                self.archive_entity(lic)
        dataset.custom_rems_licenses(manager="all_objects").remove(*unused_licenses)

    def create_automatic_workflow(self, metax_organization: str) -> REMSWorkflow:
        organization_users = MetaxUser.objects.get_organization_admins(metax_organization)
        handlers = []
        for user in organization_users:
            handlers.append(
                self.create_user(
                    userid=user.username, name=user.get_full_name(), email=user.email
                ).rems_id
            )

        return self.create_workflow(
            key=f"automatic-{metax_organization}",
            title=f"Fairdata Automatic ({metax_organization})",
            handlers=["approver-bot", "rejecter-bot", *sorted(handlers)],
            metax_organization=metax_organization,
        )

    def create_dataset_workflow(self, dataset: "Dataset") -> REMSWorkflow:
        """Get or create REMS workflow for dataset."""
        # Only automatic approval supported for now
        return self.create_automatic_workflow(dataset.metadata_owner.organization)

    def update_organization_workflows(self, metax_organization: str) -> List[REMSWorkflow]:
        """Update REMS workflows for Metax organization."""
        # Only automatic approval supported for now
        if REMSWorkflow.objects.filter(key=f"automatic-{metax_organization}").exists():
            return [self.create_automatic_workflow(metax_organization)]
        return []



    @transaction.atomic
    def publish_dataset(
        self, dataset: "Dataset", raise_errors=False
    ) -> Optional[REMSCatalogueItem]:
        """Create or update catalogue item from a Metax dataset."""
        lock_rems_publish(id=dataset.id)

        if dataset.state != "published":
            raise ValueError("Dataset needs to be published to enable REMS.")

        if not dataset.data_catalog.rems_enabled:
            raise ValueError("Catalog is not enabled for REMS.")

        if not dataset.is_rems_dataset:
            raise ValueError("Dataset is not enabled for REMS.")

        try:
            if dataset.rems_publish_error:
                dataset.rems_publish_error = None
                models.Model.save(dataset, update_fields=["rems_publish_error"])
            logging.info(f"Syncing dataset {dataset.id} ({dataset.persistent_identifier}) to REMS")

            workflow = self.create_dataset_workflow(dataset)

            licenses = []
            if terms := dataset.access_rights.data_access_terms:
                licenses.append(self.create_license_from_data_access_terms(dataset, terms))
            licenses.extend(
                [
                    self.create_license_from_dataset_license(dataset, license=dl)
                    for dl in dataset.access_rights.license.all()
                ]
            )
            self.archive_unused_custom_licenses(dataset, licenses)

            dataset_key = self.get_dataset_key(dataset)
            resource = self.create_resource(
                key=dataset_key, identifier=str(dataset.id), licenses=licenses
            )
            return self.create_catalogue_item(
                key=dataset_key,
                resource=resource,
                workflow=workflow,
                localizations=self.get_dataset_localizations(dataset),
            )

        except Exception as e:
            if raise_errors:
                raise
            # If REMS sync fails, store error
            timestamp = timezone.now().isoformat(timespec="milliseconds")
            msg = f"REMS sync failed for dataset {dataset.id} {timestamp}\n\n"
            resp = getattr(e, "response", None)
            if resp is not None:
                msg = f"Response status {resp.status_code}:\n {resp.text}\n\n"

            msg += "".join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
            logger.error(f"Dataset {dataset.id} REMS sync failed: {msg}")
            dataset.rems_publish_error = msg
            models.Model.save(dataset, update_fields=["rems_publish_error"])
            return None

    def check_user(self, user: MetaxUser):
        """Check that user is a valid user for REMS."""
        if not getattr(user, "fairdata_username", None):
            raise ValueError("User should be a Fairdata user")

    def validate_accepted_licenses(self, application: dict, accept_licenses: List[int]):
        all_licenses = set([lic["license/id"] for lic in application["application/licenses"]])
        if missing_licenses := all_licenses - set(accept_licenses):
            raise ValueError(
                f"All licenses need to be accepted. Missing: {sorted(missing_licenses)}"
            )

        if extra_licenses := set(accept_licenses) - all_licenses:
            raise ValueError(
                f"The following licenses are not available for the application: {sorted(extra_licenses)}"
            )

    def accept_licenses(self, application_id: int, licenses: List[int]):
        """Accept licenses for application.

        Expects the licenses list to contain all licenses required by the application.
        """
        application = self.session.get(f"/api/applications/{application_id}").json()

        # Accept licenses
        self.validate_accepted_licenses(application, licenses)

        data = {"application-id": application_id, "accepted-licenses": licenses}
        self.session.post("/api/applications/accept-licenses", json=data)

    def create_application_for_dataset(
        self, user: MetaxUser, dataset: "Dataset", accept_licenses: List[int]
    ) -> dict:
        """Create a REMS application for dataset."""
        self.check_user(user)

        item = REMSCatalogueItem.objects.filter(key=self.get_dataset_key(dataset)).first()
        if not item:
            raise ValueError("Dataset has not been published to REMS.")

        # Ensure user exists in REMS
        self.create_user(
            userid=user.fairdata_username, name=user.get_full_name(), email=user.email
        )

        # Create application for single dataset
        data = {"catalogue-item-ids": [item.rems_id]}
        with self.session.as_user(user.fairdata_username):
            # Create application, get the created application data
            application_id = self.session.post("/api/applications/create", json=data).json()[
                "application-id"
            ]
            self.accept_licenses(application_id=application_id, licenses=accept_licenses)

            # On failed submit, may return 200 with success=false e.g.
            # {"success":false,"errors":[{"type":"t.actions.errors/licenses-not-accepted"}]}
            data = {"application-id": application_id}
            resp = self.session.post("/api/applications/submit", json=data)
            data = resp.json()
            data["application-id"] = application_id
            return data

    def get_user_applications_for_dataset(self, user: MetaxUser, dataset: "Dataset") -> List[dict]:
        self.check_user(user)

        with self.session.as_user(user.fairdata_username):
            resp = self.session.get(f"/api/my-applications?query=resource:{dataset.id}")

        # Get only applications with correct resource id and no other resources
        applications = []
        for application in resp.json():
            resources = application["application/resources"]
            if len(resources) == 1 and resources[0]["resource/ext-id"] == str(dataset.id):
                applications.append(application)
        return applications

    def get_user_application_for_dataset(
        self, user: MetaxUser, dataset: "Dataset", application_id: int
    ) -> Optional[dict]:
        self.check_user(user)

        with self.session.as_user(user.fairdata_username):
            resp = self.session.get(f"/api/applications/{application_id}")

        application = resp.json()
        resources = application.get("application/resources", [])
        if len(resources) != 1 or resources[0]["resource/ext-id"] != str(dataset.id):
            return None  # Support only applications where the dataset is the only resource

        # Add is_data_access_terms to application license data
        terms_rems_ids = set(  # REMS identifiers of data_access_terms licenses
            REMSLicense.objects.filter(
                rems_id__in=[
                    lic["license/id"] for lic in application.get("application/licenses", [])
                ],
                is_data_access_terms=True,
            ).values_list("rems_id", flat=True)
        )
        for license in application["application/licenses"]:
            license["is_data_access_terms"] = license["license/id"] in terms_rems_ids
        return application

    def get_user_entitlements_for_dataset(self, user: MetaxUser, dataset: "Dataset") -> List[dict]:
        """Get active REMS entitlements to a dataset for user."""
        self.check_user(user)
        resp = self.session.get(
            f"/api/entitlements?resource={dataset.id}&user={user.fairdata_username}"
        )
        return resp.json()

    def get_dataset_rems_license_ids(self, dataset: "Dataset") -> List[int]:
        """Get REMS license ids for dataset resource."""
        dataset_key = self.get_dataset_key(dataset)
        resource = REMSResource.objects.get(key=dataset_key)
        resource_data = self.get_entity_data(resource)
        return [lic["id"] for lic in resource_data["licenses"]]

    def get_application_base_for_dataset(self, dataset: "Dataset") -> ApplicationBase:
        """Get data needed for submitting a valid application.

        Normally REMS users cannot see the required forms and licenses for a catalogue item
        directly. This function provides a way to preview what an application would require
        without actually creating an application.

        Implemented
        - Licenses from resource

        Not implemented
        - Licenses from workflow
        - Form (from workflow, catalogue item)
        """
        dataset_key = self.get_dataset_key(dataset)
        resource = REMSResource.objects.get(key=dataset_key)
        # TODO: Check resource is enabled?
        resource_data = self.get_entity_data(resource)
        licenses_data = resource_data.get("licenses")
        terms_rems_ids = set(  # REMS identifiers of data_access_terms licenses
            REMSLicense.objects.filter(
                rems_id__in=[lic["id"] for lic in licenses_data], is_data_access_terms=True
            ).values_list("rems_id", flat=True)
        )
        licenses = []
        for lic_data in licenses_data:
            licenses.append(
                ApplicationLicenseData.from_rems_license_data(
                    lic_data, is_data_access_terms=lic_data["id"] in terms_rems_ids
                )
            )
        forms = []  # not implemented yet
        return ApplicationBase(licenses=licenses, forms=forms)
