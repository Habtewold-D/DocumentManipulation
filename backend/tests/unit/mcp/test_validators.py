import pytest

from app.mcp.validators import MCPValidationError, validate_tool_plan


def test_validate_tool_plan_accepts_valid_replace_text() -> None:
    plan = [
        {
            "tool": "replace_text",
            "args": {
                "document_id": "doc-1",
                "old_text": "CompanyX",
                "new_text": "CompanyY",
                "scope": "all",
            },
        }
    ]

    validate_tool_plan(plan)


def test_validate_tool_plan_rejects_unknown_tool() -> None:
    plan = [{"tool": "unknown_tool", "args": {"document_id": "doc-1"}}]

    with pytest.raises(MCPValidationError):
        validate_tool_plan(plan)
