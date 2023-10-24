# Installation

## Python dependencies

### With Poetry

```bash
poetry install
```

### Without Poetry 

```bash
pip install -r dev-requirements.txt
```

## Setup PostgreSQL docker container

The following command will map new named PostgreSQL database container to localhost port 5452. It will generate the database, database user and password in the process:

```bash
docker run -d -p 5452:5432 --name metax-v3-postgres -v metax-v3-postgres:/var/lib/postgresql/data -e POSTGRES_USER=<db_user> -e POSTGRES_PASSWORD=<password> -e POSTGRES_DB=metax_db --restart=always  postgres:12
```

## Setup memcached as cache with docker container

```bash
docker run -d -p 11211:11211 memcached -I 10m
```

set ENABLE_MEMCACHED env-var in .env file:

```bash
ENABLE_MEMCACHED=true
```

## Update Environmental Variables

In the repository root, create `.env` file and add at least required variables from `.env.template` file.

## Initial setup commands

In the repository root, run:

```bash
python manage.py migrate
```

## Running development server

Launch default development server with 

```bash
python manage.py runserver <port-number>
``` 

example:  
```bash
python manage.py runserver 8002
```

You can use enchanted development server with 

```bash
python manage.py runserver_plus <port-number>
```
