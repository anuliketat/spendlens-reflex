import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin
import os

# Detect GitHub Codespaces environment
CODESPACE_NAME = os.getenv("CODESPACE_NAME")
GITHUB_CODESPACES = os.getenv("GITHUB_CODESPACES", "false").lower() == "true"

# Configure backend API URL based on environment
if GITHUB_CODESPACES and CODESPACE_NAME:
    # GitHub Codespaces: use forwarded domain
    API_URL = f"https://{CODESPACE_NAME}-8000.app.github.dev"
    print(f"🔗 GitHub Codespaces detected: Using API URL {API_URL}")
else:
    # Local development: use localhost
    API_URL = "http://localhost:8000"
    print(f"🔗 Local development: Using API URL {API_URL}")

config = rx.Config(
    app_name="spendlens",
    frontend_port=3000,
    backend_port=8000,
    api_url=API_URL,
    disable_plugins=[SitemapPlugin],
)
