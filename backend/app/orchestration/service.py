import hashlib
import json

from app.db.models.command_run import CommandRun
from app.db.models.document_version import DocumentVersion
from app.db.models.tool_execution_log import ToolExecutionLog
from app.db.session import SessionLocal
from app.config.settings import settings
from app.domain.documents.repository import DocumentRepository
from app.domain.logs.repository import ToolLogRepository
from app.domain.versions.repository import VersionRepository
from app.domain.versions.service import VersionService
from app.orchestration.graph import CommandGraph
from app.orchestration.planners.tool_planner import ToolPlanner
from app.orchestration.repository import CommandRunRepository
from app.orchestration.schemas import CommandResponse, CommandRunItem
from app.storage.cloudinary_client import CloudinaryClient


class OrchestrationService:
    def __init__(self, repository: CommandRunRepository, planner: ToolPlanner | None = None) -> None:
        self.repository = repository
        self.version_service = VersionService(
            repository=VersionRepository(self.repository.db),
            document_repository=DocumentRepository(self.repository.db),
            cloudinary_client=CloudinaryClient()
        )
        self.planner = planner or ToolPlanner()
        self.graph = CommandGraph()

    @staticmethod
    def _parse_planned_tools(planned_tools: str | None) -> dict:
        if not planned_tools:
            return {}
        try:
            parsed = json.loads(planned_tools)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _to_command_response(self, run: CommandRun) -> CommandResponse:
        details = self._parse_planned_tools(run.planned_tools)
        return CommandResponse(
            run_id=run.id,
            status=run.status,
            draft_version_id=run.draft_version_id or "",
            created_at=run.created_at,
            error=details.get("error") if isinstance(details.get("error"), str) else None,
            execution_mode=details.get("execution_mode") if isinstance(details.get("execution_mode"), str) else None,
        )

    def _to_command_run_item(self, run: CommandRun) -> CommandRunItem:
        details = self._parse_planned_tools(run.planned_tools)
        return CommandRunItem(
            run_id=run.id,
            document_id=run.document_id,
            command_text=run.command_text,
            status=run.status,
            draft_version_id=run.draft_version_id or "",
            created_at=run.created_at,
            error=details.get("error") if isinstance(details.get("error"), str) else None,
            execution_mode=details.get("execution_mode") if isinstance(details.get("execution_mode"), str) else None,
        )

    @staticmethod
    def _normalized_mode() -> str:
        raw_mode = settings.v2_execution_mode.strip().lower()
        if raw_mode not in {"off", "shadow", "canary", "on"}:
            return "off"
        return raw_mode

    @staticmethod
    def _should_use_canary_v2(run_id: str, document_id: str, command_text: str) -> bool:
        canary_percent = max(0, min(settings.v2_canary_percent, 100))
        if canary_percent <= 0:
            return False
        token = f"{run_id}:{document_id}:{command_text}"
        bucket = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16) % 100
        return bucket < canary_percent

    def _resolve_execution_mode(self, run: CommandRun) -> str:
        mode = self._normalized_mode()
        if mode == "canary":
            return "v2" if self._should_use_canary_v2(run.id, run.document_id, run.command_text) else "v1"
        if mode == "on":
            return "v2"
        if mode == "shadow":
            return "shadow"
        return "v1"

    def enqueue_command(self, document_id: str, command: str, image_url: str | None = None, idempotency_key: str | None = None) -> CommandResponse:
        db = self.repository.db

        if idempotency_key:
            existing = self.repository.get_by_idempotency_key(document_id, idempotency_key)
            if existing:
                return self._to_command_response(existing)

        document = DocumentRepository(db).get(document_id)
        if not document:
            raise ValueError("Document not found")

        run = self.repository.create(
            document_id=document_id,
            command_text=command,
            image_url=image_url,
            idempotency_key=idempotency_key,
        )
        run.planned_tools = json.dumps({"execution_mode": self._normalized_mode()})
        run.draft_version_id = None
        run.status = "queued"
        saved_run = self.repository.save(run)
        db.commit()
        return self._to_command_response(saved_run)

    def get_run(self, run_id: str) -> CommandRunItem | None:
        run = self.repository.get(run_id)
        if not run:
            return None
        return self._to_command_run_item(run)

    def list_runs(self, document_id: str, limit: int = 20) -> list[CommandRunItem]:
        runs = self.repository.list_for_document(document_id=document_id, limit=limit)
        return [self._to_command_run_item(run) for run in runs]

    def cancel_run(self, run_id: str) -> CommandRunItem:
        run = self.repository.get(run_id)
        if not run:
            raise ValueError("Run not found")
        if run.status in {"completed", "failed", "canceled"}:
            raise ValueError(f"Run cannot be canceled in state: {run.status}")
        run.status = "canceled"
        self.repository.db.add(run)
        self.repository.db.commit()
        return self._to_command_run_item(run)

    def retry_run(self, run_id: str) -> CommandRunItem:
        run = self.repository.get(run_id)
        if not run:
            raise ValueError("Run not found")
        if run.status not in {"failed", "canceled"}:
            raise ValueError(f"Only failed or canceled runs can be retried. Current state: {run.status}")
        run.status = "queued"
        run.draft_version_id = None
        run.planned_tools = json.dumps({"execution_mode": self._normalized_mode()})
        self.repository.db.add(run)
        self.repository.db.commit()
        return self._to_command_run_item(run)

    def _execute_v1(self, document_id: str, command: str, run: CommandRun | None = None) -> dict[str, object]:
        db = self.repository.db

        document_repository = DocumentRepository(db)
        version_repository = VersionRepository(db)
        tool_log_repository = ToolLogRepository(db)

        document = document_repository.get(document_id)
        if not document:
            raise ValueError("Document not found")

        image_url = run.image_url if run else None

        source_asset_id = document.original_asset_id
        if document.current_version_id:
            current_version = version_repository.get_for_document(document_id, document.current_version_id)
            if current_version and current_version.pdf_asset_id:
                source_asset_id = current_version.pdf_asset_id

        state = self.graph.run(document_id, command, image_url=image_url, source_asset_id=source_asset_id)
        plan = state.get("plan", [])
        executed_tools = state.get("executed_tools", [])
        status = state.get("status", "draft_ready")

        if status == "failed":
            details = {
                "plan": plan,
                "executed_tools": executed_tools,
                "error": state.get("error"),
            }
            return {
                "status": "failed",
                "draft_version_id": "",
                "error": state.get("error"),
                "details": details,
            }

        result_asset_id = state.get("result_asset_id") or source_asset_id
        latest_output = executed_tools[-1].get("output", {}) if executed_tools else {}
        preview_manifest = latest_output.get("preview_manifest") if isinstance(latest_output, dict) else None

        draft_version = DocumentVersion(
            document_id=document_id,
            parent_version_id=document.current_version_id,
            state="draft",
            version_number=version_repository.next_version_number(document_id),
            pdf_asset_id=result_asset_id,
            image_url=image_url,
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

        return {
            "status": "completed",
            "draft_version_id": saved_version.id,
            "error": None,
            "details": details,
        }

    def _execute_with_mode(self, run: CommandRun) -> dict[str, object]:
        execution_mode = self._resolve_execution_mode(run)
        if execution_mode in {"v2", "shadow"}:
            authoritative = self._execute_v1(run.document_id, run.command_text, run)
            details = authoritative.get("details") if isinstance(authoritative.get("details"), dict) else {}
            details = dict(details)
            details["execution_mode"] = execution_mode
            details["shadow"] = {
                "status": "skipped",
                "reason": "v2-path-not-implemented-yet",
            }
            return {
                "status": authoritative.get("status", "failed"),
                "draft_version_id": authoritative.get("draft_version_id", ""),
                "error": authoritative.get("error"),
                "details": details,
            }

        authoritative = self._execute_v1(run.document_id, run.command_text, run)
        details = authoritative.get("details") if isinstance(authoritative.get("details"), dict) else {}
        details = dict(details)
        details["execution_mode"] = execution_mode
        return {
            "status": authoritative.get("status", "failed"),
            "draft_version_id": authoritative.get("draft_version_id", ""),
            "error": authoritative.get("error"),
            "details": details,
        }

    @classmethod
    def process_queued_run(cls, run_id: str) -> None:
        db = SessionLocal()
        try:
            repository = CommandRunRepository(db)
            service = cls(repository)
            run = repository.get(run_id)
            if not run:
                return
            if run.status == "canceled":
                return
            if run.status not in {"queued", "retrying"}:
                return

            run.status = "running"
            repository.db.add(run)
            repository.db.commit()

            outcome = service._execute_with_mode(run)
            latest = repository.get(run_id)
            if latest and latest.status == "canceled":
                return

            run.status = str(outcome.get("status", "failed"))
            run.draft_version_id = str(outcome.get("draft_version_id") or "") or None
            details = outcome.get("details") if isinstance(outcome.get("details"), dict) else {}
            error = outcome.get("error")
            if isinstance(error, str) and error:
                details["error"] = error
            run.planned_tools = json.dumps(details)
            repository.db.add(run)
            repository.db.commit()
        except Exception as error:
            run = CommandRunRepository(db).get(run_id)
            if run:
                run.status = "failed"
                run.planned_tools = json.dumps({"error": str(error), "execution_mode": "v1"})
                db.add(run)
                db.commit()
        finally:
            db.close()
