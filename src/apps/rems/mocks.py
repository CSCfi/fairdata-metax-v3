import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Type, Union

from django.conf import settings
from django.utils import timezone
from requests_mock.mocker import Mocker
from requests_mock.request import _RequestObjectProxy as Request

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


@dataclass
class Call:
    action: str
    entity_type: EntityType
    request: Request
    rems_id: Optional[Union[str, int]] = None  # Requested id
    created_id: Optional[Union[str, int]] = None  # Id of created entity

    def __str__(self):
        """Return call data in compact string format useful for tests."""
        val = f"{self.action}/{self.entity_type}"
        if self.rems_id:  # Action on specific existing entity
            val += f":{self.rems_id}"
        if self.request.query:  # Query string
            val += f"?{self.request.query}"
        if self.created_id:  # Action produced entity with id
            val += f"->{self.created_id}"
        return val


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

    def add_call(self, **kwargs) -> Call:
        call = Call(**kwargs)
        self.calls.append(call)
        return call

    def clear_calls(self):
        self.calls.clear()

    @property
    def call_list(self) -> List[str]:
        """Return call list in string format."""
        return [str(call) for call in self.calls]

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
                "workflow.dynamic/handlers": workflow["workflow"]["handlers"],
            },
            license_ids=set(lic["id"] for lic in workflow["workflow"].get("licenses", [])),
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
            # Fields with no logic implemented
            "application/external-id": generated_external_id,
            "application/todo": None,  # e.g. "waiting-for-review"
            "application/events": [],  # all changes to application, who, what, when etc.
            "application/description": "",  # filled in when a form has application title field
            "application/attachments": [],  # filled in from attachment fields
            "application/forms": [],  # forms from both workflow and catalogue item
            # Fields created dynamically on response
            "application/roles": [], # roles the request user has in the application
        }
        return data

    def handle_create(self, entity_type: EntityType):
        """Create new entity."""

        def _handler(request, context):
            call = self.add_call(action="create", entity_type=entity_type, request=request)

            output = {"success": True}
            data = request.json()
            data.setdefault("archived", False)
            data.setdefault("enabled", True)

            # REMS id handling
            _id: Union[int, str]
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
            call.created_id = _id  # We now have the id, add it to the call data

            if entity_type == EntityType.WORKFLOW:
                data["workflow"] = {
                    "type": data.get("type", "workflow/default"),
                    "handlers": [
                        # REMS replaces userids with user values
                        self.entities[EntityType.USER][user_id]
                        for user_id in data["handlers"]
                    ],
                    "forms": [
                        self.entities[EntityType.FORM][form_id]
                        for form_id in data.get("forms", [])
                    ],
                }
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

    def get_query_param(self, request, param: str) -> Optional[str]:
        if val := request.qs.get(param):
            return val[0]  # Return only first value for param
        return None

    def user_is_applicant(self, request, application: dict) -> bool:
        user_id = request.headers["X-REMS-USER-ID"]
        return application["application/applicant"]["userid"] == user_id

    def user_is_handler(self, request, application: dict) -> bool:
        user_id = request.headers["X-REMS-USER-ID"]
        return any(
            handler["userid"] == user_id
            for handler in application["application/workflow"]["workflow.dynamic/handlers"]
        )

    def user_can_see_application(self, request, application: dict):
        return self.user_is_applicant(request, application) or self.user_is_handler(
            request, application
        )

    def handle_list(self, entity_type: EntityType):
        """List all existing entitities."""

        def _handler(request, context):
            self.add_call(action="list", entity_type=entity_type, request=request)
            data = list(self.entities[entity_type].values())
            if entity_type == EntityType.CATALOGUE_ITEM:
                if resid := self.get_query_param(request, "resource"):  # External resource id
                    data = [item for item in data if item["resid"] == resid]
            elif entity_type == EntityType.APPLICATION:
                data = [item for item in data if self.user_can_see_application(request, item)]
                data = [
                    self.update_application_fields(request, application=item, in_list=True)
                    for item in data
                ]
                return data

            if self.get_query_param(request, "archived") != "true":
                data = [item for item in data if not item["archived"]]

            return data

        return _handler

    def handle_get(self, entity_type: EntityType):
        """Get existing entity."""

        def _handler(request, context):
            rems_id = self.get_request_path_rems_id(entity_type, request)
            self.add_call(action="get", entity_type=entity_type, request=request, rems_id=rems_id)
            data = self.entities[entity_type].get(rems_id)
            if data and entity_type == EntityType.APPLICATION:
                if self.user_can_see_application(request, application=data):
                    data = self.update_application_fields(request, application=data, in_list=False)
                else:
                    data = None
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
            self.add_call(action="edit", entity_type=entity_type, request=request, rems_id=rems_id)

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

    def get_resource_dependencies(self, rems_id: int) -> dict:
        catalogue_items = {}
        for item in self.entities[EntityType.CATALOGUE_ITEM].values():
            if item["archived"]:
                continue
            if item["resource-id"] == rems_id:
                catalogue_items[item["id"]] = {
                    "catalogue-item/id": item["id"],
                    "localizations": item["localizations"],
                }
        if catalogue_items:
            return {"catalogue-items": catalogue_items}
        return {}

    def get_license_dependencies(self, rems_id: int) -> dict:
        """Get catalogue item and resource dependencies of license."""
        resources = {}
        catalogue_items = {}
        for resource in self.entities[EntityType.RESOURCE].values():
            if resource["archived"]:
                continue
            if any(lic["id"] == rems_id for lic in resource["licenses"]):
                resources[resource["id"]] = {
                    "resource/id": resource["id"],
                    "resid": resource["resid"],
                }
                catalogue_items.update(
                    self.get_resource_dependencies(resource["id"]).get("catalogue-items", {})
                )

        deps = {}
        if resources:
            deps["resources"] = resources
        if catalogue_items:
            deps["catalogue-items"] = catalogue_items
        return deps

    def in_use_error(self, dependencies: dict) -> dict:
        return {
            "success": False,
            "type": "t.administration.errors/in-use-by",
            # Convert dicts of entity data to lists of entity data
            **{dep_type: list(v.values()) for dep_type, v in dependencies.items()},
        }

    def handle_archive(self, entity_type: EntityType):
        """Archive/unarchive existing entity."""

        def _handler(request, context):
            if entity_type in {EntityType.USER, EntityType.ORGANIZATION}:
                raise NotImplementedError()

            rems_id = request.json()["id"]
            self.add_call(
                action="archive", entity_type=entity_type, request=request, rems_id=rems_id
            )

            if entity_type == EntityType.LICENSE:
                if deps := self.get_license_dependencies(rems_id):
                    return self.in_use_error(deps)
            elif entity_type == EntityType.RESOURCE:
                if deps := self.get_resource_dependencies(rems_id):
                    return self.in_use_error(deps)

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
            self.add_call(
                action="disable", entity_type=entity_type, request=request, rems_id=rems_id
            )

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
                self.approve_application(application, handler)
                break

    def approve_application(self, application, approver) -> dict:
        now = timezone.now()
        userid = application["application/applicant"]["userid"]
        application["application/modified"] = now.isoformat()
        application["application/state"] = self.ApplicationState.APPROVED

        # Create entitlement
        self.id_counters[EntityType.ENTITLEMENT] += 1
        entitlement_id = self.id_counters[EntityType.ENTITLEMENT]
        entitlements = self.entities[EntityType.ENTITLEMENT].setdefault(userid, {})
        entitlements[entitlement_id] = {
            "resource": application["application/resources"][0]["resource/ext-id"],
            "user": self.entities[EntityType.USER][userid],
            "application-id": application["application/id"],
            "start": now.isoformat(),
            "end": None,
            "mail": approver.get("email"),
        }
        return entitlements[entitlement_id]

    def reject_application(self, application) -> dict:
        now = timezone.now()
        application["application/modified"] = now.isoformat()
        application["application/state"] = self.ApplicationState.REJECTED

    def filter_application_list_fields(self, application):
        """Application lists don't include forms or licenses."""
        return {
            field: value
            for field, value in application.items()
            if field not in {"application/forms", "application/licenses"}
        }

    def add_user_application_fields(self, request, application: dict) -> dict:
        roles = []
        if self.user_is_applicant(request, application=application):
            roles.append("applicant")
        if self.user_is_handler(request, application=application):
            roles.append("handler")
        return {**application, "application/roles": roles}

    def update_application_fields(self, request, application: dict, in_list=False) -> dict:
        """Update request-specific fields of application dict."""
        application = self.add_user_application_fields(request, application)
        if in_list:
            application = self.filter_application_list_fields(application)
        return application

    def handle_list_my_applications(self, request, context):
        applications = self.entities[EntityType.APPLICATION].values()
        return [
            self.update_application_fields(request, application=a, in_list=True)
            for a in applications
            if self.user_is_applicant(request, application=a)
        ]

    def handle_list_applications_todo(self, request, context):
        applications = self.entities[EntityType.APPLICATION].values()
        return [
            self.update_application_fields(request, application=a, in_list=True)
            for a in applications
            if self.user_is_handler(request, application=a)
            and a["application/state"] == self.ApplicationState.SUBMITTED
        ]

    def handle_list_applications_handled(self, request, context):
        applications = self.entities[EntityType.APPLICATION].values()
        return [
            self.update_application_fields(request, application=a, in_list=True)
            for a in applications
            if self.user_is_handler(request, application=a)
            and a["application/state"] != self.ApplicationState.SUBMITTED
            and a["application/state"] != self.ApplicationState.DRAFT
        ]

    def validate_application_command(
        self, request, context, allowed_states: list
    ) -> Tuple[Optional[dict], any]:
        """Validate application command.

        Parameters:
            request: The incoming HTTP request containing JSON data with 'application-id'.
            context: The response context object used to set HTTP status codes.
            allowed_states: A list of valid application states for the command.

        Returns:
            tuple containing
            - application (dict | None): Valid application for the command.
            - error (any): Error response content if command is not valid.
        """
        rems_id = request.json()["application-id"]
        application = self.entities[EntityType.APPLICATION][rems_id]
        if not application:
            context.status_code = 404
            return None, f"Application {rems_id} not found"
        if not self.user_can_see_application(request, application):
            context.status_code = 403
            return None, "Forbidden"
        if (
            not self.user_is_handler(request, application)
            or application["application/state"] not in allowed_states
        ):
            # When user can see application, but has wrong role
            # or application is in wrong state, return 200 with a forbidden error.
            return None, {"success": False, "errors": [{"type": "forbidden"}]}
        return application, None

    def handle_approve_application(self, request, context):
        application, error = self.validate_application_command(
            request, context, allowed_states=[self.ApplicationState.SUBMITTED]
        )
        if error:
            return error
        userid = request.headers["X-REMS-USER-ID"]
        handler = self.entities[EntityType.USER][userid]
        self.approve_application(application, approver=handler)
        return {"success": True}

    def handle_reject_application(self, request, context):
        application, error = self.validate_application_command(
            request, context, allowed_states=[self.ApplicationState.SUBMITTED]
        )
        if error:
            return error
        self.reject_application(application)
        return {"success": True}

    def handle_list_entitlements(self, request, context):
        userid = request.headers["X-REMS-USER-ID"]
        if userid != settings.REMS_USER_ID:
            raise NotImplementedError("Only supported for owner user")

        # Require both resource and user for now in query
        resource_ext_id = request.qs["resource"][0]
        query_user = request.qs["user"][0]

        user_entitlements = self.entities[EntityType.ENTITLEMENT].get(query_user, {})
        return [e for e in user_entitlements.values() if e["resource"] == resource_ext_id]

    def get_base_url(self, entity_type: EntityType):
        return f"{settings.REMS_BASE_URL}/api/{entity_type}s"

    def register_endpoints(self, mocker: Mocker):
        """Register endpoints to a Mocker instance (e.g. requests_mock pytest fixture)."""
        for entity_type in EntityType:
            if entity_type == EntityType.ENTITLEMENT:  # Entitlements can only be lisetd
                continue

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

        # Application-specific endpoints
        base = f"{settings.REMS_BASE_URL}/api/applications"
        mocker.post(f"{base}/accept-licenses", json=self.handle_application_accept_licenses)
        mocker.post(f"{base}/submit", json=self.handle_application_submit)
        mocker.get(
            f"{settings.REMS_BASE_URL}/api/my-applications", json=self.handle_list_my_applications
        )
        mocker.get(
            f"{settings.REMS_BASE_URL}/api/applications/todo",
            json=self.handle_list_applications_todo,
        )
        mocker.get(
            f"{settings.REMS_BASE_URL}/api/applications/handled",
            json=self.handle_list_applications_handled,
        )
        mocker.get(
            f"{settings.REMS_BASE_URL}/api/applications/handled",
            json=self.handle_list_applications_handled,
        )
        mocker.post(
            f"{settings.REMS_BASE_URL}/api/applications/approve",
            json=self.handle_approve_application,
        )
        mocker.post(
            f"{settings.REMS_BASE_URL}/api/applications/reject",
            json=self.handle_reject_application,
        )

        # Entitlement-specific endpoints
        mocker.get(
            f"{settings.REMS_BASE_URL}/api/entitlements", json=self.handle_list_entitlements
        )
