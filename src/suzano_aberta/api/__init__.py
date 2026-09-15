from .app import API_VERSION, create_app
from .settings import ApiSettings

app = create_app()

__all__ = ["API_VERSION", "ApiSettings", "app", "create_app"]
