class XDownloaderError(Exception):
    """Base exception for XDownloader."""
    pass

class NavigationTimeoutError(XDownloaderError):
    """Raised when navigation to a URL times out."""
    pass

class ContentDeletedError(XDownloaderError):
    """Raised when the content is no longer available (e.g., deleted tweet)."""
    pass

class PlatformBlockedError(XDownloaderError):
    """Raised when the platform blocks the request (e.g., CAPTCHA, rate limit)."""
    pass

class ExtractionError(XDownloaderError):
    """Raised when article extraction fails (no content found)."""
    pass

class PluginNotFoundError(XDownloaderError):
    """Raised when no suitable plugin is found for a URL."""
    pass
