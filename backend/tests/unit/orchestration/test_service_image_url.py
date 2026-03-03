from types import MethodType, SimpleNamespace

from app.orchestration.service import OrchestrationService


def test_execute_with_mode_passes_run_to_v1_path() -> None:
    service = OrchestrationService.__new__(OrchestrationService)

    run = SimpleNamespace(id="run-1", document_id="doc-1", command_text="insert this image")

    captured: dict[str, object] = {}

    def fake_resolve_execution_mode(self: OrchestrationService, current_run: object) -> str:
        assert current_run is run
        return "v1"

    def fake_execute_v1(self: OrchestrationService, document_id: str, command: str, current_run: object | None = None):
        captured["document_id"] = document_id
        captured["command"] = command
        captured["run"] = current_run
        return {"status": "completed", "draft_version_id": "draft-1", "error": None, "details": {}}

    service._resolve_execution_mode = MethodType(fake_resolve_execution_mode, service)
    service._execute_v1 = MethodType(fake_execute_v1, service)

    result = OrchestrationService._execute_with_mode(service, run)

    assert result["status"] == "completed"
    assert captured["document_id"] == "doc-1"
    assert captured["command"] == "insert this image"
    assert captured["run"] is run
