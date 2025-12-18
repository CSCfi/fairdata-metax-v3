docker exec -it $(docker ps -q -f name="metax-v3\.") python manage.py migrate
docker exec -it $(docker ps -q -f name="metax-v3\.") python manage.py index_reference_data
docker exec -it $(docker ps -q -f name="metax-v3\.") python manage.py index_organizations
docker exec -it $(docker ps -q -f name="metax-v3\.") python manage.py load_test_data
docker exec -it $(docker ps -q -f name="metax-v3\.") python manage.py load_admin_organizations
docker exec -it -e AUTH_TOKEN_VALUE=smeartesttoken $(docker ps -q -f name="metax-v3\.") python manage.py create_api_user service_smartsmear --groups smartsmear service --token-override
docker exec -it -e AUTH_TOKEN_VALUE=idatesttoken $(docker ps -q -f name="metax-v3\.") python manage.py create_api_user service_ida --groups ida service --token-override
docker exec -it -e AUTH_TOKEN_VALUE=pastesttoken $(docker ps -q -f name="metax-v3\.") python manage.py create_api_user service_tpas --groups pas service --token-override
docker exec -it -e DJANGO_SUPERUSER_PASSWORD=test1234 $(docker ps -q -f name="metax-v3\.") python manage.py createsuperuser --no-input --username admin_su --email ""
