from app.orchestration.nodes.execute_tools import execute_tools
from app.orchestration.nodes.finalize_draft import finalize_draft
from app.orchestration.nodes.parse_command import parse_command
from app.orchestration.nodes.validate_plan import validate_plan


class CommandGraph:
    def run(self, document_id: str, command: str) -> dict:
        state = {
            "document_id": document_id,
            "command": command,
            "plan": [],
            "status": "pending",
        }
        state = parse_command(state)
        state = validate_plan(state)
        state = execute_tools(state)
        state = finalize_draft(state)
        return state
