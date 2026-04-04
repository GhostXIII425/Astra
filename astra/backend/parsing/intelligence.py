from typing import List, Optional
from astra.backend.storage.models import Transaction, CategoryRule
import re

class RuleEngine:
    def __init__(self, rules: List[CategoryRule]):
        self.rules = sorted(rules, key=lambda x: x.priority, reverse=True)

    def categorize(self, transaction: Transaction) -> str:
        desc = transaction.description.lower()
        for rule in self.rules:
            if rule.keyword.lower() in desc:
                return rule.category
        return "Uncategorized"

class IntelligenceSystem:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.refresh_rules()

    def refresh_rules(self):
        rules = self.db_manager.get_rules()
        self.engine = RuleEngine(rules)

    def predict_category(self, transaction: Transaction) -> str:
        return self.engine.categorize(transaction)

    def detect_recurring(self, transactions: List[Transaction]) -> List[Transaction]:
        # Basic recurrence detection based on exact description and amount
        # In a real app, this would use fuzzy matching and date intervals
        patterns = {}
        for tx in transactions:
            key = (tx.description.lower(), tx.amount)
            if key not in patterns:
                patterns[key] = []
            patterns[key].append(tx)

        recurring = []
        for key, txs in patterns.items():
            if len(txs) >= 2:
                recurring.extend(txs)
        return recurring

    def get_safe_to_spend(self, budget_limit: float, current_spent: float, days_left: int) -> float:
        remaining = budget_limit - current_spent
        if days_left <= 0:
            return max(0, remaining)
        return max(0, remaining / days_left)
