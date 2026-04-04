from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

class AccountType(Enum):
    CASH = "Cash"
    CHECKING = "Checking"
    CREDIT = "Credit"
    ENVELOPE = "Envelope"
    SAVINGS = "Savings"

@dataclass
class Transaction:
    id: Optional[int] = None
    date: datetime = field(default_factory=datetime.now)
    amount: float = 0.0
    description: str = ""
    category: str = "Uncategorized"
    account_id: Optional[int] = None
    source_account: str = ""
    is_confirmed: bool = False
    is_recurring: bool = False
    raw_data: str = ""
    tags: str = "" # Comma separated tags
    # Keep confidence for ML backward compatibility if needed, though rules use 1.0
    confidence: float = 1.0

@dataclass
class Account:
    id: Optional[int] = None
    name: str = ""
    type: AccountType = AccountType.CHECKING
    account_number: str = ""
    institution: str = ""
    balance: float = 0.0
    is_hidden: bool = False

@dataclass
class CategoryRule:
    id: Optional[int] = None
    keyword: str = ""
    category: str = ""
    priority: int = 0

@dataclass
class Budget:
    id: Optional[int] = None
    category: str = ""
    limit: float = 0.0
    period: str = "monthly" # monthly, biweekly, weekly
    rollover: bool = False
