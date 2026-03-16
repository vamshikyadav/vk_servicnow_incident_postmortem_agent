import requests
from app.config import settings


class ConfluenceClient:
    def __init__(self) -> None:
        self.base_url = settings.confluence_base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (settings.confluence_username, settings.confluence_api_token)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def create_page(self, space_key: str, title: str, body_html: str) -> dict:
        url = f"{self.base_url}/wiki/rest/api/content"
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": body_html,
                    "representation": "storage",
                }
            },
        }
        response = self.session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()