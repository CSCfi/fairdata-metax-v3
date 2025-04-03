import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, List, Optional

import requests
from django.conf import settings
from requests.exceptions import HTTPError

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

if TYPE_CHECKING:
    from apps.core.models import Dataset, DatasetLicense


logger = logging.getLogger(__name__)


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

        # TODO: Implement updating workflow
        workflow = self.session.post("/api/workflows/create", json=data).json()
        entity = REMSWorkflow.objects.create(key=key, rems_id=workflow["id"])
        return entity

    def create_license(self, title: dict, url: str):
        """Create REMS license."""
        key = f"reference-{url}" # Assumes license is reference data
        entity_data = None
        entity = REMSLicense.objects.filter(key=key).first()
        if entity:
            value = self.get_entity_data(entity)
            entity_data = {
                "licensetype": value["licensetype"],
                "organization": {"organization/id": value["organization"]["organization/id"]},
                "localizations": value["localizations"],
            }

        # License types:
        # - link: textcontent is an URL pointing to the license
        # - text: textcontent is the license text
        # - attachment: has file attachment
        data = {
            "licensetype": "link",
            "organization": self.get_default_organization_data(),
            "localizations": {  # check: are both fi and en required?
                "en": {"title": title.get("en") or title.get("fi"), "textcontent": url},
                "fi": {"title": title.get("fi") or title.get("en"), "textcontent": url},
            },
        }
        if data == entity_data:
            return entity

        if entity:
            self.archive_changed_entity(entity)

        lic = self.session.post("/api/licenses/create", json=data).json()
        entity = REMSLicense.objects.create(key=key, rems_id=lic["id"])
        return entity

    def create_license_from_dataset_license(self, license: "DatasetLicense"):
        # TODO: Support custom licenses
        return self.create_license(url=license.reference.url, title=license.reference.pref_label)

    def get_license_ids(self, licenses: List[REMSEntity]):
        ids = []
        for lic in licenses:
            if lic.entity_type != EntityType.LICENSE:
                raise ValueError(f"Invalid EntityType for license: {lic.entity_type}")
            ids.append(lic.rems_id)
        return ids

    def create_resource(self, identifier: str, licenses: List[REMSEntity]):
        """Create or update REMS resource."""
        key = f"dataset-{identifier}"

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

    def create_dataset(self, dataset: "Dataset"):
        """Create or update catalogue item from a Metax dataset."""
        if dataset.state != "published":
            raise ValueError("Dataset needs to be published to enable REMS.")

        if not dataset.data_catalog.rems_enabled:
            raise ValueError("Catalog is not enabled for REMS.")

        workflow = REMSWorkflow.objects.get(key="automatic")

        licenses = [
            self.create_license_from_dataset_license(dl)
            for dl in dataset.access_rights.license.all()
        ]

        dataset_key = f"dataset-{dataset.id}"
        resource = self.create_resource(identifier=dataset_key, licenses=licenses)
        return self.create_catalogue_item(
            key=dataset_key,
            resource=resource,
            workflow=workflow,
            localizations=self.get_dataset_localizations(dataset),
        )
