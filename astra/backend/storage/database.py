import sqlite3
import os
import base64
from typing import List, Optional
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from astra.backend.storage.models import User, Transaction, Account

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
    """Manages SQLite connections, schema creation, and user isolation."""
    def __init__(self, data_dir: str = "data"):
        """Initialize the database manager and ensure the data directory exists."""
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        self.system_db_path = os.path.join(data_dir, "system.db")
        self._init_system_db()
        self._encryption_cache = {} # user_id -> DataEncryption

    def set_user_encryption(self, user_id: str, password: str, salt: bytes):
        key = DataEncryption.generate_key(password, salt)
        self._encryption_cache[user_id] = DataEncryption(key)

    def _get_encryption(self, user_id: str) -> DataEncryption:
        if user_id not in self._encryption_cache:
            # In a real app, we might need a way to recover this or prompt user
            raise ValueError(f"Encryption not initialized for user {user_id}")
        return self._encryption_cache[user_id]

    def _get_connection(self, db_path: str):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_system_db(self):
        with self._get_connection(self.system_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def get_user_db_path(self, user_id: str) -> str:
        return os.path.join(self.data_dir, f"user_{user_id}.db")

    def init_user_db(self, user_id: str):
        db_path = self.get_user_db_path(user_id)
        with self._get_connection(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    account_number TEXT,
                    institution TEXT,
                    balance REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TIMESTAMP NOT NULL,
                    amount TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    raw_data TEXT,
                    account_id INTEGER,
                    confidence REAL DEFAULT 0.0,
                    is_confirmed BOOLEAN DEFAULT 0,
                    FOREIGN KEY (account_id) REFERENCES accounts (id)
                )
            """)

    # User methods (System DB)
    def create_user(self, user: User, salt: bytes):
        with self._get_connection(self.system_db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
                (user.id, user.username, user.password_hash, salt, user.created_at)
            )
        self.init_user_db(user.id)

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self._get_connection(self.system_db_path) as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if row:
                user = User(id=row["id"], username=row["username"], password_hash=row["password_hash"],
                            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"])
                return {"user": user, "salt": row["salt"]}
        return None

    # Transaction methods (User DB)
    def add_transaction(self, user_id: str, tx: Transaction) -> int:
        """Add a new transaction to the user's database with encrypted sensitive fields."""
        encryptor = self._get_encryption(user_id)
        description_enc = encryptor.encrypt(tx.description)
        raw_data_enc = encryptor.encrypt(tx.raw_data)
        amount_enc = encryptor.encrypt(str(tx.amount))

        db_path = self.get_user_db_path(user_id)
        with self._get_connection(db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO transactions (date, amount, description, category, raw_data, account_id, confidence, is_confirmed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (tx.date, amount_enc, description_enc, tx.category, raw_data_enc, tx.account_id, tx.confidence, tx.is_confirmed)
            )
            return cursor.lastrowid

    def get_transactions(self, user_id: str) -> List[Transaction]:
        """Retrieve all transactions for a user, decrypting sensitive fields."""
        encryptor = self._get_encryption(user_id)
        db_path = self.get_user_db_path(user_id)
        with self._get_connection(db_path) as conn:
            rows = conn.execute("SELECT * FROM transactions ORDER BY date DESC").fetchall()
            transactions = []
            for row in rows:
                transactions.append(Transaction(
                    id=row["id"],
                    date=datetime.fromisoformat(row["date"]) if isinstance(row["date"], str) else row["date"],
                    amount=float(encryptor.decrypt(row["amount"])),
                    description=encryptor.decrypt(row["description"]),
                    category=row["category"],
                    raw_data=encryptor.decrypt(row["raw_data"]),
                    account_id=row["account_id"],
                    confidence=row["confidence"],
                    is_confirmed=bool(row["is_confirmed"])
                ))
            return transactions

    def update_transaction(self, user_id: str, tx: Transaction):
        """Update an existing transaction in the user's database."""
        encryptor = self._get_encryption(user_id)
        description_enc = encryptor.encrypt(tx.description)
        raw_data_enc = encryptor.encrypt(tx.raw_data)
        amount_enc = encryptor.encrypt(str(tx.amount))

        db_path = self.get_user_db_path(user_id)
        with self._get_connection(db_path) as conn:
            conn.execute(
                """UPDATE transactions SET
                   date = ?, amount = ?, description = ?, category = ?, raw_data = ?,
                   account_id = ?, confidence = ?, is_confirmed = ?
                   WHERE id = ?""",
                (tx.date, amount_enc, description_enc, tx.category, raw_data_enc,
                 tx.account_id, tx.confidence, tx.is_confirmed, tx.id)
            )

    # Account methods (User DB)
    def add_account(self, user_id: str, acc: Account) -> int:
        encryptor = self._get_encryption(user_id)
        acc_num_enc = encryptor.encrypt(acc.account_number)

        db_path = self.get_user_db_path(user_id)
        with self._get_connection(db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO accounts (name, account_number, institution, balance) VALUES (?, ?, ?, ?)",
                (acc.name, acc_num_enc, acc.institution, acc.balance)
            )
            return cursor.lastrowid

    def get_accounts(self, user_id: str) -> List[Account]:
        encryptor = self._get_encryption(user_id)
        db_path = self.get_user_db_path(user_id)
        with self._get_connection(db_path) as conn:
            rows = conn.execute("SELECT * FROM accounts").fetchall()
            accounts = []
            for row in rows:
                accounts.append(Account(
                    id=row["id"],
                    name=row["name"],
                    account_number=encryptor.decrypt(row["account_number"]),
                    institution=row["institution"],
                    balance=row["balance"]
                ))
            return accounts
