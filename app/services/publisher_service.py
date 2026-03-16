from app.clients.confluence_client import ConfluenceClient
from app.config import settings


class PublisherService:
    def __init__(self) -> None:
        self.client = ConfluenceClient()

    def publish_postmortem(self, title: str, body_html: str) -> dict:
        return self.client.create_page(
            space_key=settings.confluence_space_key,
            title=title,
            body_html=body_html,
        )