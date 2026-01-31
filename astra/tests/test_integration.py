import pytest
import shutil
import os
from astra.backend.services.api import AstraAPI

@pytest.fixture
def api():
    test_dir = "test_data_integration"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    api = AstraAPI(test_dir)
    yield api
    shutil.rmtree(test_dir)

def test_full_workflow(api):
    # 1. Register and Login
    assert api.register("alice", "password") is True
    assert api.login("alice", "password") is True

    # 2. Import some transactions
    # Create a small CSV file for testing
    csv_path = "test_import.csv"
    with open(csv_path, "w") as f:
        f.write("Date,Description,Amount\n")
        f.write("2023-01-01,Starbucks,-5.50\n")
        f.write("2023-01-02,Starbucks,-6.00\n")
        f.write("2023-01-03,Starbucks,-5.75\n")
        f.write("2023-01-04,Starbucks,-5.50\n") # 4 starbucks

    api.import_transactions(csv_path)
    txs = api.get_transactions()
    assert len(txs) == 4

    # 3. Confirm some transactions to train ML
    # Categories need 3 confirmed to start predicting
    for i in range(3):
        api.confirm_transaction(txs[i].id, "Coffee")

    # 4. Import another transaction and see if it predicts "Coffee"
    with open("test_import_2.csv", "w") as f:
        f.write("Date,Description,Amount\n")
        f.write("2023-01-05,Starbucks,-5.50\n")

    api.import_transactions("test_import_2.csv")
    new_txs = api.get_transactions()
    # Most recent should be at the top if get_transactions uses ORDER BY date DESC
    latest_tx = next(t for t in new_txs if t.description == "Starbucks" and not t.is_confirmed)
    assert latest_tx.category == "Coffee"

    # 5. Check summary
    summary = api.get_summary()
    assert "Coffee" in summary["categories"]
    assert summary["total_spent"] < 0

    # Cleanup temp files
    os.remove(csv_path)
    os.remove("test_import_2.csv")
