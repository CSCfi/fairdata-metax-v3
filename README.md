# fairdata-metax-service

- Metax is a metadata storage for Finnish research data

## Getting started

- How to get started with `fairdata-metax-service`

### Python dependencies

- This repository uses [uv](https://docs.astral.sh/) for managing Python dependencies
- `uv` generates a very strict `requirements.txt` file
- `uv` enables easy installation and updating of dependencies using version constraints defined in `pyproject.toml`
- Hashes and other information on installed dependencies are stored in `uv.lock`
- Locked dependencies can be exported as `requirements.txt` which can then be installed using `pip` in environments that don't use `uv`

#### Install uv

First, [install uv](https://docs.astral.sh/uv/getting-started/installation). If using pipx:
```bash
# Install uv
pipx install uv

# To updgrade uv to a newer version when needed
pipx upgrade uv
```

To run a Python script, use `uv run <script_name.py>`, which
- reads dependency constraints and configuration from `pyproject.toml`
- resolves dependencies using the `uv.lock` file and updates it
- creates a virtual environment in `.venv` subdirectory or updates it
- runs the actual command

If no suitable Python version is installed, `uv` also downloads the
newest compatible Python version. To use a specific python version,
use e.g. `uv python pin 3.12` which creates a `.python-version` file that `uv` will use.

The virtual environment is an ordinary Python virtual env and can be activated
with `source .venv/bin/activate` if you want to use `python <script_name.py>` to run scripts.


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
uv run manage.py createsuperuser
```

### Initial setup commands

```bash
# In the repository root, run
uv run manage.py migrate
mkdir static
uv run manage.py collectstatic --no-input
```
* Alternatively if you run Metax in Docker, you can use `first_time_setup.sh` script, which will initialize the database. Note: To work, the script expects that Metax is running inside a Docker container named `metax-v3`
```bash
# In the repository root, run
chmod a+x first_time_setup.sh
./first_time_setup.sh
```

### Optional: Docker setup

If you want to run a containerized version with PostgreSQL & Mecached, see: 🐋 [Docker](docs/developer-guide/install/docker.md)

## Getting started with V2 <-> V3 integration

- make sure both metaxes have a test catalog with same identifier
  - in V3, loading test data creates two test catalogs
    - `urn:nbn:fi:att:data-catalog-test` for non-harvested datasets and
    - `urn:nbn:fi:att:data-catalog-harvested-test` for harvested datasets
    - created with `uv run manage.py load_test_data`
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
uv run manage.py create_api_user service_metax_v2 --groups metax_v2 service v2_migration
```

- create token for the user

```bash
# in metax-service -repo
uv run manage.py drf_create_token service_metax_v2
```

- If V2 is in a container and V3 is not, V2 cannot access V3 if it's running at `localhost:<port>`, so start the V3 development server at `0.0.0.0:<port>` instead. This way, V3 is available to containers at host `172.17.0.1:<port>`
  - `uv run manage.py runserver 0.0.0.0:<port>`
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
uv run manage.py runserver 8002

# Enhanced development server
uv run manage.py runserver_plus 8002

# Enhanced development server, enhanced interpreter
uv run manage.py runserver_plus --bpython 8002
```

### Running background tasks

Set `ENABLE_BACKGROUND_TASKS=true` in `.env`.
Run development server and run the task processing
cluster in e.g. another terminal

```bash
uv run manage.py qcluster
```

### Accessing the admin panel

- When the development server is running, access the admin panel at `localhost:<port>/v3/admin`
- Use the credentials generated in the _"Creating superuser"_ part of this readme.

### cli-tools

```bash
# Show all available management commands
uv run manage.py --help
```

### Testing

- Run pytest managed tests with `pytest` command
- You can run tox tests with `tox` command.

```bash
# Run tests, stop on first failure, reuse test-database, run failed tests first, 2 workers
uv run pytest -x --reuse-db -n 2 --ff
```

### Building MkDocs documentation

- The mkdocs port can be defined freely

```bash
# Running development server:
uv run mkdocs serve -a localhost:8005

# Building mkdocs for production
uv run mkdocs build
```

### Using Silk profiler

- Disabled by default
- Silk profiling can be turned on by setting `ENABLE_SILK_PROFILER` env-var to true
- The profiler is only available when on `development` DJANGO_ENV

```bash
# After setting ENABLE_SILK_PROFILER env-var to True, run:
uv run manage.py migrate
uv run manage.py collectstatic --no-input
```

- After successful setup, the profiler is available at /v3/silk endpoint
- More information about Silk can be found from [official docs](https://github.com/jazzband/django-silk)

### Disabling debug-toolbar

- The Django Debug Toolbar can slow down SQL-queries
- Switch it off by setting `ENABLE_DEBUG_TOOLBAR` env-var to False

## Managing dependencies with uv

```bash
# Adding developer dependencies
uv add --dev <packages>

# Adding application dependencies
uv add <packages>

# Check dependencies for vulnerabilities (still experimental in uv 0.11.7)
uv audit

# List dependencies from pyproject.toml that have newer versions
uv tree --outdated --depth 1 | grep latest:

# Updating all dependencies while maintaing constraints defined in pyproject.toml
uv lock --up

# Updating dependency constraints in pyproject.toml, e.g. to install a new major version
uv add [--dev] "package>=6.0.1,<7"

# Removing dependencies
uv remove [--dev] <packages>

# Regenerating requirements.txt after dependencies have changed
uv export --frozen --no-hashes --no-annotate --format requirements.txt --no-dev > requirements.txt
uv export --frozen --no-hashes --no-annotate --format requirements.txt > dev-requirements.txt
```

## Git hooks

To help ensure `requirements.txt` files are up-to-date, there is a post-commit hook that notifies
if the exported requirements are out of sync. See `hooks/HOOKS.md` for details.

## Formatting code

- Black formatter and isort are used for code formatting

```bash
# Ignore formatting commits by configuring git as follows
git config blame.ignoreRevsFile .git-blame-ignore-revs
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
