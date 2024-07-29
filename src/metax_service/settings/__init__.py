"""
This is a django-split-settings main file.
For more information read this:
https://github.com/sobolevn/django-split-settings
To change settings file:
`DJANGO_ENV=production python manage.py runserver`
"""

from os import environ

from dotenv import load_dotenv
from split_settings.tools import include

load_dotenv()
# Managing environment via DJANGO_ENV variable:
environ.setdefault("DJANGO_ENV", "development")
ENV = environ["DJANGO_ENV"]

base_settings = [
    "components/base.py",
    "components/refdata.py",
    "components/actors.py",
    "components/users.py",
    "components/cache.py",
    "environments/{0}.py".format(ENV),
]
# Include settings:
include(*base_settings)
