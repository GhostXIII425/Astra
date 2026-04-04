import os
import logging
from typing import List, Optional, Tuple, Dict, Any
from astra.backend.storage.database import DatabaseManager
from astra.backend.parsing.parsers import TransactionParser
from astra.backend.parsing.intelligence import IntelligenceSystem
from astra.backend.storage.models import Transaction, Account, CategoryRule

logger = logging.getLogger(__name__)

class AstraAPI:
    """The main interface for the Astra application, coordinating services."""
    def __init__(self, data_dir: str = "data"):
        """Initialize the API with a data directory."""
        self.db_manager = DatabaseManager(data_dir)
        self.parser = TransactionParser()
        self.intelligence = IntelligenceSystem(self.db_manager)

    # Security
    def unlock(self, password: str) -> bool:
        """Unlock the database with a vault key."""
        try:
            self.db_manager.set_encryption(password)
            return True
        except Exception as e:
            logger.error(f"Failed to unlock: {e}")
            return False

    def is_unlocked(self) -> bool:
        return self.db_manager.is_unlocked()

    # Accounts
    def add_account(self, acc: Account) -> int:
        return self.db_manager.add_account(acc)

    # Accounts
    def add_account(self, acc: Account) -> int:
        return self.db_manager.add_account(acc)

    def get_accounts(self) -> List[Account]:
        return self.db_manager.get_accounts()

    # Transactions
    def get_transactions(self) -> List[Transaction]:
        return self.db_manager.get_transactions()

    def add_manual_transaction(self, tx: Transaction):
        """Add a transaction, automatically predicting its category."""
        if tx.category == "Uncategorized":
            tx.category = self.intelligence.predict_category(tx)
        self.db_manager.add_transaction(tx)

    def confirm_transaction(self, transaction_id: int, category: str):
        txs = self.get_transactions()
        tx = next((t for t in txs if t.id == transaction_id), None)
        if tx:
            tx.category = category
            tx.is_confirmed = True
            # Create a rule if it doesn't exist to "learn" from correction
            self.db_manager.add_rule(CategoryRule(keyword=tx.description, category=category))
            self.db_manager.update_transaction(tx)
            self.intelligence.refresh_rules()

    # Import
    def get_import_preview(self, filepath: str) -> Dict[str, Any]:
        return self.parser.preview_file(filepath)

    def import_transactions(self, filepath: str, mapping: Dict[str, str] = None, date_format: str = None, account_id: int = None):
        ext = os.path.splitext(filepath)[1].lower()

        if ext == '.csv':
            txs = self.parser.parse_csv(filepath, mapping, date_format)
        elif ext in ['.xls', '.xlsx']:
            txs = self.parser.parse_excel(filepath, mapping, date_format)
        else:
            txs = self.parser.parse_text(filepath)

        for tx in txs:
            if account_id:
                tx.account_id = account_id

            # Predict category if not already set by mapping or if it was "Uncategorized"
            if tx.category == "Uncategorized":
                tx.category = self.intelligence.predict_category(tx)
                tx.confidence = 0.8
            else:
                tx.confidence = 1.0

            self.db_manager.add_transaction(tx)

    def add_manual_transaction(self, tx: Transaction):
        """Add a transaction, automatically predicting its category."""
        if tx.category == "Uncategorized":
            tx.category = self.intelligence.predict_category(tx)
        self.db_manager.add_transaction(tx)

    def confirm_transaction(self, transaction_id: int, category: str):
        txs = self.get_transactions()
        tx = next((t for t in txs if t.id == transaction_id), None)
        if tx:
            tx.category = category
            tx.is_confirmed = True
            # Create a rule if it doesn't exist to "learn" from correction
            # This satisfies "User corrections improve future categorization locally"
            self.db_manager.add_rule(CategoryRule(keyword=tx.description, category=category))
            self.db_manager.update_transaction(tx)
            self.intelligence.refresh_rules()

    # Dashboard data
    def get_summary(self):
        """Get a summary of spending and income."""
        txs = self.get_transactions()
        total_spent = sum(t.amount for t in txs if t.amount < 0)
        total_income = sum(t.amount for t in txs if t.amount > 0)

        return {
            "total_spent": total_spent,
            "total_income": total_income,
            "categories": self.get_category_spending()
        }

    def get_category_spending(self) -> dict:
        """Aggregate total spending (absolute value) per category."""
        txs = self.get_transactions()
        categories = {}
        for t in txs:
            if t.amount < 0:
                categories[t.category] = categories.get(t.category, 0) + abs(t.amount)
        return categories
