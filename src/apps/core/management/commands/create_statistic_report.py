import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Sum


from apps.core.models import (
    Dataset,
    FileSet,
    MetadataProvider,
    OrganizationStatistics,
    ProjectStatistics,
)
from apps.files.models import File, FileStorage

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        logger.info("Creating statistic summary")

        OrganizationStatistics.objects.all().delete()
        ProjectStatistics.objects.all().delete()

        all_projects = FileStorage.objects.order_by("csc_project").values("csc_project").distinct()

        for project in all_projects:
            project_id = project["csc_project"]
            if not project_id:
                continue

            ida_published_pids = []
            ida_count = 0
            ida_byte_size = 0
            pas_published_pids = []
            pas_count = 0
            pas_byte_size = 0
            project_storages = list(
                FileStorage.objects.filter(csc_project=project_id).values("id").distinct()
            )
            for storage in project_storages:
                storage_id = storage["id"]

                ida_published_datasets = Dataset.objects.filter(
                    file_set__storage_id=storage_id,
                    state="published",
                    data_catalog__id="urn:nbn:fi:att:data-catalog-ida",
                )

                ida_filesets = list(
                    FileSet.objects.filter(dataset__in=ida_published_datasets).values_list(
                        "id", flat=True
                    )
                )
                # M2M for FileSet<->File is in implicitly created model
                # FileSet.files.through that has fields "id", "file_set", "file_id".
                filesets_through = FileSet.files.through.objects
                ida_published_files = File.objects.filter(
                    Exists(
                        filesets_through.filter(
                            fileset_id__in=ida_filesets, file_id=OuterRef("id")
                        )
                    )
                )

                ida_published_pids.extend(
                    list(
                        ida_published_datasets.order_by("persistent_identifier")
                        .values_list("persistent_identifier", flat=True)
                        .distinct()
                    )
                )
                aggregates = ida_published_files.aggregate(
                    count=Count("*"), size=Sum("size", default=0)
                )
                ida_count += aggregates["count"]
                ida_byte_size += aggregates["size"]

                pas_published_datasets = Dataset.objects.filter(
                    file_set__storage_id=storage_id,
                    state="published",
                    data_catalog__id="urn:nbn:fi:att:data-catalog-pas",
                )

                pas_filesets = list(
                    FileSet.objects.filter(dataset__in=pas_published_datasets).values_list(
                        "id", flat=True
                    )
                )
                pas_published_files = File.objects.filter(
                    Exists(
                        filesets_through.filter(
                            fileset_id__in=pas_filesets, file_id=OuterRef("id")
                        )
                    )
                )

                pas_published_pids.extend(
                    list(
                        pas_published_datasets.order_by("persistent_identifier")
                        .values_list("persistent_identifier", flat=True)
                        .distinct()
                    )
                )
                aggregates = pas_published_files.aggregate(
                    count=Count("*"), size=Sum("size", default=0)
                )
                pas_count += aggregates["count"]
                pas_byte_size += aggregates["size"]

            ProjectStatistics.objects.create(
                project_identifier=project_id,
                ida_count=ida_count,
                ida_byte_size=ida_byte_size,
                ida_published_datasets=ida_published_pids,
                pas_count=pas_count,
                pas_byte_size=pas_byte_size,
                pas_published_datasets=pas_published_pids,
            )

        all_organizations = list(
            MetadataProvider.objects.order_by("organization")
            .values_list("organization", flat=True)
            .distinct()
        )

        # Datasets from these organizations were harvested by Etsin-harvester
        # so their metadata owner organization is fairdata.fi, but they need
        # to be attributed to their correct organizations
        harvested_organizations = {
            "syke.fi": "urn:nbn:fi:att:data-catalog-harvest-syke",
            "fsd.tuni.fi": "urn:nbn:fi:att:data-catalog-harvest-fsd",
            "kielipankki.fi": "urn:nbn:fi:att:data-catalog-harvest-kielipankki",
        }

        for org in harvested_organizations.keys():
            if org not in all_organizations:
                all_organizations.append(org)

        if "fairdata.fi" in all_organizations:
            all_organizations.remove("fairdata.fi")

        for org_id in all_organizations:
            if not org_id:
                continue

            all_datasets = Dataset.objects.filter(
                metadata_owner__organization=org_id, state="published"
            )
            ida_datasets = all_datasets.filter(data_catalog__id="urn:nbn:fi:att:data-catalog-ida")
            pas_datasets = all_datasets.filter(data_catalog__id="urn:nbn:fi:att:data-catalog-pas")
            att_datasets = all_datasets.filter(data_catalog__id="urn:nbn:fi:att:data-catalog-att")

            count_total = all_datasets.count()
            count_ida = ida_datasets.count()
            count_pas = pas_datasets.count()
            count_att = att_datasets.count()

            filesets_through = FileSet.files.through.objects
            total_filesets = FileSet.objects.filter(dataset__in=all_datasets)
            total_published_files = File.objects.filter(
                Exists(
                    filesets_through.filter(
                        fileset_id__in=list(total_filesets), file_id=OuterRef("id")
                    )
                )
            )
            byte_size_total = total_published_files.aggregate(Sum("size", default=0))["size__sum"]

            ida_filesets = FileSet.objects.filter(dataset__in=ida_datasets)
            ida_published_files = File.objects.filter(
                Exists(
                    filesets_through.filter(
                        fileset_id__in=list(ida_filesets), file_id=OuterRef("id")
                    )
                )
            )
            byte_size_ida = ida_published_files.aggregate(Sum("size", default=0))["size__sum"]

            pas_filesets = FileSet.objects.filter(dataset__in=pas_datasets)
            pas_published_files = File.objects.filter(
                Exists(
                    filesets_through.filter(
                        fileset_id__in=list(pas_filesets), file_id=OuterRef("id")
                    )
                )
            )
            byte_size_pas = pas_published_files.aggregate(Sum("size", default=0))["size__sum"]

            if org_id in harvested_organizations.keys():
                count_total += Dataset.objects.filter(
                    data_catalog__id=harvested_organizations[org_id], state="published"
                ).count()

            count_other = count_total - count_ida - count_pas - count_att

            OrganizationStatistics.objects.create(
                organization=org_id,
                count_total=count_total,
                count_ida=count_ida,
                count_pas=count_pas,
                count_att=count_att,
                count_other=count_other,
                byte_size_total=byte_size_total,
                byte_size_ida=byte_size_ida,
                byte_size_pas=byte_size_pas,
            )

        logger.info("Statistic summary created")
