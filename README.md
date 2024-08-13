# fairdata-metax-service
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/e977dc412a19496bb3369b2d961cdbba)](https://app.codacy.com/gh/EarthModule/fairdata-metax-v3/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

- Metax is a metadata storage for Finnish research data

## Getting started

- How to get started with `fairdata-metax-service`

### Python dependencies

- This repository uses Poetry for managing Python dependencies securely
- Poetry enables easy updates of minor security/bug patches from pip with `pyproject.toml`-defined version constraints
- The Poetry file `poetry.lock` stores hashes of all dependencies, if the integrity of the dependency-tree ever needs to be verified
- [Poetry documentation](https://python-poetry.org/docs/)

#### Install Poetry

- First, install [pipx](https://github.com/pypa/pipx)
- `pipx` is a system-wide Python application installer
- `pipx` creates a virtualenv for every package installed and automatically includes them in your workstation's path
- It can also uninstall any package installed using pipx
- After installation, you will have poetry available system-wide

```bash
# With pipx installed, install Poetry
pipx install poetry

# Upgrade if needed (minimum 1.2.0+ required)
pipx upgrade poetry
```

#### Install dependencies

- Poetry creates and manages its virtual environments in a dedicated cache directory on your workstation
- Tested with pip version `21.1.2`
- Tested with poetry version `1.8.0`

```bash
# First, activate a poetry virtual environment
poetry shell

# ... then, install dependencies with poetry
poetry install
```

### Define local environmental variables

```bash
# Create a .env file based on .env.template
cp .env.template .env
```

- Define `<required>` variables in the `.env` file
- Define other non-required values as needed

### Creating a superuser

```bash
# In the repository root, run
python manage.py createsuperuser
```

### Initial setup commands

```bash
# In the repository root, run
python manage.py migrate
mkdir static
python manage.py collectstatic --no-input
```

### Optional: Docker setup

If you want to run a containerized version with PostgreSQL & Mecached, see: 🐋 [Docker](docs/developer-guide/install/docker.md)

## Getting started with V2 <-> V3 integration

- make sure both metaxes have a test catalog with same identifier
  - in V3, loading test data creates two test catalogs
    - `urn:nbn:fi:att:data-catalog-test` for non-harvested datasets and
    - `urn:nbn:fi:att:data-catalog-harvested-test` for harvested datasets
    - created with `python manage.py load_test_data`
  - create these also in V2
  - you might also need to patch the V3 catalogs with correct permissions:

```json
PATCH /v3/data-catalogs/urn:nbn:fi:att:data-catalog-harvested-test
{
	"dataset_groups_create": [
		"service"
	],
	"dataset_groups_admin": [
		"service"
	]
}
```

```json
PATCH /v3/data-catalogs/urn:nbn:fi:att:data-catalog-test
{
	"dataset_groups_create": [
		"fairdata_users"
	]
}
```

### V2 -> V3 integration

#### Changes in Metax V3

- create service user for V2 in V3

```bash
# in metax-service -repo
python manage.py create_api_user service_metax_v2 --groups metax_v2 service v2_migration
```

- create token for the user

```bash
# in metax-service -repo
python manage.py drf_create_token service_metax_v2
```

- If V2 is in a container and V3 is not, V2 cannot access V3 if it's running at `localhost:<port>`, so start the V3 development server at `0.0.0.0:<port>` instead. This way, V3 is available to containers at host `172.17.0.1:<port>`
  - `python manage.py runserver 0.0.0.0:<port>`
  - in this case, also add `172.17.0.1` to `ALLOWED_HOSTS` in V3 development settings `src/metax_service/settings/environments/development.py`

#### Changes in Metax V2

- add these settings to `fairdata-metax/docker-compose.yaml`, under metax-web environment:

```yaml
METAX_V3_HOST: <your local V3 host> # 172.17.0.1:<port>, if V2 is in a container and V3 is not
METAX_V3_TOKEN: <token of V2 service user>
METAX_V3_INTEGRATION_ENABLED: "true"
```

- redeploy metax_dev stack

### V3 -> V2 integration

#### Changes in Metax V3

- set up local V3 environment with these settings in `.env`:

```bash
METAX_V2_INTEGRATION_ENABLED=True
METAX_V2_HOST=<your local V2 host> # most likely https://metax.fd-dev.csc.fi
METAX_V2_USER=metax_service
METAX_V2_PASSWORD=test-metax_service
```

## Development operations

- The section below lists common development operations

### Running a development server

You can change the port number as needed

```bash
# Default development server
python manage.py runserver 8002

# Enhanced development server
python manage.py runserver_plus 8002

# Enhanced development server, enhanced interpreter
python manage.py runserver_plus --bpython 8002
```

### Accessing the admin panel

- When the development server is running, access the admin panel at `localhost:<port>/v3/admin`
- Use the credentials generated in the _"Creating superuser"_ part of this readme.

### cli-tools

```bash
# Show all available management commands
python manage.py --help

# Show all setup.py commands
python setup.py --help
```

### Testing

- Run pytest managed tests with `pytest` command
- You can run tox tests with `tox` command.

```bash
# Run tests, stop on first failure, reuse test-database, run failed tests first, 2 workers
pytest -x --reuse-db -n 2 --ff
```

### Building MkDocs documentation

- The mkdocs port can be defined freely

```bash
# Running development server:
mkdocs serve -a localhost:8005

# Building mkdocs for production
mkdocs build
```

### Using Silk profiler

- Disabled by default
- Silk profiling can be turned on by setting `ENABLE_SILK_PROFILER` env-var to true
- The profiler is only available when on `development` DJANGO_ENV

```bash
# After setting ENABLE_SILK_PROFILER env-var to True, run:
python manage.py migrate
python manage.py collectstatic --no-input
```

- After successful setup, the profiler is available at /silk endpoint
- More information about Silk can be found from [official docs](https://github.com/jazzband/django-silk)

### Disabling debug-toolbar

- The Django Debug Toolbar can slow down SQL-queries
- Switch it off by setting `ENABLE_DEBUG_TOOLBAR` env-var to False

## Managing dependencies with Poetry

```bash
# Adding developer dependencies
poetry add -D <package>

# Adding application dependencies
poetry add <package>

# Updating all dependencies
poetry update

# Removing dependencies
poetry remove (-D) <package>
```

## Formatting code

- Black formatter and isort are used for code formatting

```bash
# Ignore formatting commits by configuring git as follows
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

### Using ruff

Install ruff globally with 

```bash
pipx install ruff
```

on the repository root, run ruff check ./

```bash
ruff check ./
```

## Notes

### setup.cfg

- `setup.cfg` is the main configuration file due to still incomplete support of `pyproject.toml` in several development tools

### Database models

- The database models are based on following specifications:
- https://joinup.ec.europa.eu/collection/semantic-interoperability-community-semic/solution/dcat-application-profile-data-portals-europe/release/210
- https://www.w3.org/TR/vocab-dcat-3/

### PyScaffold

- This project has been set up using PyScaffold 3.3.1
- For details and usage information on PyScaffold see https://pyscaffold.org/.
