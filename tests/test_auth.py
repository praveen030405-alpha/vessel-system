"""
Unit tests for Bearer authentication verification.
"""

import os
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from vessel_system.auth import verify_bearer_token, check_auth_header, is_auth_enabled


def test_auth_with_token(monkeypatch):
    monkeypatch.setenv("VESSEL_MCP_AUTH_TOKEN", "secret-test-token-xyz")
    assert is_auth_enabled() is True

    # Valid token
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret-test-token-xyz")
    assert verify_bearer_token(cred) is True

    # Valid string header
    assert check_auth_header("Bearer secret-test-token-xyz") is True

    # Invalid string header
    assert check_auth_header("Bearer wrong-token") is False

    # Invalid token raises 401
    bad_cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-token")
    with pytest.raises(HTTPException) as exc:
        verify_bearer_token(bad_cred)
    assert exc.value.status_code == 401

    # Missing token raises 401
    with pytest.raises(HTTPException) as exc2:
        verify_bearer_token(None)
    assert exc2.value.status_code == 401


def test_auth_disabled_in_dev(monkeypatch):
    monkeypatch.delenv("VESSEL_MCP_AUTH_TOKEN", raising=False)
    assert is_auth_enabled() is False
    # In dev when no token configured, verification passes
    assert verify_bearer_token(None) is True
    assert check_auth_header("") is True
