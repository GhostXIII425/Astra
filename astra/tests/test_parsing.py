import pytest
import os
import pandas as pd
from datetime import datetime
from astra.backend.parsing.parsers import TransactionParser

@pytest.fixture
def parser():
    return TransactionParser()

def test_csv_parsing_default(parser, tmp_path):
    csv_file = tmp_path / "test_default.csv"
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

def test_csv_parsing_with_mapping(parser, tmp_path):
    csv_file = tmp_path / "test_mapping.csv"
    df = pd.DataFrame({
        "TX_DATE": ["01/01/2023", "02/01/2023"],
        "PAYEE": ["Starbucks", "Walmart"],
        "VALUE": [-5.50, -100.0],
        "TYPE": ["Food", "Groceries"]
    })
    df.to_csv(csv_file, index=False)

    mapping = {
        "date": "TX_DATE",
        "description": "PAYEE",
        "amount": "VALUE",
        "category": "TYPE"
    }
    date_format = "%m/%d/%Y"

    txs = parser.parse_csv(str(csv_file), mapping=mapping, date_format=date_format)
    assert len(txs) == 2
    assert txs[0].description == "Starbucks"
    assert txs[0].amount == -5.50
    assert txs[0].category == "Food"
    assert txs[0].date.year == 2023
    assert txs[0].date.month == 1
    assert txs[0].date.day == 1

def test_preview_file(parser, tmp_path):
    csv_file = tmp_path / "test_preview.csv"
    df = pd.DataFrame({
        "Col1": [1, 2, 3],
        "Col2": ["A", "B", "C"]
    })
    df.to_csv(csv_file, index=False)

    preview = parser.preview_file(str(csv_file), nrows=2)
    assert preview["columns"] == ["Col1", "Col2"]
    assert len(preview["rows"]) == 2
    assert preview["rows"][0]["Col1"] == 1
    assert preview["rows"][1]["Col2"] == "B"

def test_text_parsing(parser, tmp_path):
    txt_file = tmp_path / "test.txt"
    with open(txt_file, "w") as f:
        f.write("2023-01-01 Grocery -50.0\n")
        f.write("2023-01-02 Gas -40.0\n")

    txs = parser.parse_text(str(txt_file))
    assert len(txs) == 2
    assert txs[0].amount == -50.0
    assert "Grocery" in txs[0].description
