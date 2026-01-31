import pytest
from astra.backend.ml.engine import MLEngine
from astra.backend.storage.models import Transaction

@pytest.fixture
def ml_engine():
    return MLEngine()

def test_ml_prediction(ml_engine):
    # Need at least 3 confirmed transactions to train
    txs = [
        Transaction(description="Electronics Apple Store", category="Shopping", is_confirmed=True),
        Transaction(description="Electronics Best Buy", category="Shopping", is_confirmed=True),
        Transaction(description="Electronics Gadgets", category="Shopping", is_confirmed=True),
        Transaction(description="Grocery Whole Foods", category="Groceries", is_confirmed=True),
        Transaction(description="Grocery Trader Joes", category="Groceries", is_confirmed=True),
        Transaction(description="Grocery Safeway", category="Groceries", is_confirmed=True),
    ]

    ml_engine.train(txs)

    # Predict
    pred, conf = ml_engine.predict("Apple Store NYC")
    assert pred == "Shopping"
    assert conf > 0.4

    pred, conf = ml_engine.predict("Grocery Market")
    assert pred == "Groceries"
    assert conf > 0.4

def test_ml_incremental_learning(ml_engine):
    txs = [
        Transaction(description="A", category="X", is_confirmed=True),
        Transaction(description="B", category="X", is_confirmed=True),
        Transaction(description="C", category="X", is_confirmed=True),
    ]
    ml_engine.train(txs)

    # Initially predicts X
    pred, _ = ml_engine.predict("D")
    assert pred == "X"

    # New confirmation for Y
    new_txs = [
        Transaction(description="D", category="Y", is_confirmed=True),
        Transaction(description="E", category="Y", is_confirmed=True),
        Transaction(description="F", category="Y", is_confirmed=True),
        Transaction(description="G", category="Y", is_confirmed=True),
        Transaction(description="H", category="Y", is_confirmed=True),
    ]
    for tx in new_txs:
        ml_engine.update(tx)

    # Now it should lean towards Y for similar inputs
    pred, _ = ml_engine.predict("D")
    assert pred == "Y"
