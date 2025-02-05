# User Access

## End User Access

The primary way for end users to use Metax is by using [Fairdata Etsin](https://etsin.fairdata.fi) for viewing datasets and [Fairdata Qvain](https://qvain.fairdata.fi) for creating and editing datasets. Metax supports Fairdata SSO authentication that puts Fairdata services under a unified login. Logging into one of the supported services such as Metax, Etsin or Qvain logs you into all of them.

### End user token authentication

For advanced usage using the API directly, Metax supports authentication of API requests with bearer authentication. This requires creating an API token.

#### Creating an API token

API tokens for authentication can be created as follows:

- Log in to Metax using the UI
- Navigate to "API tokens" from the user dropdown
- Click "Create new API token"
- Write down the `token` value

The created token will be valid only for a limited time. You can have multiple valid tokens at the same time. You can manage your tokens and view their expiration times on the token list.

<!-- prettier-ignore -->
!!! note
    The full token is stored as a hashed value and cannot be recovered afterwards.
    If you lose the value, you need to create a new token.

#### Making authenticated requests

To make an authenticated request, include the header `Authorization: Bearer <token>` in your request, where `<token>` is the token value you have written down.

Below is an example of requesting user details for the authenticated user in Python.

```python
import requests

# Print user details using bearer authentication
headers = { 'Authorization': 'Bearer 3e621588143f41cdd792fd32' }
response = requests.get('https://metax.fairdata.fi/v3/auth/user', headers=headers)
print(response.json())
```

## Service User Access

Service users use token authentication with a token provided by Fairdata. 
To authenticate a request, include the header `Authorization: Token <token>`, 
where `<token>` is the provided token value.

Below is an example of requesting user details for a service user in Python.

```python
import requests

# Print service user details using provided token
headers = { 'Authorization': 'Token 18f6e252928699407e5a95d7adef841440e95511' }
response = requests.get('https://metax.fairdata.fi/v3/auth/user', headers=headers)
print(response.json())
```
