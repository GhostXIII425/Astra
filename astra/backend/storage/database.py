import sqlite3
import os
import base64
from typing import List, Optional
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from astra.backend.storage.models import Transaction, Account, AccountType, CategoryRule

class DataEncryption:
    @staticmethod
    def generate_key(password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        if not data:
            return data
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        if not token:
            return token
        return self.fernet.decrypt(token.encode()).decode()

class DatabaseManager:
    """Manages the single local SQLite database."""
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        self.db_path = os.path.join(data_dir, "astra_local.db")
        self.encryption: Optional[DataEncryption] = None
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value BLOB
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    account_number TEXT,
                    institution TEXT,
                    balance REAL DEFAULT 0.0,
                    is_hidden BOOLEAN DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TIMESTAMP NOT NULL,
                    amount TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    account_id INTEGER,
                    source_account TEXT,
                    is_confirmed BOOLEAN DEFAULT 0,
                    is_recurring BOOLEAN DEFAULT 0,
                    raw_data TEXT,
                    tags TEXT,
                    FOREIGN KEY (account_id) REFERENCES accounts (id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS category_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    priority INTEGER DEFAULT 0
                )
            """)

    def set_encryption(self, password: str, salt: bytes = b'astra_static_salt'):
        key = DataEncryption.generate_key(password, salt)
        self.encryption = DataEncryption(key)

    def is_unlocked(self) -> bool:
        return self.encryption is not None

    def _encrypt(self, data: str) -> str:
        if not self.encryption:
            raise ValueError("Database is locked. Please set vault key first.")
        return self.encryption.encrypt(data)

    def _decrypt(self, data: str) -> str:
        if not self.encryption:
            raise ValueError("Database is locked. Please set vault key first.")
        return self.encryption.decrypt(data)

    # Transaction methods
    def add_transaction(self, tx: Transaction) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO transactions (date, amount, description, category, account_id, source_account, is_confirmed, is_recurring, raw_data, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tx.date, self._encrypt(str(tx.amount)), self._encrypt(tx.description), tx.category,
                 tx.account_id, tx.source_account, tx.is_confirmed, tx.is_recurring, self._encrypt(tx.raw_data), tx.tags)
            )
            return cursor.lastrowid

    def get_transactions(self) -> List[Transaction]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM transactions ORDER BY date DESC").fetchall()
            return [Transaction(
                id=row["id"],
                date=datetime.fromisoformat(row["date"]) if isinstance(row["date"], str) else row["date"],
                amount=float(self._decrypt(row["amount"])),
                description=self._decrypt(row["description"]),
                category=row["category"],
                account_id=row["account_id"],
                source_account=row["source_account"],
                is_confirmed=bool(row["is_confirmed"]),
                is_recurring=bool(row["is_recurring"]),
                raw_data=self._decrypt(row["raw_data"]),
                tags=row["tags"]
            ) for row in rows]

    def update_transaction(self, tx: Transaction):
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE transactions SET
                   date = ?, amount = ?, description = ?, category = ?, account_id = ?,
                   source_account = ?, is_confirmed = ?, is_recurring = ?, raw_data = ?, tags = ?
                   WHERE id = ?""",
                (tx.date, self._encrypt(str(tx.amount)), self._encrypt(tx.description), tx.category,
                 tx.account_id, tx.source_account, tx.is_confirmed, tx.is_recurring, self._encrypt(tx.raw_data), tx.tags, tx.id)
            )

    # Account methods
    def add_account(self, acc: Account) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO accounts (name, type, account_number, institution, balance, is_hidden) VALUES (?, ?, ?, ?, ?, ?)",
                (acc.name, acc.type.value, self._encrypt(acc.account_number), acc.institution, acc.balance, acc.is_hidden)
            )
            return cursor.lastrowid

    def get_accounts(self) -> List[Account]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM accounts").fetchall()
            return [Account(
                id=row["id"],
                name=row["name"],
                type=AccountType(row["type"]),
                account_number=self._decrypt(row["account_number"]),
                institution=row["institution"],
                balance=row["balance"],
                is_hidden=bool(row["is_hidden"])
            ) for row in rows]

    # Rule methods
    def add_rule(self, rule: CategoryRule):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO category_rules (keyword, category, priority) VALUES (?, ?, ?)",
                (rule.keyword, rule.category, rule.priority)
            )

    def get_rules(self) -> List[CategoryRule]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM category_rules ORDER BY priority DESC").fetchall()
            return [CategoryRule(id=row["id"], keyword=row["keyword"], category=row["category"], priority=row["priority"]) for row in rows]
