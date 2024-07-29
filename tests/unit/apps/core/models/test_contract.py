def test_create_contract(contract):
    contract.save()
    assert contract.id is not None
