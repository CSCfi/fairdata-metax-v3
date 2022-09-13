import os
import secrets
import string

alphabet = string.ascii_letters + string.digits
default_password = "".join(secrets.choice(alphabet) for i in range(20))

METAX_SUPERUSER = {
    "username": os.getenv("METAX_USER_USERNAME", default="metax"),
    "email": os.getenv("METAX_USER_EMAIL", default="it-support@csc.fi"),
    "password": os.getenv("METAX_USER_PASSWORD", default=default_password),
}
