import bcrypt
import uuid
import os
from typing import Optional
from astra.backend.storage.models import User
from astra.backend.storage.database import DatabaseManager

class AuthManager:
    """Handles user authentication and session management."""
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.current_user: Optional[User] = None

    def register(self, username, password) -> bool:
        """Register a new user with hashed password and encryption salt."""
        if self.db_manager.get_user_by_username(username):
            return False

        user_id = str(uuid.uuid4())
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode(), salt).decode()

        # We need a separate salt for data encryption, or use the same one?
        # Encryption salt should probably be random and stored.
        encryption_salt = os.urandom(16)

        user = User(id=user_id, username=username, password_hash=password_hash)
        self.db_manager.create_user(user, encryption_salt)
        return True

    def login(self, username, password) -> bool:
        user_data = self.db_manager.get_user_by_username(username)
        if not user_data:
            return False

        user = user_data["user"]
        encryption_salt = user_data["salt"]

        if bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            self.current_user = user
            # Initialize encryption for this session
            self.db_manager.set_user_encryption(user.id, password, encryption_salt)
            return True
        return False

    def logout(self):
        self.current_user = None

    def is_authenticated(self) -> bool:
        return self.current_user is not None
