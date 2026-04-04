import pytest
import shutil
import os
from astra.backend.services.api import AstraAPI
from astra.backend.storage.models import Transaction, Account, AccountType

@pytest.fixture
def api():
    test_dir = "test_data_integration"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    api = AstraAPI(test_dir)
    api.unlock("test_vault_key")
    yield api
    shutil.rmtree(test_dir)

def test_full_workflow_offline(api):
    # 1. Setup an account
    api.add_account(Account(name="Main Checking", type=AccountType.CHECKING, balance=1000.0))
    accounts = api.get_accounts()
    assert len(accounts) == 1

    # 2. Manual Transaction
    api.add_manual_transaction(Transaction(description="Grocery Store", amount=-50.0))
    txs = api.get_transactions()
    assert len(txs) == 1
    assert txs[0].description == "Grocery Store"

    # 3. Rule-based categorization
    from astra.backend.storage.models import CategoryRule
    api.db_manager.add_rule(CategoryRule(keyword="Starbucks", category="Coffee"))
    api.intelligence.refresh_rules()

    # Import/Add transaction matching rule
    api.add_manual_transaction(Transaction(description="Morning Starbucks", amount=-5.50))
    txs = api.get_transactions()
    latest = next(t for t in txs if "Starbucks" in t.description)
    assert latest.category == "Coffee"

    # 4. Summary
    summary = api.get_summary()
    assert summary["total_spent"] < 0
    assert "Coffee" in summary["categories"]
