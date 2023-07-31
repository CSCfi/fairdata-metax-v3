import logging
from argparse import ArgumentParser

import httpx
from django.core.management.base import BaseCommand

from apps.core.models import LegacyDataset

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Migrate V2 datasets to V3 from specific Metax instance
    Examples:
        Migrate all publicly available datasets from metax instance

            $ python manage.py migrate_v2_datasets -a -mi https://metax.fairdata.fi

        Migrate only specified V2 datasets

            $ python manage.py migrate_v2_datasets -ids cr955e904-e3dd-4d7e-99f1-3fed446f96d1 cr955e904-e3dd-4d7e-99f1-3fed446f96d3 -mi https://metax.fairdata.fi
    """

    allow_fail = False
    failed_datasets = []

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--identifiers",
            "-ids",
            nargs="+",
            type=str,
            help="List of Metax V1-V2 identifiers to migrate",
        )
        parser.add_argument(
            "--all",
            "-a",
            action="store_true",
            required=False,
            default=False,
            help="Migrate all publicly available datasets from provided metax instance",
        )
        parser.add_argument(
            "--allow-fail",
            "-af",
            action="store_true",
            required=False,
            default=False,
            help="Allow individual datasets to fail without halting the migration",
        )
        parser.add_argument(
            "--metax-instance",
            "-mi",
            type=str,
            required=False,
            default="http://localhost:8002",
            help="Fully qualified Metax instance URL to migrate datasets from",
        )
        parser.add_argument(
            "--pagination_size",
            "-ps",
            type=int,
            required=False,
            default=100,
            help="Number of datasets to migrate per request",
        )

    def get_or_create_dataset(self, data):
        try:
            dataset, created = LegacyDataset.objects.get_or_create(
                dataset_json__identifier=data["identifier"],
                defaults={"dataset_json": data},
            )
            self.stdout.write(f"{dataset.id=}, {dataset.legacy_identifier=}, {created=}")
            return dataset
        except Exception as e:
            if self.allow_fail:
                logger.error(e)
                self.stdout.write(f"Failed to migrate dataset payload {data}")
                self.failed_datasets.append(data)
            else:
                raise e

    def migrate_from_list(self, list_json):
        created_instances = []
        for data in list_json:
            dataset = self.get_or_create_dataset(data)
            if dataset:
                created_instances.append(dataset)
        return created_instances

    def handle(self, *args, **options):
        identifiers = options.get("identifiers")
        migrate_all = options.get("all")
        metax_instance = options.get("metax_instance")
        self.allow_fail = options.get("allow_fail")
        limit = options.get("pagination_size")

        datasets = []
        if identifiers and migrate_all:
            self.stderr.write("--identifiers and --all are mutually exclusive")
        if identifiers and not migrate_all:
            for identifier in identifiers:
                response = httpx.get(f"{metax_instance}/rest/v2/datasets/{identifier}")
                dataset_json = response.json()
                datasets.append(self.get_or_create_dataset(dataset_json))
        if migrate_all and not identifiers:
            response = httpx.get(
                f"{metax_instance}/rest/v2/datasets?limit={limit}&include_legacy=true"
            )
            response_json = response.json()
            datasets = datasets + self.migrate_from_list(response_json["results"])
            while next_url := response_json.get("next"):
                response = httpx.get(next_url)
                response_json = response.json()
                datasets = datasets + self.migrate_from_list(response_json["results"])
        self.stdout.write(
            f"successfully migrated {len(datasets)} datasets: {[str(x.id) for x in datasets]}"
        )
        self.stdout.write(
            f"legacy identifiers of migrated datasets: "
            f"{[str(x.legacydataset.legacy_identifier) for x in datasets]}"
        )
        if len(self.failed_datasets) > 0:
            self.stdout.write(
                f"failed to migrate {len(self.failed_datasets)} "
                f"datasets: {[str(x['identifier']) for x in self.failed_datasets]}"
            )
