import pytest
from backend.app.auth.auth import get_password_hash, verify_password, create_access_token
from backend.app.config import THRESHOLD_CLEAR, THRESHOLD_BLOCK

def test_password_hashing():
    password = "supersecurepassword123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_access_token_creation():
    data = {"email": "test@fraudsense.com", "role": "analyst", "user_id": 99}
    token = create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 20

def test_config_thresholds():
    assert THRESHOLD_CLEAR == 0.3
    assert THRESHOLD_BLOCK == 0.7
