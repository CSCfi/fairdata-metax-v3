def test_download_placeholder_endpoints(admin_client):
    get_packages = admin_client.get("/v3/download/packages")
    assert get_packages.status_code == 503
    assert (
        get_packages.data["detail"]
        == "Getting available packages through Metax V3 not implemented."
    )

    request_packages = admin_client.post("/v3/download/packages", content_type="application/json")
    assert request_packages.status_code == 503
    assert (
        request_packages.data["detail"]
        == "Requesting package generation through Metax V3 not implemented."
    )

    authorize_download = admin_client.post(
        "/v3/download/authorize", content_type="application/json"
    )
    assert authorize_download.status_code == 503
    assert (
        authorize_download.data["detail"]
        == "Resource authorization through Metax V3 not implemented."
    )

    subscribe = admin_client.post("/v3/download/subscribe", content_type="application/json")
    assert subscribe.status_code == 503
    assert subscribe.data["detail"] == "Package subscriptions through Metax V3 not implemented."

    notify = admin_client.post("/v3/download/notifications", content_type="application/json")
    assert notify.status_code == 503
    assert notify.data["detail"] == "Package notifications through Metax V3 not implemented."
