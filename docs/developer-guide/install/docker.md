# Docker setup

This describes how to run a Dockerized version of `fairdata-metax-service`

## PostgreSQL container

* The following command will map new named PostgreSQL database container to localhost port 5452
* It will generate the database, database user and password in the process

```bash
docker run -d -p 5452:5432 --name metax-v3-postgres -v metax-v3-postgres:/var/lib/postgresql/data -e POSTGRES_USER=metax -e POSTGRES_PASSWORD=password -e POSTGRES_DB=metax_db --restart=always  postgres:12
```

## Memcached container

```bash
# Run container
docker run -d -p 11211:11211 memcached -I 10m

# Then, set ENABLE_MEMCACHED env-var in .env file:
ENABLE_MEMCACHED=true
```

# Docker troubleshooting

## Role "metax" does not exist

This can happen when trying to run migrations

```bash
# Solution
docker exec -it metax-v3-postgres bash
psql -U postgres
CREATE USER metax WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE metax_db TO metax;
\q
exit
```

## Must be superuser to create this extension

This can happen when trying to run migrations

```bash
# Solution
docker exec -it metax-v3-postgres bash
psql -U postgres
ALTER USER metax WITH SUPERUSER;
\q
exit
```
