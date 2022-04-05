from pytest_bdd import scenario, given, when, then


@given("I'm an admin user")
def admin_user():
    pass


@when("I post a new DataCatalog to the datacatalog REST-endpoint")
def datacatalog_post_request():
    raise NotImplementedError(u'STEP: When I post a new DataCatalog to the datacatalog REST-endpoint')


@then("New DataCatalog object is saved to database")
def check_datacatalog_is_created():
    raise NotImplementedError(u'STEP: Then New DataCatalog object is saved to database')


@given("It should return 201 http code")
def step_impl():
    raise NotImplementedError(u'STEP: And It should return 201 http code')


@when("I post delete request to datacatalog REST-endpoint")
def step_impl():
    raise NotImplementedError(u'STEP: When I post delete request to datacatalog REST-endpoint')
