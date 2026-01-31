from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class User:
    id: str
    username: str
    password_hash: str
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Transaction:
    id: Optional[int] = None
    date: datetime = field(default_factory=datetime.now)
    amount: float = 0.0
    description: str = ""
    category: str = "Uncategorized"
    raw_data: str = ""
    account_id: Optional[int] = None
    confidence: float = 0.0
    is_confirmed: bool = False

@dataclass
class Account:
    id: Optional[int] = None
    name: str = ""
    account_number: str = ""
    institution: str = ""
    balance: float = 0.0
