from split_settings.tools import include

include("production.py")

ALLOW_LOAD_TEST_DATA = True

# Demo-type environments are expected to use django_env: 'stable'
ALLOW_LOAD_PAS_TEST_DATA = True
