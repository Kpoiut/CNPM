from datetime import datetime

from scripts.quality.seed_ci_reference_data import _reference_accounts, _reference_properties


def test_ci_reference_accounts_do_not_preempt_admin_bootstrap():
    accounts = _reference_accounts()

    assert len(accounts) == 13
    assert {account["role"] for account in accounts} == {"user"}
    assert len({account["username"] for account in accounts}) == 13
    assert all(str(account["hashed_password"]).startswith("$2") for account in accounts)


def test_ci_reference_properties_match_canonical_ml_scope():
    properties = _reference_properties(datetime.now())

    assert len(properties) == 12
    assert {prop["province_city"] for prop in properties} == {"TP. Hồ Chí Minh"}
    assert {prop["district"] for prop in properties} == {"Quận 7"}
