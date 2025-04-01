def test_dataset_rems_approval_type(admin_client, dataset_a_json, data_catalog, reference_data, settings):

    access_rights = dataset_a_json["access_rights"]
    access_rights["access_type"] = {
        "url": "http://uri.suomi.fi/codelist/fairdata/access_type/code/permit"
    }
    access_rights["restriction_grounds"] = [
        {"url": "http://uri.suomi.fi/codelist/fairdata/restriction_grounds/code/research"}
    ]
    access_rights["rems_approval_type"] = "automatic"
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 400

    settings.REMS_ENABLED = True
    res = admin_client.post("/v3/datasets", dataset_a_json, content_type="application/json")
    assert res.status_code == 201
    assert res.data["access_rights"]["rems_approval_type"] == "automatic"
