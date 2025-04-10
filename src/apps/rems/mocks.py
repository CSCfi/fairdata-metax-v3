import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Set, Type, Union

from django.conf import settings
from django.utils import timezone
from requests_mock.mocker import Mocker

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

logger = logging.getLogger(__name__)


class MockREMS:
    """Mock REMS class for tests.

    When creating an entity, stores input data mostly unchanged in self.entities.
    """

    class ApplicationState:
        DRAFT = "application.state/draft"
        SUBMITTED = "application.state/submitted"
        APPROVED = "application.state/approved"
        REJECTED = "application.state/rejected"
        CLOSED = "application.state/closed"
        RETURNED = "application.state/returned"
        REVOKED = "application.state/revoked"

    entity_models: List[Type[REMSEntity]] = [
        REMSCatalogueItem,
        REMSForm,
        REMSLicense,
        REMSOrganization,
        REMSResource,
        REMSUser,
        REMSWorkflow,
    ]

    def __init__(self):
        self.calls = []  # Used for tracking called endpoints in format "endpoint/entity_type"
        self.entities: Dict[str, dict]  # Entities by entity_type and rems_id
        self.id_counters: Dict[str, int]  # Counters for autoincrementing id by entity type
        self.clear_entities()
        self.reset_counters()

    def clear_entities(self):
        self.entities = {}
        for entity_type in EntityType:
            self.entities[entity_type] = {}

    def reset_counters(self):
        self.id_counters = {}  # Counters for autoincrementing id by entity type
        for entity_type in EntityType:
            if entity_type not in {EntityType.USER, EntityType.ORGANIZATION}:
                self.id_counters[entity_type] = 0

    def clear_calls(self):
        self.calls.clear()

    def get_request_path_rems_id(self, entity_type, request):
        match = re.match(
            f"{settings.REMS_BASE_URL}/api/{entity_type}s/(?P<rems_id>[^/]+)/?.*", request.url
        )
        if match:
            val = match.group("rems_id")
            try:  # Convert value to int if possible
                val = int(val)
            except ValueError:
                pass
            return val
        return None

    @dataclass
    class ApplicationResourceData:
        resources: List[dict]  # Resources in the format returned by application endpoint
        license_ids: Set[int]  # All licenses used in resources
        wfid: int  # Workflow common for all resources

    def create_application_resource_data(
        self, catalogue_item_ids: List[int]
    ) -> ApplicationResourceData:
        """Determine application resource objects and related data."""
        catalogue_items = [
            self.entities[EntityType.CATALOGUE_ITEM][_id] for _id in catalogue_item_ids
        ]

        wfid = None
        license_ids = set()
        resources = []
        for item in catalogue_items:
            if wfid:
                if wfid != item["wfid"]:
                    raise ValueError("All catalogue items in bundle should have the same workflow")
            else:
                wfid = item["wfid"]

            resource = self.entities[EntityType.RESOURCE][item["resource-id"]]
            for lic in resource["licenses"]:
                license_ids.add(lic["id"])

            resource = {
                "catalogue-item/id": item.get("id"),
                "catalogue-item/start": item.get("start"),
                "catalogue-item/end": item.get("end"),
                "catalogue-item/expired": bool(item.get("expired")),
                "catalogue-item/enabled": bool(item.get("enabled")),
                "catalogue-item/archived": bool(item.get("archived")),
                "resource/id": item["resource-id"],
                "catalogue-item/title": {
                    lang: loc.get("title") for lang, loc in item["localizations"].items()
                },
                "catalogue-item/infourl": {
                    lang: loc.get("infourl") for lang, loc in item["localizations"].items()
                },
                "resource/ext-id": item["resid"],
            }
            resources.append(resource)
        return self.ApplicationResourceData(
            resources=resources, license_ids=license_ids, wfid=wfid
        )

    @dataclass
    class ApplicationWorkflowData:
        workflow: dict  # Resources in the format returned by application endpoint
        license_ids: Set[int]  # All licenses used in resources

    def create_application_workflow_data(self, wfid: int) -> ApplicationWorkflowData:
        """Determine application workflow and related data."""
        workflow = self.entities[EntityType.WORKFLOW][wfid]
        return self.ApplicationWorkflowData(
            workflow={
                "workflow/id": workflow["id"],
                "workflow/type": workflow["type"],
                # handlers are in workflow.dynamic/handlers even if workflow is not dynamic
                "workflow.dynamic/handlers": workflow["handlers"],
            },
            license_ids=set(lic["id"] for lic in workflow.get("licenses", [])),
        )

    def create_application_license_data(self, license_ids: Set[int]) -> List[dict]:
        """Determine application license objects."""
        licenses = []
        for lic_id in sorted(license_ids):
            license = self.entities[EntityType.LICENSE][lic_id]
            license_type = license["licensetype"]
            license_data = {
                "license/id": lic_id,
                "license/type": license_type,
                "license/title": {
                    lang: loc.get("title") for lang, loc in license["localizations"].items()
                },
                "license/enabled": license["enabled"],
                "license/archived": license["archived"],
            }

            textcontent = {
                lang: loc.get("textcontent") for lang, loc in license["localizations"].items()
            }
            if license_type == "text":
                license["license/text"] = textcontent
            elif license_type == "link":
                license["license/link"] = textcontent
            else:  # attachment
                raise NotImplementedError("Attachment license not implemented")

            licenses.append(license_data)
        return licenses

    def create_application_data(
        self, application_id: int, user_id: str, catalogue_item_ids: List[int]
    ) -> dict:
        resource_data = self.create_application_resource_data(
            catalogue_item_ids=catalogue_item_ids
        )
        workflow_data = self.create_application_workflow_data(resource_data.wfid)
        licenses = self.create_application_license_data(
            resource_data.license_ids | workflow_data.license_ids
        )

        # Most of these fields are not used by Metax
        # but they are kept here for documentation
        now = timezone.now()
        generated_external_id = f"{now.year}/{application_id}"
        data = {
            "application/id": application_id,
            "application/state": self.ApplicationState.DRAFT,
            "application/generated-external-id": generated_external_id,
            "application/accepted-licenses": {},  # userid -> List[license_id]
            # Timestamps, e.g. "2025-03-05T14:43:35.064Z"
            "application/first-submitted": None,
            "application/created": now.isoformat(),
            "application/modified": now.isoformat(),
            # Expanded references to users, only applicant implemented
            "application/applicant": self.entities[EntityType.USER][user_id],
            "application/members": [],  # additional users in application
            "application/invited-members": [],
            "application/blacklist": [],  # list of banned users
            # Expanded references to other entities
            "application/licenses": licenses,  # licenses from both workflow and catalogue item
            "application/resources": resource_data.resources,  # resources with catalogue item data
            "application/workflow": workflow_data.workflow,  # workflow from catalogue item
            # Values that should be specific to current user, no logic implemented
            "application/permissions": [],  # what current user can do with the application
            "application/roles": ["applicant"],  # application roles of current user
            # Fields with no logic implemented
            "application/external-id": generated_external_id,
            "application/todo": None,  # e.g. "waiting-for-review"
            "application/events": [],  # all changes to application, who, what, when etc.
            "application/description": "",  # filled in when a form has application title field
            "application/attachments": [],  # filled in from attachment fields
            "application/forms": [],  # forms from both workflow and catalogue item
        }
        return data

    def handle_create(self, entity_type: EntityType):
        """Create new entity."""

        def _handler(request, context):
            self.calls.append(f"create/{entity_type}")

            output = {"success": True}
            data = request.json()
            data.setdefault("archived", False)
            data.setdefault("enabled", True)

            # REMS id handling
            if entity_type == EntityType.USER:
                _id = data["userid"]  # User creation does not return userid
            elif entity_type == EntityType.ORGANIZATION:
                _id = data["organization/id"]
                if _id in self.entities[EntityType.ORGANIZATION]:
                    # REMS returns 200 respose with success=false for duplicate organization id
                    return {
                        "success": False,
                        "errors": [
                            {"type": "t.actions.errors/duplicate-id", "organization/id": "orgid"}
                        ],
                    }
                output["organization/id"] = _id
            else:  # REMS generates the id
                self.id_counters[entity_type] += 1
                _id = self.id_counters[entity_type]
                data["id"] = _id
                output["id"] = _id

            if entity_type == EntityType.WORKFLOW:
                data.setdefault("type", "workflow/decider")
                # REMS replaces userids with user values
                data["handlers"] = [
                    self.entities[EntityType.USER][user_id] for user_id in data["handlers"]
                ]
                # REMS replaces license ids with license values
                data["licenses"] = [
                    self.entities[EntityType.LICENSE][lic_id]
                    for lic_id in data.get("licenses", [])
                ]

            if entity_type == EntityType.RESOURCE:
                # REMS replaces license ids with license values
                data["licenses"] = [
                    self.entities[EntityType.LICENSE][lic_id] for lic_id in data["licenses"]
                ]

            if entity_type == EntityType.CATALOGUE_ITEM:
                # REMS replaces catalogue item resid with resource.resid
                data["resource-id"] = data["resid"]
                data["resid"] = self.entities[EntityType.RESOURCE][data["resid"]]["resid"]

            if entity_type == EntityType.APPLICATION:
                user_id = request.headers["X-REMS-USER-ID"]
                data = self.create_application_data(
                    application_id=_id,
                    user_id=user_id,
                    catalogue_item_ids=data["catalogue-item-ids"],
                )
                # Note "application-id" on creation but "application/id" on GET
                output = {"success": True, "application-id": data["application/id"]}

            self.entities[entity_type][_id] = data
            return output

        return _handler

    def handle_list(self, entity_type: EntityType):
        """List all existing entitities."""

        def _handler(request, context):
            self.calls.append(f"list/{entity_type}")
            data = self.entities[entity_type]
            return data

        return _handler

    def handle_get(self, entity_type: EntityType):
        """Get existing entity."""

        def _handler(request, context):
            self.calls.append(f"get/{entity_type}")
            rems_id = self.get_request_path_rems_id(entity_type, request)
            data = self.entities[entity_type].get(rems_id)
            if not data:
                context.status_code = 404
                context.reason = f"{entity_type} {rems_id} not found"
                return
            return data

        return _handler

    def handle_edit(self, entity_type: EntityType):
        """Edit existing entity."""

        def _handler(request, context):
            if entity_type in {
                EntityType.USER,
                EntityType.RESOURCE,
                EntityType.LICENSE,
            }:
                raise NotImplementedError(f"Not implemented or not supported for {entity_type}")

            rems_id = request.json()[
                "id" if entity_type != EntityType.ORGANIZATION else REMSOrganization.rems_id_field
            ]
            self.calls.append(f"edit/{entity_type}")

            data = self.entities[entity_type].get(rems_id)
            if not data:
                context.status_code = 404
                context.reason = f"{entity_type} {rems_id} not found"
                return

            new_data = request.json()
            if entity_type == EntityType.CATALOGUE_ITEM:
                if invalid := {"form", "workflow", "resid"}.intersection(new_data):
                    raise ValueError(f"Unexpected fields: {invalid}")

            self.entities[entity_type][rems_id].update(new_data)
            return {"success": True}

        return _handler

    def handle_archive(self, entity_type: EntityType):
        """Archive/unarchive existing entity."""

        def _handler(request, context):
            if entity_type in {EntityType.USER, EntityType.ORGANIZATION}:
                raise NotImplementedError()

            rems_id = request.json()["id"]
            self.calls.append(f"archive/{entity_type}")

            data = self.entities[entity_type].get(rems_id)
            if not data:
                context.status_code = 404
                context.reason = f"{entity_type} {rems_id} not found"
                return

            new_data = request.json()
            if new_data.keys() != {"id", "archived"}:
                raise ValueError(
                    f"Expected fields 'id', 'archived' in data, "
                    f"got: {sorted(request.json().keys())}"
                )

            data.update(new_data)
            return {"success": True}

        return _handler

    def handle_disable(self, entity_type: EntityType):
        """Enable/disable existing entity."""

        def _handler(request, context):
            if entity_type in {EntityType.USER, EntityType.ORGANIZATION}:
                raise NotImplementedError()

            rems_id = request.json()["id"]
            self.calls.append(f"disable/{entity_type}")

            data = self.entities[entity_type].get(rems_id)
            if not data:
                context.status_code = 404
                context.reason = f"{entity_type} {rems_id} not found"
                return

            new_data = request.json()
            if new_data.keys() != {"id", "enabled"}:
                raise ValueError(
                    f"Expected fields 'id', 'enabled' in data, "
                    f"got: {sorted(request.json().keys())}"
                )

            data.update(new_data)
            return {"success": True}

        return _handler

    def handle_application_accept_licenses(self, request, context):
        data = request.json()
        if set(data) != {"application-id", "accepted-licenses"}:
            raise ValueError("Expected fields 'application-id', 'accepted-licenses'")

        application = self.entities[EntityType.APPLICATION][data["application-id"]]
        userid = request.headers["X-REMS-USER-ID"]

        # Assume application has only applicant, no members
        if application["application/applicant"]["userid"] != userid:
            context.status_code = 403
            return "Permission denied"

        if application["application/state"] not in {
            self.ApplicationState.DRAFT,
            self.ApplicationState.RETURNED,
        }:
            context.status_code = 400
            return "Application is not writable"

        # Check that accepted licenses are actually in the application
        # Note: REMS does not do this check
        license_ids = set(data["accepted-licenses"])
        application_licenses = {lic["license/id"] for lic in application["application/licenses"]}
        if invalid_licenses := license_ids - application_licenses:
            raise ValueError(f"Invalid license ids: in {sorted(invalid_licenses)}")

        # Add licenses for user
        old_accepted = application["application/accepted-licenses"].get(userid, [])
        new_accepted = sorted(set(old_accepted) | license_ids)
        application["application/accepted-licenses"][userid] = new_accepted
        return {"success": True}

    def handle_application_submit(self, request, context) -> Union[dict, str]:
        data = request.json()
        if set(data) != {"application-id"}:
            raise ValueError("Expected fields 'application-id'")

        application = self.entities[EntityType.APPLICATION][data["application-id"]]
        userid = request.headers["X-REMS-USER-ID"]
        if application["application/applicant"]["userid"] != userid:
            context.status_code = 403
            return "Permission denied"

        if application["application/state"] not in {
            self.ApplicationState.DRAFT,
            self.ApplicationState.RETURNED,
        }:
            context.status_code = 400
            return "Application is not writable"

        # Check that all users have accepted all licenses
        # Only applicant supported, not members for now
        license_ids = {lic["license/id"] for lic in application["application/licenses"]}
        if license_ids - set(application["application/accepted-licenses"].get(userid, [])):
            return {
                "success": False,
                "errors": [{"type": "t.actions.errors/licenses-not-accepted"}],
            }

        # Update application state
        now = timezone.now()
        application["application/first-submitted"] = now.isoformat()
        application["application/modified"] = now.isoformat()
        application["application/state"] = self.ApplicationState.SUBMITTED

        self.post_application_submit_handler(application)

        return {"success": True}

    def post_application_submit_handler(self, application):
        """Simulate bot users after submitting application."""
        handlers = application["application/workflow"]["workflow.dynamic/handlers"]
        for handler in handlers:
            if handler["userid"] == "approver-bot":
                now = timezone.now()
                application["application/modified"] = now.isoformat()
                application["application/state"] = self.ApplicationState.APPROVED
                break

    def handle_list_my_applications(self, request, context):
        userid = request.headers["X-REMS-USER-ID"]
        applications = self.entities[EntityType.APPLICATION]
        return [a for a in applications.values() if a["application/applicant"]["userid"] == userid]

    def get_base_url(self, entity_type: EntityType):
        return f"{settings.REMS_BASE_URL}/api/{entity_type}s"

    def register_endpoints(self, mocker: Mocker):
        """Register endpoints to a Mocker instance (e.g. requests_mock pytest fixture)."""
        for entity_type in EntityType:
            base = self.get_base_url(entity_type)
            mocker.post(f"{base}/create", json=self.handle_create(entity_type=entity_type))
            # REMS users don't have the same list/get endpoints as the other entities have
            if entity_type != EntityType.USER:
                mocker.get(
                    base,
                    json=self.handle_list(entity_type=entity_type),
                )
                mocker.get(
                    re.compile(rf"{base}/(?P<rems_id>[^/]+)"),
                    json=self.handle_get(entity_type=entity_type),
                )

            # Applications and entitlements don't have the usual edit, archive, enable endpoints
            if entity_type == EntityType.APPLICATION:
                continue

            # REMS licenses cannot be edited
            if entity_type != EntityType.LICENSE:
                mocker.put(
                    re.compile(f"{base}/edit"),
                    json=self.handle_edit(entity_type=entity_type),
                )
            mocker.put(
                re.compile(f"{base}/archived"),
                json=self.handle_archive(entity_type=entity_type),
            )
            mocker.put(
                re.compile(f"{base}/enable"),
                json=self.handle_disable(entity_type=entity_type),
            )

        # Application endpoints
        base = f"{settings.REMS_BASE_URL}/api/applications"
        mocker.post(f"{base}/accept-licenses", json=self.handle_application_accept_licenses)
        mocker.post(f"{base}/submit", json=self.handle_application_submit)
        mocker.get(
            f"{settings.REMS_BASE_URL}/api/my-applications", json=self.handle_list_my_applications
        )
