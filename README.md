# fairdata-metax-service

* Metax is a metadata storage for Finnish research data

## Getting started

* How to get started with `fairdata-metax-service`

### Python dependencies

* This repository uses Poetry for managing Python dependencies securely
* Poetry generates a very strict `requirements.txt` file
* Poetry enables easy updates of minor security/bug patches from pip with `pyproject.toml`-defined version constraints
* The generated `requirements.txt` file is guaranteed to lock all dependencies and sub-dependencies
* The Poetry file `poetry.lock` stores hashes of all dependencies, if the integrity of the dependency-tree ever needs to be verified
* [Poetry documentation](https://python-poetry.org/docs/)

#### Install Poetry

* First, install [pipx](https://github.com/pypa/pipx)
* `pipx` is a system-wide Python application installer
* `pipx` creates a virtualenv for every package installed and automatically includes them in your workstation's path
* It can also uninstall any package installed using pipx
* After installation, you will have poetry available system-wide

```bash
# With pipx installed, install Poetry
pipx install poetry

# Upgrade if needed (minimum 1.2.0+ required)
pipx upgrade poetry
```

#### Install dependencies

* Poetry creates and manages its virtual environments in a dedicated cache directory on your workstation
* Tested with pip version `21.1.2`
* Tested with poetry version `1.8.0`

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

* Define `<required>` variables in the `.env` file
* Define other non-required values as needed

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

## Development operations

* The section below lists common development operations

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

* When the development server is running, access the admin panel at `localhost:<port>/v3/admin`
* Use the credentials generated in the _"Creating superuser"_ part of this readme.

### cli-tools

```bash
# Show all available management commands
python manage.py --help

# Show all setup.py commands
python setup.py --help
```

### Testing

* Run pytest managed tests with `pytest` command
* You can run tox tests with `tox` command.

```bash
# Run tests, stop on first failure, reuse test-database, run failed tests first, 2 workers
pytest -x --reuse-db -n 2 --ff
```

### Building MkDocs documentation

* The mkdocs port can be defined freely

```bash
# Running development server:
mkdocs serve -a localhost:8005

# Building mkdocs for production
mkdocs build
```

### Using Silk profiler

* Disabled by default
* Silk profiling can be turned on by setting `ENABLE_SILK_PROFILER` env-var to true
* The profiler is only available when on `development` DJANGO_ENV

```bash
# After setting ENABLE_SILK_PROFILER env-var to True, run:
python manage.py migrate
python manage.py collectstatic --no-input
```

* After successful setup, the profiler is available at /silk endpoint
* More information about Silk can be found from [official docs](https://github.com/jazzband/django-silk)

### Disabling debug-toolbar

* The Django Debug Toolbar can slow down SQL-queries
* Switch it off by setting `ENABLE_DEBUG_TOOLBAR` env-var to False

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

# Regenerating requirements.txt after modification of pyproject.toml
poetry export --without-hashes -o requirements.txt
poetry export --dev --without-hashes -o dev-requirements.txt 
```

## Formatting code

* Black formatter and isort are used for code formatting

```bash
# Ignore formatting commits by configuring git as follows
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

## Notes

### setup.cfg

* `setup.cfg` is the main configuration file due to still incomplete support of `pyproject.toml` in several development tools

### Database models

* The database models are based on following specifications:
* https://joinup.ec.europa.eu/collection/semantic-interoperability-community-semic/solution/dcat-application-profile-data-portals-europe/release/210
* https://www.w3.org/TR/vocab-dcat-3/

### PyScaffold

* This project has been set up using PyScaffold 3.3.1
* For details and usage information on PyScaffold see https://pyscaffold.org/.
