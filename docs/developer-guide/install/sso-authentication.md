# Fairdata SSO Authentication

Metax API endpoints support user authentication via Fairdata SSO using SSO session cookies.

## Configuration variables

To enable SSO authentication support, add the following variables to the Metax `.env` file:

| Variable               | Type    | Usage                                                                            |
| ---------------------- | ------- | -------------------------------------------------------------------------------- |
| ENABLE_SSO_AUTH        | boolean | Enable SSO authentication. Defaults to false.                                    |
| SSO_HOST               | string  | Host where SSO requests will be sent to, e.g. `https://sso.<fairdata-domain>.fi` |
| SSO_SESSION_COOKIE     | string  | Name of the SSO session cookie.                                                  |
| SSO_SECRET_KEY         | string  | Secret key used for verifying the SSO session token.                             |
| SSO_METAX_SERVICE_NAME | string  | Service name Metax uses to identify itself for SSO, e.g. `METAX`.                |

## External service configuration

To allow external services to use the SSO session for cross-site Metax requests, they need to be listed in `CORS_ALLOWED_ORIGINS`, and `CORS_ALLOW_CREDENTIALS` has to be enabled. For unsafe requests (`POST`, `PUT`, etc.), the origin also has to be listed in `CSRF_TRUSTED_ORIGINS`. The CSRF token can be retrieved from `/v3/auth/user` after SSO login and needs to be included as `X-CSRFToken` header in each unsafe request.

<!-- prettier-ignore -->
!!! NOTE
    The CSRF token is only valid during the SSO session and needs to be retrieved again after a new login. Also, the value is masked for security reasons which makes it look different on each `/v3/auth/user` request.

The related `.env` variables are:

| Variable               | Type                 | Usage                                                                                            |
| ---------------------- | -------------------- | ------------------------------------------------------------------------------------------------ |
| CORS_ALLOWED_ORIGINS   | comma-separated list | List of origins allowed to make cross-site requests, e.g. `https://service.<fairdata-domain>.fi` |
| CORS_ALLOW_CREDENTIALS | boolean              | Allow cookies to be included in cross-site requests. Defaults to false.                          |
| CSRF_TRUSTED_ORIGINS   | comma-separated list | List of trusted origins for unsafe requests, e.g. `service.<fairdata-domain>.fi`                 |

## Development server

To be able to access the SSO session cookies, Metax needs to be running HTTPS and has to be in the same domain as SSO cookies. For example, add

```
127.0.0.1       metaxv3.fd-dev.csc.fi
```

to `/etc/hosts` and run

```
poetry run python manage.py runserver_plus 0:8100 \
--cert-file <path-to-fd-dev.csc.fi.crt.pem> \
--key-file <path-to-fd-dev.csc.fi.key.pem>
```

## Example configuration for local Etsin and Qvain

For local Etsin/Qvain development, the following values can be used in Metax `.env` file.

```
# SSO configuration
ENABLE_SSO_AUTH=true
SSO_SECRET_KEY=<e.g. SSO.key from etsin-qvain app_config_dev>
SSO_SESSION_COOKIE=fd_dev_csc_fi_fd_sso_session
SSO_HOST=https://sso.fd-dev.csc.fi
# SSO does not yet have METAX service defined but QVAIN can be used instead
SSO_METAX_SERVICE_NAME=QVAIN

# External service configuration
CSRF_TRUSTED_ORIGINS=etsin.fd-dev.csc.fi,qvain.fd-dev.csc.fi
CORS_ALLOWED_ORIGINS=https://etsin.fd-dev.csc.fi,https://qvain.fd-dev.csc.fi
CORS_ALLOW_CREDENTIALS=true
```

## Testing requests from Etsin and Qvain

After updating configuration and restarting the development server, it should be possible to make requests to Metax from the browser in Etsin or Qvain. Note that cookies are not sent for cross-origin requests by default and "unsafe" methods (e.g. POST) require a CSRF token in the `X-CSRFToken` header.

<details><summary>Example of creating a dataset from external service, can be run in Qvain javascript console.</summary>

```javascript
const metaxUrl = "https://metaxv3.fd-dev.csc.fi:8100";

// Get CSRF token required for POST requests
const resp = await fetch(`${metaxUrl}/v3/auth/user`, {
  credentials: "include", // required for the SSO cookie to be sent
});
const data = await resp.json();

// Create dataset
const resp2 = await fetch(`${metaxUrl}/v3/datasets`, {
  method: "POST",
  body: JSON.stringify({
    data_catalog: "urn:nbn:fi:att:data-catalog-ida",
    title: {
      en: "Test dataset",
    },
  }),
  headers: {
    "X-CSRFToken": data.metax_csrf_token,
    "Content-Type": "application/json",
  },
  credentials: "include",
});
console.log((await resp2.json()).id); // print id of created dataset
```
