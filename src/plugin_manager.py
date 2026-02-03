from typing import List
from .interfaces import IPlugin
from .plugins.x_com import XComPlugin

class PluginManager:
    """
    Registry for all available plugins.
    """
    def __init__(self):
        # Register plugins manually for now.
        # Future: Use importlib to scan plugins directory.
        self.plugins: List[IPlugin] = [
            XComPlugin()
        ]

    def get_plugin(self, url: str) -> IPlugin:
        """Finds the first plugin that can handle the URL."""
        for plugin in self.plugins:
            if plugin.can_handle(url):
                return plugin
        raise ValueError(f"No plugin found capable of handling URL: {url}")
