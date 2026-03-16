from app.clients.vertex_client import VertexClient


class WriterService:
    def __init__(self) -> None:
        self.client = VertexClient()

    def write_postmortem(self, incident: dict, timeline_markdown: str) -> dict:
        return self.client.generate_postmortem_sections(incident, timeline_markdown)