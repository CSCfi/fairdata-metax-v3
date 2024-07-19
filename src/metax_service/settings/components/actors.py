# URL where organization data is fetched from
ORGANIZATION_FETCH_API_URL = (
    "https://researchfi-api-production.2.rahtiapp.fi/portalapi/organization/_search?size=100"
)

# File where fetched organization data is cached
ORGANIZATION_DATA_FILE = "src/apps/actors/local_data/organizations.csv"

# Common reference data organization attributes
ORGANIZATION_SCHEME = "http://uri.suomi.fi/codelist/fairdata/organization"
ORGANIZATION_BASE_URI = "http://uri.suomi.fi/codelist/fairdata/organization/code/"
