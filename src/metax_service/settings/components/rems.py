from environs import Env

env = Env()

REMS_ENABLED = env.bool("REMS_ENABLED", False)
REMS_BASE_URL = env.str("REMS_BASE_URL", "http://localhost:3000")
REMS_USER_ID = env.str("REMS_USER_ID", "owner")
REMS_API_KEY = env.str("REMS_API_KEY", "42")
REMS_ORGANIZATION_ID = env.str("REMS_ORGANIZATION_ID", "csc")
