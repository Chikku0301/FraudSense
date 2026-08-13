import pytest

# Import authentication utilities used by the application.
# get_password_hash() -> securely hashes a plain-text password.
# verify_password()  -> checks whether a password matches its hash.
# create_access_token() -> generates a JWT access token.
from backend.app.auth.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
)

# Import the fraud risk thresholds used by the application.
# THRESHOLD_CLEAR -> scores below this value are considered low risk.
# THRESHOLD_BLOCK -> scores above this value are considered high risk.
from backend.app.config import THRESHOLD_CLEAR, THRESHOLD_BLOCK


def test_password_hashing():
    """
    Test the application's password hashing functionality.

    This verifies three important things:
    1. The password is actually hashed and is not stored as plain text.
    2. The original password can be successfully verified against the hash.
    3. An incorrect password is rejected.
    """

    # Plain-text password that we want to hash.
    password = "supersecurepassword123"

    # Generate a secure hash from the password.
    hashed = get_password_hash(password)

    # The generated hash must not be identical to the original password.
    # This ensures that passwords are not stored as plain text.
    assert hashed != password

    # The original password should successfully match the generated hash.
    assert verify_password(password, hashed) is True

    # A different password should not match the stored hash.
    assert verify_password("wrongpassword", hashed) is False


def test_access_token_creation():
    """
    Test JWT access-token creation.

    The token should be generated successfully from the supplied
    user information and should be returned as a non-empty string.
    """

    # Example user information that will be encoded into the token.
    data = {
        "email": "test@fraudsense.com",
        "role": "analyst",
        "user_id": 99,
    }

    # Create an access token containing the user's information.
    token = create_access_token(data)

    # Verify that the returned token is a string.
    assert isinstance(token, str)

    # A valid JWT should contain a reasonable amount of encoded data.
    # This also prevents accidentally returning an empty/very short value.
    assert len(token) > 20


def test_config_thresholds():
    """
    Test the fraud-risk classification thresholds.

    These values control how the application interprets a model's
    risk score, so they should remain consistent with the configuration.
    """

    # Transactions below 0.3 should fall within the clear/low-risk range.
    assert THRESHOLD_CLEAR == 0.3

    # Transactions at or above 0.7 should fall within the block/high-risk range.
    assert THRESHOLD_BLOCK == 0.7