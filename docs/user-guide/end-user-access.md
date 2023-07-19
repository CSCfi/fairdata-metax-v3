# End User Access

Write access and some other features in Metax require user authentication. For advanced usage using the API directly, Metax supports authentication of API requests with bearer authentication. This requires creating an API token.

## Creating an API token

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

## Making authenticated requests

To make an authenticated request, include the header `Authorization: Bearer <token>` in your request, where `<token>` is the token value you have written down.

Below is an example of requesting user details for the authenticated user in Python.

```python
import requests

# Print user details using bearer authentication
headers = { 'Authorization': 'Bearer 3e621588143f41cdd792fd32' }
response = requests.get('https://metax.fairdata.fi/auth/user', headers=headers)
print(response.json())
```
