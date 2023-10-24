# Token Based Authentication

## Bearer Tokens 

Bearer tokens are used by end-users trough Fairdata SSO and are manually generated from Metax UI. 

### Generating the token without SSO

You can generate Bearer token without SSO by following these steps.

#### Create superuser & generate new token

```bash
python manage.py createsuperuser
```
Login to admin panel from /admin endpoint. Go to endpoint /auth/tokens and generate a new bearer token. Copy the token value from the page. 

### Using the token

You can now use this token in requests by adding the following header

```
Authorization: Bearer <token>
```

### Hijacking another user to generate bearer token

You can hijack another user to generate a bearer token for them, this is useful when you want to test authorization of non-admin users. Go to admin-panel and open "Users" table under "Users" header. On the right side of any users, you can click the HIJACK button, it will direct you to non-existing page, but you can now go to /auth/tokens and generate new token for the user. On the bottom of the webpage you can release the hijack and return to your previous user. 

## DRF Tokens

If you want to use non-expiring token, you can enable DRF native token implementation. 

### Setting the environment variable

Start by setting the env-var ENABLE_DRF_TOKEN_AUTH=True in your .env file.

```
# .env file
ENABLE_DRF_TOKEN_AUTH=True 
```

### Running migrations

After setting the env-var, you must run python manage.py migrate to generate the necessary database tables:

```bash
python manage.py migrate
```

### Getting the token

While the env-var is true, all users will get a DRF-token on save operation. This includes admin users. There are two ways of getting this token.

#### Using the endpoint

You can send your user and password on post request to /drf-token-auth/ endpoint. It will return your token.

```
# POST /drf-token-auth
{"username":"username","password":"password"}
```

#### From the admin panel

DRF tokens can be found on the admin panels "Tokens" table under "Auth Token" section.

### Using the token

Add Authorization header to your requests in this form:

```
Authorization: Token <token value>
```
