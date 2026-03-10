import pytest
import os
import yaml
from src.config import ConfigLoader, Config

def test_config_loader_singleton():
    """Test that ConfigLoader is a singleton."""
    loader1 = ConfigLoader()
    loader2 = ConfigLoader()
    assert loader1 is loader2

def test_config_loader_get_defaults():
    """Test that ConfigLoader can access internal defaults."""
    loader = ConfigLoader()
    # config.yaml overrides defaults, so we check what's actually there
    # or we can check keys that are not overridden if any.
    # In this project, we'll check that we get SOME value, 
    # and verify the logic of 'get'
    assert loader.get("app.timeout") is not None
    assert isinstance(loader.get("app.timeout"), int)

def test_config_loader_get_with_default():
    """Test that get returns the default value if key is missing."""
    loader = ConfigLoader()
    assert loader.get("nonexistent.key", "default_val") == "default_val"

def test_config_loader_merge(tmp_path):
    """Test that _merge correctly updates base config."""
    loader = ConfigLoader()
    base = {"a": 1, "b": {"c": 2}}
    update = {"b": {"c": 3, "d": 4}, "e": 5}
    loader._merge(base, update)
    assert base == {"a": 1, "b": {"c": 3, "d": 4}, "e": 5}

def test_static_config_api():
    """Test that the static Config class correctly maps to ConfigLoader values."""
    assert Config.DEFAULT_TIMEOUT == ConfigLoader().get("app.timeout")
    assert Config.Selectors.ARTICLE == ConfigLoader().get("selectors.x_com.article")
