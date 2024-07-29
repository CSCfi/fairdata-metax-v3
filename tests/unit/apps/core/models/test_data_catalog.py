def test_create_data_catalog_with_foreign_keys(data_catalog):
    assert data_catalog.id is not None


def test_delete_data_catalog_with_foreign_keys(data_catalog):
    publisher = data_catalog.publisher
    data_catalog.delete()
    assert publisher.catalogs.filter(id=data_catalog.id).count() == 0
