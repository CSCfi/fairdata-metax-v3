# Creating REST API-endpoints

In most cases, REST API-endpoint needs following elements:

- Model
- Serializer
- View
- Filters
- Router URL

## Model

This is the Django-model that the endpoint will do operations for. Please read creating models

## Serializer

For most cases, ModelSerializer is the best way to serialize the Model object. Serializers are defined in the serializers.py module or one of its submodules. 

## View

like ModelSerializer, ModelViewSet gives all necessary httpd-methods for most use-cases. View is defined in the views.py module, or views/submodule.py file

## Filters

For GET-request URL-parameters, django-filters library provides out-of-the-box solution for filtering results. Filters are defined in the views.py module or if the views is split into submodules, in the same file as the View.

## Router-Urls

Django Rest Framework router should be used to register the new endpoint. Router definition is located at the apps urls.py file.
