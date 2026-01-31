import pytest
import shutil
import os
from astra.backend.storage.database import DatabaseManager
from astra.backend.auth.manager import AuthManager

@pytest.fixture
def temp_db():
    test_dir = "test_data_auth"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    db = DatabaseManager(test_dir)
    yield db
    shutil.rmtree(test_dir)

def test_registration_and_login(temp_db):
    auth = AuthManager(temp_db)

    # Test successful registration
    assert auth.register("testuser", "password123") is True

    # Test duplicate registration
    assert auth.register("testuser", "password456") is False

    # Test successful login
    assert auth.login("testuser", "password123") is True
    assert auth.current_user.username == "testuser"
    assert auth.is_authenticated() is True

    # Test failed login
    auth.logout()
    assert auth.login("testuser", "wrongpassword") is False
    assert auth.is_authenticated() is False
