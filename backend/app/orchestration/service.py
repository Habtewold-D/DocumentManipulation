from datetime import UTC, datetime
import json

from app.db.models.command_run import CommandRun
from app.db.models.document_version import DocumentVersion
from app.db.models.tool_execution_log import ToolExecutionLog
from app.domain.documents.repository import DocumentRepository
from app.domain.logs.repository import ToolLogRepository
from app.domain.versions.repository import VersionRepository
from app.orchestration.graph import CommandGraph
from app.orchestration.planners.tool_planner import ToolPlanner
from app.orchestration.repository import CommandRunRepository
from app.orchestration.schemas import CommandResponse


class OrchestrationService:
    def __init__(self, repository: CommandRunRepository, planner: ToolPlanner | None = None) -> None:
        self.repository = repository
        self.planner = planner or ToolPlanner()
        self.graph = CommandGraph()

    def run_command(self, document_id: str, command: str, idempotency_key: str | None = None) -> CommandResponse:
        db = self.repository.db

        if idempotency_key:
            existing = self.repository.get_by_idempotency_key(document_id, idempotency_key)
            if existing:
                return CommandResponse(
                    run_id=existing.id,
                    status=existing.status,
                    draft_version_id=existing.draft_version_id or "",
                    created_at=existing.created_at,
                    error=None,
                )

        document_repository = DocumentRepository(db)
        version_repository = VersionRepository(db)
        tool_log_repository = ToolLogRepository(db)

        document = document_repository.get(document_id)
        if not document:
            raise ValueError("Document not found")

        source_asset_id = document.original_asset_id
        if document.current_version_id:
            current_version = version_repository.get_for_document(document_id, document.current_version_id)
            if current_version and current_version.pdf_asset_id:
                source_asset_id = current_version.pdf_asset_id

        state = self.graph.run(document_id, command, source_asset_id=source_asset_id)
        plan = state.get("plan", [])
        executed_tools = state.get("executed_tools", [])
        status = state.get("status", "draft_ready")

        if status == "failed":
            details = {
                "plan": plan,
                "executed_tools": executed_tools,
                "error": state.get("error"),
            }
            run = CommandRun(
                document_id=document_id,
                command_text=command,
                idempotency_key=idempotency_key,
                planned_tools=json.dumps(details),
                draft_version_id=None,
                status=status,
            )
            saved_run = self.repository.save(run)
            db.commit()
            return CommandResponse(
                run_id=saved_run.id,
                status=status,
                draft_version_id="",
                created_at=datetime.now(UTC),
                error=state.get("error"),
            )
        result_asset_id = state.get("result_asset_id") or source_asset_id
        latest_output = executed_tools[-1].get("output", {}) if executed_tools else {}
        preview_manifest = latest_output.get("preview_manifest") if isinstance(latest_output, dict) else None

        draft_version = DocumentVersion(
            document_id=document_id,
            parent_version_id=document.current_version_id,
            state="draft",
            version_number=version_repository.next_version_number(document_id),
            pdf_asset_id=result_asset_id,
            preview_manifest=json.dumps(preview_manifest) if preview_manifest else None,
            operation_log=json.dumps({"plan": plan, "executed_tools": executed_tools}),
        )
        saved_version = version_repository.save(draft_version)

        for index, step in enumerate(plan):
            tool_name = step.get("tool", "unknown") if isinstance(step, dict) else "unknown"
            args = step.get("args", {}) if isinstance(step, dict) else {}
            output = executed_tools[index] if index < len(executed_tools) else {"status": "unknown"}

            log = ToolExecutionLog(
                document_id=document_id,
                version_id=saved_version.id,
                tool_name=tool_name,
                status=(output.get("status") or "unknown") if isinstance(output, dict) else "unknown",
                input_payload=json.dumps(args),
                output_payload=json.dumps(output if isinstance(output, dict) else {}),
                error_message=None,
            )
            tool_log_repository.save(log)

        details = {
            "plan": plan,
            "executed_tools": executed_tools,
            "error": state.get("error"),
        }

        run = CommandRun(
            document_id=document_id,
            command_text=command,
            idempotency_key=idempotency_key,
            planned_tools=json.dumps(details),
            draft_version_id=saved_version.id,
            status=status,
        )
        saved_run = self.repository.save(run)
        db.commit()

        return CommandResponse(
            run_id=saved_run.id,
            status=status,
            draft_version_id=saved_version.id,
            created_at=datetime.now(UTC),
            error=None,
        )
