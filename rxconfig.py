import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="spendlens",
    api_url="http://localhost:8001",
    disable_plugins=[SitemapPlugin],
)
