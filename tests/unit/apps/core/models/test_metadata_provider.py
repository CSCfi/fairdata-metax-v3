def test_create_metadata_provider_with_user(metadata_provider, user):
    metadata_provider.user = user
    metadata_provider.save()
    assert metadata_provider.id is not None
    assert metadata_provider.user is not None
    assert metadata_provider.user == user


def test_delete_metadata_provider_with_foreign_keys(metadata_provider, user):
    metadata_provider.user = user
    metadata_provider.save()
    metadata_provider.delete()
    user.delete()
    assert metadata_provider.removed
    assert user.is_removed
