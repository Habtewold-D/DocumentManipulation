from datetime import UTC, datetime
from uuid import uuid4
import json

from app.db.models.command_run import CommandRun
from app.orchestration.graph import CommandGraph
from app.orchestration.planners.tool_planner import ToolPlanner
from app.orchestration.repository import CommandRunRepository
from app.orchestration.schemas import CommandResponse


class OrchestrationService:
    def __init__(self, repository: CommandRunRepository, planner: ToolPlanner | None = None) -> None:
        self.repository = repository
        self.planner = planner or ToolPlanner()
        self.graph = CommandGraph()

    def run_command(self, document_id: str, command: str) -> CommandResponse:
        state = self.graph.run(document_id, command)
        plan = state.get("plan", [])
        draft_version_id = state.get("draft_version_id", str(uuid4()))

        run = CommandRun(
            document_id=document_id,
            command_text=command,
            planned_tools=json.dumps(plan),
            draft_version_id=draft_version_id,
            status=state.get("status", "draft_ready"),
        )
        saved_run = self.repository.save(run)

        return CommandResponse(
            run_id=saved_run.id,
            status=state.get("status", "draft_ready"),
            draft_version_id=draft_version_id,
            created_at=datetime.now(UTC),
        )
