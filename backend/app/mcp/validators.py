from typing import Any

from app.mcp.registry import get_tool_schema


class MCPValidationError(ValueError):
    pass


def _is_optional(type_spec: str) -> bool:
    return type_spec.endswith("?")


def _base_type(type_spec: str) -> str:
    return type_spec[:-1] if _is_optional(type_spec) else type_spec


def _matches_type(value: Any, type_spec: str) -> bool:
    base = _base_type(type_spec)

    if "|" in base:
        return isinstance(value, str) and value in base.split("|")
    if base == "string":
        return isinstance(value, str)
    if base == "number":
        return isinstance(value, int | float)
    if base == "boolean":
        return isinstance(value, bool)
    if base == "number[]":
        return isinstance(value, list) and all(isinstance(item, int | float) for item in value)
    return True


def validate_tool_step(step: dict[str, Any]) -> None:
    if not isinstance(step, dict):
        raise MCPValidationError("Plan step must be an object")

    tool_name = step.get("tool")
    args = step.get("args", {})

    if not isinstance(tool_name, str) or not tool_name:
        raise MCPValidationError("Each step must include a valid tool name")
    if not isinstance(args, dict):
        raise MCPValidationError("Step args must be an object")

    schema = get_tool_schema(tool_name)
    if not schema:
        raise MCPValidationError(f"Unknown tool: {tool_name}")

    for field, type_spec in schema.input_schema.items():
        optional = _is_optional(type_spec)
        if field not in args:
            if optional:
                continue
            raise MCPValidationError(f"Missing required field '{field}' for tool '{tool_name}'")
        value = args[field]
        if value is None and optional:
            continue
        if not _matches_type(value, type_spec):
            raise MCPValidationError(
                f"Invalid type/value for '{field}' in tool '{tool_name}'. Expected {type_spec}"
            )


def validate_tool_plan(plan: list[dict[str, Any]]) -> None:
    if not isinstance(plan, list):
        raise MCPValidationError("Plan must be a list")
    for step in plan:
        validate_tool_step(step)
