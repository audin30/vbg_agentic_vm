import pytest
from auth import authenticate_user

def test_authenticate_user_invalid_creds():
    # Mocking would be needed for real LDAP, testing failure for now
    assert authenticate_user("fake_user", "wrong_password") is None
