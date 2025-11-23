from app.orchestration.providers.groq_client import GroqClient


class ToolPlanner:
    def __init__(self) -> None:
        self.client = GroqClient()

    def create_plan(self, command: str) -> dict:
        plan = self.client.plan(command)
        if plan.get("plan"):
            return plan

        command_lower = command.lower()
        if "extract" in command_lower and "text" in command_lower:
            return {
                "status": "fallback",
                "plan": [
                    {
                        "tool": "extract_text",
                        "args": {"scope": "all"},
                    }
                ],
            }

        return {
            "status": "fallback",
            "plan": [
                {
                    "tool": "replace_text",
                    "args": {
                        "old_text": "from",
                        "new_text": "to",
                        "scope": "all",
                    },
                }
            ],
        }
