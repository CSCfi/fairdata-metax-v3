import logging
import re
from typing import Dict, List, Type

from django.conf import settings
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
        for model in self.entity_models:
            self.entities[model.entity_type] = {}

    def reset_counters(self):
        self.id_counters = {}  # Counters for autoincrementing id by entity type
        for model in self.entity_models:
            if model.entity_type not in {EntityType.USER, EntityType.ORGANIZATION}:
                self.id_counters[model.entity_type] = 0

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

            if entity_type == EntityType.RESOURCE:
                # REMS replaces license ids with license values
                data["licenses"] = [
                    self.entities[EntityType.LICENSE][lic_id] for lic_id in data["licenses"]
                ]

            if entity_type == EntityType.CATALOGUE_ITEM:
                # REMS replaces catalogue item resid with resource.resid
                data["resource-id"] = data["resid"]
                data["resid"] = self.entities[EntityType.RESOURCE][data["resid"]]["resid"]

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

    def get_base_url(self, model: REMSEntity):
        return f"{settings.REMS_BASE_URL}/api/{model.entity_type}s"

    def register_endpoints(self, mocker: Mocker):
        """Register endpoints to a Mocker instance (e.g. requests_mock pytest fixture)."""
        for model in self.entity_models:
            base = self.get_base_url(model)
            mocker.post(f"{base}/create", json=self.handle_create(entity_type=model.entity_type))
            # REMS users don't have the same list/get endpoints as the other entities have
            if model.entity_type != EntityType.USER:
                mocker.get(
                    base,
                    json=self.handle_list(entity_type=model.entity_type),
                )
                mocker.get(
                    re.compile(rf"{base}/(?P<rems_id>[^/]+)"),
                    json=self.handle_get(entity_type=model.entity_type),
                )
            # REMS licenses cannot be edited
            if model.entity_type != EntityType.LICENSE:
                mocker.put(
                    re.compile(f"{base}/edit"),
                    json=self.handle_edit(entity_type=model.entity_type),
                )
            mocker.put(
                re.compile(f"{base}/archived"),
                json=self.handle_archive(entity_type=model.entity_type),
            )
            mocker.put(
                re.compile(f"{base}/enable"),
                json=self.handle_disable(entity_type=model.entity_type),
            )
