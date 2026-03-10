import pytest
from src.plugin_manager import PluginManager
from src.plugins.x_com import XComPlugin

def test_plugin_manager_registration():
    """Test that PluginManager starts with known plugins."""
    pm = PluginManager()
    assert len(pm.plugins) > 0
    assert any(isinstance(p, XComPlugin) for p in pm.plugins)

def test_plugin_manager_get_plugin_success():
    """Test that PluginManager returns the correct plugin for a URL."""
    pm = PluginManager()
    url = "https://x.com/username/status/123"
    plugin = pm.get_plugin(url)
    assert isinstance(plugin, XComPlugin)

def test_plugin_manager_get_plugin_failure():
    """Test that PluginManager raises ValueError for unsupported URLs."""
    pm = PluginManager()
    unsupported_url = "https://google.com"
    with pytest.raises(ValueError) as exc:
        pm.get_plugin(unsupported_url)
    assert "No plugin found" in str(exc.value)
