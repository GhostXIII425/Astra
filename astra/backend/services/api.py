import os
from typing import List, Optional, Tuple
from astra.backend.storage.database import DatabaseManager
from astra.backend.auth.manager import AuthManager
from astra.backend.parsing.parsers import TransactionParser
from astra.backend.ml.engine import MLEngine
from astra.backend.storage.models import Transaction, Account, User

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

    def import_transactions(self, filepath: str):
        if not self.auth_manager.is_authenticated():
            return

        user_id = self.auth_manager.current_user.id
        ext = os.path.splitext(filepath)[1].lower()

        if ext == '.csv':
            txs = self.parser.parse_csv(filepath)
        elif ext in ['.xls', '.xlsx']:
            txs = self.parser.parse_excel(filepath)
        else:
            txs = self.parser.parse_text(filepath)

        for tx in txs:
            # Predict category
            pred, conf = self.ml_engines[user_id].predict(tx.description)
            tx.category = pred
            tx.confidence = conf
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

    # Dashboard data
    def get_summary(self):
        if not self.auth_manager.is_authenticated():
            return {}

        txs = self.get_transactions()
        total_spent = sum(t.amount for t in txs if t.amount < 0)
        total_income = sum(t.amount for t in txs if t.amount > 0)

        # Categorized breakdown
        categories = {}
        for t in txs:
            categories[t.category] = categories.get(t.category, 0) + abs(t.amount)

        return {
            "total_spent": total_spent,
            "total_income": total_income,
            "categories": categories
        }
