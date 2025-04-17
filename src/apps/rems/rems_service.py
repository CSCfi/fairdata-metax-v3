import logging
import traceback
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterable, List, Optional

import requests
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from requests.exceptions import HTTPError

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
from apps.users.models import MetaxUser

if TYPE_CHECKING:
    from apps.core.models import Dataset, DatasetLicense


logger = logging.getLogger(__name__)


class LicenseType(models.TextChoices):
    link = "link"  # textcontent is an URL pointing to the license
    text = "text"  # textcontent is an license text
    attachment = "attachment"  # license has file attachment (not implemented in Metaxx)


class REMSError(HTTPError):
    pass


class REMSSession(requests.Session):
    """REMS wrapper for requests.Session.

    Modifies requests in the following way:
    - url is appended to REMS_BASE_URL
    - REMS headers are set automatically
    - raises error if request returns an error or is unsuccessful
    - when allow_notfound=True, a 404 response will not raise an error
    - as_user context manager allows making requests as another user
    """

    def __init__(self):
        super().__init__()
        self.base_url = settings.REMS_BASE_URL
        self.rems_user_id = settings.REMS_USER_ID
        self.rems_api_key = settings.REMS_API_KEY

    def get_headers(self):
        return {
            "x-rems-user-id": self.rems_user_id,
            "x-rems-api-key": self.rems_api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

    def request(
        self, method: str, url: str, allow_notfound=False, *args, **kwargs
    ) -> requests.Response:
        if not url.startswith("/"):
            raise ValueError("URL should start with '/'")
        url = f"{self.base_url}{url}"

        # Update the default headers with headers from kwargs
        headers = self.get_headers()
        if extra_headers := kwargs.get("headers"):
            headers.update(extra_headers)
        kwargs["headers"] = headers

        resp = super().request(method, url, *args, **kwargs)
        try:
            if resp.status_code == 404 and allow_notfound:
                return resp
            resp.raise_for_status()
        except HTTPError as e:
            logging.error(f"REMS error {str(e)}: {resp.text}")
            raise REMSError(*e.args, request=e.request, response=e.response)
        except Exception as e:
            logging.error(f"Making REMS request failed: {str(e)}")
            raise

        # Some errors may return a 200 response with success=False
        data = resp.json()
        if "success" in data and not data["success"]:
            logging.error(f"REMS error: {resp.text}")
            raise REMSError(
                f"REMS request was unsuccessful, status_code={resp.status_code=}: {resp.text}",
                request=resp.request,
                response=resp,
            )
        return resp

    @contextmanager
    def as_user(self, user_id: str):
        """Make requests as a specific user instead of the REMS owner user.

        The request will have the same permissions as the user would.

        Example:
            # Get own applications of user
            session = REMSSession()
            with session.as_user("teppo"):
                applications = session.get("/api/my-applications").json()
        """
        original_user_id = self.rems_user_id
        try:
            self.rems_user_id = user_id
            yield
        finally:
            self.rems_user_id = original_user_id


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

    def archive_changed_entity(self, entity: REMSEntity):
        """Archive changed entity in REMS and soft delete it in Metax."""
        entity_type = entity.entity_type
        if entity.entity_type == EntityType.USER:
            raise ValueError(f"Not supported for {entity_type=}")

        logger.info(
            f"REMS {entity_type} {entity.key=} changed, archiving old version {entity.rems_id=}"
        )

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
        entity.delete(soft=True)

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

    def create_workflow(
        self,
        key: str,
        title: str,
        handlers: List[str],
        forms: List[REMSForm] = [],
    ) -> REMSEntity:
        """Create REMS workflow."""
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

        # TODO: Implement updating workflow (handlers, title)
        workflow = self.session.post("/api/workflows/create", json=data).json()
        entity = REMSWorkflow.objects.create(key=key, rems_id=workflow["id"])
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
            self.archive_changed_entity(entity)

        lic = self.session.post("/api/licenses/create", json=data).json()
        entity = REMSLicense.objects.create(
            key=key, rems_id=lic["id"], custom_license_dataset=custom_license_dataset
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

    def get_license_ids(self, licenses: List[REMSEntity]):
        ids = []
        for lic in licenses:
            if lic.entity_type != EntityType.LICENSE:
                raise ValueError(f"Invalid EntityType for license: {lic.entity_type}")
            ids.append(lic.rems_id)
        return ids

    def create_resource(self, key: str, identifier: str, licenses: List[REMSEntity]):
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
            self.archive_changed_entity(entity)

        resource = self.session.post("/api/resources/create", json=data).json()
        entity = REMSResource.objects.create(
            key=key,
            rems_id=resource["id"],
        )
        return entity

    def get_catalogue_item_operation(self, new: dict, entity: REMSEntity):
        """Determine what needs to be to catalogue item to get it match the new values."""
        if not entity:
            return "create"  # Create new entity

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
            return "create"  # Create new item, archive old
        if new["localizations"] != old_value["localizations"]:
            return "edit"  # Update localizations
        return "keep"  # No changes, use existing item

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
        if op == "keep":
            return item  # No changes, keep existing entity

        if op == "edit":
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
            self.archive_changed_entity(item)

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
                self.archive_changed_entity(lic)
        dataset.custom_rems_licenses(manager="all_objects").remove(*unused_licenses)

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

            # Only automatic approval supported for now
            workflow = REMSWorkflow.objects.get(key="automatic")

            licenses = [
                self.create_license_from_dataset_license(dataset, license=dl)
                for dl in dataset.access_rights.license.all()
            ]
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
            logger.error(f"Dataset {dataset.id} REMS sync failed: {e}")
            dataset.rems_publish_error = msg
            models.Model.save(dataset, update_fields=["rems_publish_error"])
            return None

    def check_user(self, user: MetaxUser):
        """Check that user is a valid user for REMS."""
        if not user.fairdata_username:
            raise ValueError("User should be a Fairdata user")

    def create_application_for_dataset(self, user: MetaxUser, dataset: "Dataset") -> dict:
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
            _id = self.session.post("/api/applications/create", json=data).json()["application-id"]
            application = self.session.get(f"/api/applications/{_id}").json()

            # Accept licenses
            # TODO: Require license ids to be listed explicitly
            # in call instead of approving all automatically. Also check
            # that the licenses actually exist in the application because REMS
            # allows accepting licenses that are not in the application and might not even exist.
            licenses = [lic["license/id"] for lic in application["application/licenses"]]
            data = {"application-id": _id, "accepted-licenses": licenses}
            self.session.post("/api/applications/accept-licenses", json=data)

            # On failed submit, may return 200 with success=false e.g.
            # {"success":false,"errors":[{"type":"t.actions.errors/licenses-not-accepted"}]}
            data = {"application-id": _id}
            resp = self.session.post("/api/applications/submit", json=data)
            return resp.json()

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

    def get_user_entitlements_for_dataset(self, user: MetaxUser, dataset: "Dataset") -> List[dict]:
        self.check_user(user)
        resp = self.session.get(
            f"/api/entitlements?resource={dataset.id}&user={user.fairdata_username}"
        )
        return resp.json()
