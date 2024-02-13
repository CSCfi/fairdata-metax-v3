from django.apps import apps


def test_model_ordering():
    """Check that all concrete models have a default ordering.

    Subclasses that define their own Meta class do not automatically inherit
    meta attributes such as ordering. In such cases, either explicitly extend
    the base Meta class or manually define ordering in the new Meta class.
    See https://docs.djangoproject.com/en/5.0/topics/db/models/#meta-inheritance
    """
    checked_apps = ["actors", "core", "common", "files", "cache", "refdata", "users"]
    missing_orderings = []
    for app in checked_apps:
        config = apps.get_app_config(app)
        for model in config.get_models():
            model_name = model.__name__
            if model_name.startswith("Historical"):
                continue  # ignore historical models
            if not model._meta.ordering:
                missing_orderings.append(f"{app}.{model_name}")
    assert missing_orderings == []
