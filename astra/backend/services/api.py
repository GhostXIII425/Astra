import os
import logging
from typing import List, Optional, Tuple, Dict, Any
from astra.backend.storage.database import DatabaseManager
from astra.backend.auth.manager import AuthManager
from astra.backend.parsing.parsers import TransactionParser
from astra.backend.ml.engine import MLEngine
from astra.backend.storage.models import Transaction, Account, User

logger = logging.getLogger(__name__)

class AstraAPI:
    """The main interface for the Astra application, coordinating services."""
    def __init__(self, data_dir: str = "data"):
        """Initialize the API with a data directory."""
        self.db_manager = DatabaseManager(data_dir)
        self.auth_manager = AuthManager(self.db_manager)
        self.parser = TransactionParser()
        self.ml_engines = {} # user_id -> MLEngine

    # Auth
    def register(self, username, password) -> bool:
        """Register a new user."""
        return self.auth_manager.register(username, password)

    def login(self, username, password) -> bool:
        success = self.auth_manager.login(username, password)
        if success:
            user_id = self.auth_manager.current_user.id
            self.ml_engines[user_id] = MLEngine()
            # Initial train
            txs = self.db_manager.get_transactions(user_id)
            self.ml_engines[user_id].train(txs)
        return success

    def logout(self):
        self.auth_manager.logout()

    def get_current_user(self) -> Optional[User]:
        return self.auth_manager.current_user

    # Transactions
    def get_transactions(self) -> List[Transaction]:
        if not self.auth_manager.is_authenticated():
            return []
        user_id = self.auth_manager.current_user.id
        return self.db_manager.get_transactions(user_id)

    def get_import_preview(self, filepath: str) -> Dict[str, Any]:
        return self.parser.preview_file(filepath)

    def import_transactions(self, filepath: str, mapping: Dict[str, str] = None, date_format: str = None, account_id: int = None):
        if not self.auth_manager.is_authenticated():
            return

        user_id = self.auth_manager.current_user.id
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
                pred, conf = self.ml_engines[user_id].predict(tx.description)
                tx.category = pred
                tx.confidence = conf
            else:
                tx.confidence = 1.0 # Trust the mapping

            self.db_manager.add_transaction(user_id, tx)

    def confirm_transaction(self, transaction_id: int, category: str):
        if not self.auth_manager.is_authenticated():
            return

        user_id = self.auth_manager.current_user.id
        txs = self.get_transactions()
        tx = next((t for t in txs if t.id == transaction_id), None)
        if tx:
            tx.category = category
            tx.is_confirmed = True
            tx.confidence = 1.0
            self.db_manager.update_transaction(user_id, tx)
            # Update ML model
            self.ml_engines[user_id].update(tx)

    # Accounts
    def get_accounts(self) -> List[Account]:
        if not self.auth_manager.is_authenticated():
            return []
        user_id = self.auth_manager.current_user.id
        return self.db_manager.get_accounts(user_id)

    def create_account(self, name: str, account_number: str = "", institution: str = "", balance: float = 0.0) -> int:
        if not self.auth_manager.is_authenticated():
            return -1
        user_id = self.auth_manager.current_user.id
        acc = Account(name=name, account_number=account_number, institution=institution, balance=balance)
        return self.db_manager.add_account(user_id, acc)

    # Dashboard data
    def get_summary(self):
        """Get a summary of spending and income."""
        if not self.auth_manager.is_authenticated():
            return {}

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
        if not self.auth_manager.is_authenticated():
            return {}

        txs = self.get_transactions()
        categories = {}
        for t in txs:
            # We aggregate absolute values for the chart
            categories[t.category] = categories.get(t.category, 0) + abs(t.amount)
        return categories
