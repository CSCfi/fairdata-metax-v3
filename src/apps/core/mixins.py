from typing import Dict, List


class V2DatasetMixin:
    """Mixin for converting the class object into v2 Dataset"""

    def _generate_v2_ref_data_field(
        self,
        field_name: str,
        document: Dict,
        pref_label_text: str = "pref_label",
        top_level_key_name: str = None,
        extra_top_level_fields: List = None,
    ):
        """

        Args:
            field_name (RelatedManager): ForeignKey from which the reference data object is constructed
            document (Dict): V2 Dataset dictionary
            pref_label_text (): Object reference data key name
            top_level_key_name ():
            extra_top_level_fields ():

        Returns:

        """

        related_manager = getattr(self, field_name)
        if related_manager.count() == 0:
            return

        obj_list = []
        for row in related_manager.all():
            obj = {pref_label_text: row.pref_label, "identifier": row.url}
            if row.in_scheme:
                obj["in_scheme"] = row.in_scheme
            if top_level_key_name:
                obj = {top_level_key_name: obj}
                obj_list.append(obj)
            else:
                obj_list.append(obj)
            if extra_top_level_fields:
                for field in extra_top_level_fields:
                    if getattr(row, field) is not None:
                        obj.update({field: getattr(row, field)})
        if len(obj_list) != 0:
            document["research_dataset"][field_name] = obj_list
        return obj_list

    def _generate_v2_other_identifiers(self, document: Dict):
        obj_list = []
        for identifier in self.other_identifiers.all():
            obj_list.append(
                {
                    "type": {
                        "in_scheme": identifier.identifier_type.in_scheme,
                        "identifier": identifier.identifier_type.url,
                        "pref_label": identifier.identifier_type.pref_label,
                    },
                    "notation": identifier.notation,
                }
            )
        if len(obj_list) != 0:
            document["research_dataset"]["other_identifier"] = obj_list
        return obj_list

    def _generate_v2_temporal(self, document: Dict):
        obj_list = []
        for temporal in self.temporal.filter(provenance=None):
            obj_list.append(
                {
                    "start_date": temporal.start_date,
                    "end_date": temporal.end_date,
                }
            )
        if len(obj_list) != 0:
            document["research_dataset"]["temporal"] = obj_list
        return obj_list

    def _generate_v2_provenance(self, document: Dict) -> List:
        obj_list = []
        for provenance in self.provenance.all():
            data = {
                "title": provenance.title,
                "description": provenance.description,
            }

            if provenance.spatial:
                data["spatial"] = {
                    "place_uri": {
                        "in_scheme": provenance.spatial.in_scheme,
                        "url": provenance.spatial.url,
                        "pref_label": provenance.spatial.pref_label,
                    }
                }
                if full_address := provenance.spatial.full_address:
                    data["spatial"]["full_address"] = full_address
                if geographic_name := provenance.spatial.geographic_name:
                    data["spatial"]["geographic_name"] = geographic_name
            if temporal := provenance.temporal:
                data["temporal"] = {
                    "start_date": temporal.start_date,
                    "end_date": temporal.end_date,
                }
            if provenance.variables.all().count() != 0:
                data["variable"] = []
                for variable in provenance.variables.all():
                    var_data = {"pref_label": variable.pref_label}
                    data["variable"].append(var_data)
            if provenance.lifecycle_event:
                data["lifecycle_event"] = {
                    "pref_label": provenance.lifecycle_event.pref_label,
                    "identifier": provenance.lifecycle_event.url,
                    "in_scheme": provenance.lifecycle_event.in_scheme,
                }
            if provenance.event_outcome:
                data["event_outcome"] = {
                    "pref_label": provenance.event_outcome.pref_label,
                    "identifier": provenance.event_outcome.url,
                    "in_scheme": provenance.event_outcome.in_scheme,
                }
            if provenance.outcome_description:
                data["outcome_description"] = provenance.outcome_description

            if provenance.is_associated_with.all().count() != 0:
                data["was_associated_with"] = []
                for association in provenance.is_associated_with.all():
                    data["was_associated_with"].append(association.as_v2_data())

            obj_list.append(data)
        if len(obj_list) != 0:
            document["research_dataset"]["provenance"] = obj_list
        return obj_list

    def _generate_v2_access_rights(self) -> Dict:
        data = {
            "access_type": {
                "in_scheme": self.access_rights.access_type.in_scheme,
                "identifier": self.access_rights.access_type.url,
                "pref_label": self.access_rights.access_type.pref_label,
            },
            "license": [],
        }

        for license in self.access_rights.license.all():
            row = {"identifier": license.url, "title": license.pref_label}
            if description := license.description:
                row["description"] = description
            data["license"].append(row)
        for res_grounds in self.access_rights.restriction_grounds.all():
            if not data.get("restriction_grounds"):
                data["restriction_grounds"] = []
            data["restriction_grounds"].append(
                {
                    "identifier": res_grounds.url,
                    "pref_label": res_grounds.pref_label,
                    "in_scheme": res_grounds.in_scheme,
                }
            )
        return data

    def as_v2_dataset(self) -> Dict:
        def add_actor(role: str, document: Dict):
            actors = self.actors.filter(role=role)
            if actors.count() == 0:
                return
            if role != "publisher":
                document["research_dataset"][role] = []
            for dataset_actor in actors:
                data = dataset_actor.as_v2_data()
                if role == "publisher":
                    document["research_dataset"][role] = data
                else:
                    document["research_dataset"][role].append(data)

        doc = {
            "identifier": str(self.id),
            "deprecated": self.is_deprecated,
            "preservation_state": self.preservation_state,
            "state": self.state,
            "cumulative_state": self.cumulative_state.real,
            "date_created": self.created,
            "removed": self.is_removed,
            "metadata_provider_user": self.metadata_owner.user.username,
            "metadata_provider_org": self.metadata_owner.organization,
            "metadata_owner_org": self.metadata_owner.organization,
            "research_dataset": {
                "title": self.title,
                "description": self.description,
                "modified": self.modified,
                "preferred_identifier": self.persistent_identifier,
                "total_files_byte_size": self.total_files_byte_size,
                "keyword": self.keyword,
                "access_rights": self._generate_v2_access_rights(),
            },
            "data_catalog": {"identifier": self.data_catalog.id},
        }
        if self.cumulation_started:
            doc["date_cumulation_started"] = self.cumulation_started
        if self.last_cumulative_addition:
            doc["date_last_cumulative_addition"] = self.last_cumulative_addition
        if self.preservation_identifier:
            doc["preservation_identifier"] = self.preservation_identifier
        if self.last_modified_by:
            doc["user_modified"] = self.last_modified_by.username
        if self.issued:
            doc["research_dataset"]["issued"] = self.issued

        self._generate_v2_other_identifiers(doc)
        self._generate_v2_ref_data_field("language", doc, pref_label_text="title"),
        self._generate_v2_ref_data_field("field_of_science", doc),
        self._generate_v2_ref_data_field(
            "spatial",
            doc,
            top_level_key_name="place_uri",
            extra_top_level_fields=["geographic_name", "full_address"],
        )
        self._generate_v2_temporal(doc)
        self._generate_v2_provenance(doc)
        add_actor("creator", doc)
        add_actor("publisher", doc)
        return doc
