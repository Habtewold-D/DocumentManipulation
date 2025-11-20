from app.orchestration.providers.groq_client import GroqClient


class ToolPlanner:
    def __init__(self) -> None:
        self.client = GroqClient()

    def create_plan(self, command: str) -> dict:
        return self.client.plan(command)
