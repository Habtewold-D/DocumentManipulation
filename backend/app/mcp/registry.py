from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSchema:
    name: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


TOOL_REGISTRY: dict[str, ToolSchema] = {
    "remove_text": ToolSchema(
        name="remove_text",
        input_schema={
            "document_id": "string",
            "old_text": "string",
            "scope": "page|all",
            "page_number": "number?",
        },
        output_schema={
            "success": "boolean",
            "pages_modified": "number[]",
            "version_id": "string",
            "message": "string?",
        },
    ),
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
    ),
    "add_text": ToolSchema(
        name="add_text",
        input_schema={
            "document_id": "string",
            "text": "string",
            "page_number": "number",
            "x": "number",
            "y": "number",
        },
        output_schema={"success": "boolean", "version_id": "string", "message": "string?"},
    ),
    "search_replace": ToolSchema(
        name="search_replace",
        input_schema={
            "document_id": "string",
            "search": "string",
            "replace": "string",
            "match_case": "boolean?",
        },
        output_schema={"success": "boolean", "replacements": "number", "version_id": "string"},
    ),
    "change_font_size": ToolSchema(
        name="change_font_size",
        input_schema={
            "document_id": "string",
            "target_text": "string",
            "font_size": "number?",
            "reference_text": "string?",
        },
        output_schema={"success": "boolean", "version_id": "string"},
    ),
    "change_font_color": ToolSchema(
        name="change_font_color",
        input_schema={"document_id": "string", "target_text": "string", "color": "string"},
        output_schema={"success": "boolean", "version_id": "string"},
    ),
    "set_text_style": ToolSchema(
        name="set_text_style",
        input_schema={"document_id": "string", "target_text": "string", "style": "bold|italic"},
        output_schema={"success": "boolean", "version_id": "string"},
    ),
    "convert_case": ToolSchema(
        name="convert_case",
        input_schema={"document_id": "string", "target_text": "string", "case": "upper|lower|capitalize"},
        output_schema={"success": "boolean", "version_id": "string"},
    ),
    "highlight_text": ToolSchema(
        name="highlight_text",
        input_schema={"document_id": "string", "target_text": "string", "color": "string?"},
        output_schema={"success": "boolean", "version_id": "string"},
    ),
    "underline_text": ToolSchema(
        name="underline_text",
        input_schema={"document_id": "string", "target_text": "string"},
        output_schema={"success": "boolean", "version_id": "string"},
    ),
    "strikethrough_text": ToolSchema(
        name="strikethrough_text",
        input_schema={"document_id": "string", "target_text": "string"},
        output_schema={"success": "boolean", "version_id": "string"},
    ),
    "extract_text": ToolSchema(
        name="extract_text",
        input_schema={"document_id": "string", "scope": "page|all", "page_number": "number?"},
        output_schema={"success": "boolean", "text": "string", "version_id": "string?"},
    ),
}


def list_tools() -> list[str]:
    return sorted(TOOL_REGISTRY.keys())


def get_tool_schema(tool_name: str) -> ToolSchema | None:
    return TOOL_REGISTRY.get(tool_name)
