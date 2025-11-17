from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSchema:
    name: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


TOOL_REGISTRY: dict[str, ToolSchema] = {
    "replace_text": ToolSchema(
        name="replace_text",
        input_schema={
            "document_id": "string",
            "old_text": "string",
            "new_text": "string",
            "scope": "page|all",
            "page_number": "number?",
        },
        output_schema={
            "success": "boolean",
            "pages_modified": "number[]",
            "version_id": "string",
            "message": "string?",
        },
    )
}


def list_tools() -> list[str]:
    return sorted(TOOL_REGISTRY.keys())


def get_tool_schema(tool_name: str) -> ToolSchema | None:
    return TOOL_REGISTRY.get(tool_name)
