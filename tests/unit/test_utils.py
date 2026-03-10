import pytest
from src.utils import is_safe_url

def test_is_safe_url_public():
    # 8.8.8.8 is a public DNS IP
    assert is_safe_url("https://8.8.8.8") is True
    assert is_safe_url("https://www.google.com") is True

def test_is_safe_url_private():
    assert is_safe_url("http://192.168.1.1") is False
    assert is_safe_url("http://10.0.0.1") is False
    assert is_safe_url("http://172.16.0.1") is False

def test_is_safe_url_loopback():
    assert is_safe_url("http://127.0.0.1") is False
    assert is_safe_url("http://localhost") is False

def test_is_safe_url_invalid_scheme():
    assert is_safe_url("ftp://8.8.8.8") is False
    assert is_safe_url("javascript:alert(1)") is False

def test_is_safe_url_no_hostname():
    assert is_safe_url("https://") is False
