from datetime import UTC, datetime
from uuid import uuid4

from app.orchestration.schemas import CommandResponse


class OrchestrationService:
    def run_command(self, document_id: str, command: str) -> CommandResponse:
        _ = document_id
        _ = command
        return CommandResponse(
            run_id=str(uuid4()),
            status="draft_ready",
            draft_version_id=str(uuid4()),
            created_at=datetime.now(UTC),
        )
