import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Tuple, Optional
from astra.backend.storage.models import Transaction

class MLEngine:
    """Machine learning engine for transaction categorization."""
    def __init__(self):
        # include single-character tokens
        self.vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        # k=1 is often better for personal finance with recurring transactions
        self.model = KNeighborsClassifier(n_neighbors=1)
        self.is_trained = False
        self.training_data: List[Transaction] = []

    def train(self, transactions: List[Transaction]):
        """Train the k-NN model on confirmed transactions."""
        confirmed = [tx for tx in transactions if tx.is_confirmed and tx.category != "Uncategorized"]
        if len(confirmed) < 1:
            return

        descriptions = [tx.description for tx in confirmed]
        categories = [tx.category for tx in confirmed]

        X = self.vectorizer.fit_transform(descriptions)
        self.model.fit(X, categories)
        self.is_trained = True
        self.training_data = confirmed

    def predict(self, description: str) -> Tuple[str, float]:
        if not self.is_trained:
            return "Uncategorized", 0.0

        try:
            X = self.vectorizer.transform([description])
            prediction = self.model.predict(X)[0]
            # Get confidence based on distance or voting?
            # KNeighborsClassifier.predict_proba gives confidence
            probs = self.model.predict_proba(X)[0]
            confidence = np.max(probs)
            return prediction, float(confidence)
        except Exception:
            return "Uncategorized", 0.0

    def update(self, transaction: Transaction):
        if transaction.is_confirmed:
            # Simple approach: add to training data and retrain
            self.training_data.append(transaction)
            self.train(self.training_data)
