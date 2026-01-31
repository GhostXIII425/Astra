import pytest
import os
import pandas as pd
from astra.backend.parsing.parsers import TransactionParser

@pytest.fixture
def parser():
    return TransactionParser()

def test_csv_parsing(parser, tmp_path):
    csv_file = tmp_path / "test.csv"
    df = pd.DataFrame({
        "Date": ["2023-01-01", "2023-01-02"],
        "Description": ["Grocery Store", "Gas Station"],
        "Amount": [-50.0, -40.0]
    })
    df.to_csv(csv_file, index=False)

    txs = parser.parse_csv(str(csv_file))
    assert len(txs) == 2
    assert txs[0].description == "Grocery Store"
    assert txs[0].amount == -50.0
    assert txs[1].description == "Gas Station"
    assert txs[1].amount == -40.0

def test_text_parsing(parser, tmp_path):
    txt_file = tmp_path / "test.txt"
    with open(txt_file, "w") as f:
        f.write("2023-01-01 Grocery -50.0\n")
        f.write("2023-01-02 Gas -40.0\n")

    txs = parser.parse_text(str(txt_file))
    assert len(txs) == 2
    assert txs[0].amount == -50.0
    assert "Grocery" in txs[0].description
