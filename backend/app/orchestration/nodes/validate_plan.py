import re

from app.mcp.validators import MCPValidationError, validate_tool_plan


def _parse_number(value: object) -> float | int | None:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            number = float(stripped)
            return int(number) if number.is_integer() else number
        except ValueError:
            return None
    return None


def _normalize_step_args(step: dict, document_id: str | None, command: str | None) -> None:
    args = step.setdefault("args", {})
    if not isinstance(args, dict):
        return

    if document_id and "document_id" not in args:
        args["document_id"] = document_id

    tool_name = step.get("tool")
    if not isinstance(tool_name, str):
        return

    target_text_tools = {
        "change_font_type",
        "change_font_size",
        "change_font_color",
        "set_text_style",
        "convert_case",
        "highlight_text",
        "underline_text",
        "strikethrough_text",
    }

    if tool_name in target_text_tools and "target_text" not in args:
        for alias in ("text", "search", "word", "query", "old_text", "target"):
            value = args.get(alias)
            if isinstance(value, str) and value.strip():
                args["target_text"] = value
                break

    if tool_name == "search_replace":
        if "search" not in args and isinstance(args.get("old_text"), str):
            args["search"] = args["old_text"]
        if "replace" not in args and isinstance(args.get("new_text"), str):
            args["replace"] = args["new_text"]

    if tool_name == "replace_text":
        if "old_text" not in args and isinstance(args.get("search"), str):
            args["old_text"] = args["search"]
        if "new_text" not in args and isinstance(args.get("replace"), str):
            args["new_text"] = args["replace"]

    if tool_name == "change_font_color" and "color" not in args:
        for alias in ("font_color", "text_color"):
            value = args.get(alias)
            if isinstance(value, str) and value.strip():
                args["color"] = value
                break

    if tool_name == "change_font_size":
        if "font_size" in args:
            normalized_size = _parse_number(args.get("font_size"))
            if normalized_size is not None:
                args["font_size"] = normalized_size
        if "font_size" not in args:
            for alias in ("size", "new_size", "value", "fontsize", "fontSize"):
                normalized_size = _parse_number(args.get(alias))
                if normalized_size is not None:
                    args["font_size"] = normalized_size
                    break
        if "font_size" not in args and isinstance(command, str):
            match = re.search(r"\b(?:to|size)\s+(\d+(?:\.\d+)?)\b", command.lower())
            if match:
                parsed = _parse_number(match.group(1))
                if parsed is not None:
                    args["font_size"] = parsed

    if tool_name == "add_text":
        if "text" not in args:
            for alias in ("new_text", "content", "value", "insert_text"):
                value = args.get(alias)
                if isinstance(value, str) and value.strip():
                    args["text"] = value
                    break

        if "reference_text" not in args:
            for alias in ("anchor_text", "relative_to", "target_text", "below_text", "next_to_text"):
                value = args.get(alias)
                if isinstance(value, str) and value.strip():
                    args["reference_text"] = value
                    break

        if "position" not in args:
            placement = args.get("placement")
            if isinstance(placement, str) and placement.strip():
                args["position"] = placement

        if isinstance(command, str) and command.strip() and "command" not in args:
            args["command"] = command


def validate_plan(state: dict) -> dict:
    plan = state.get("plan")
    if not isinstance(plan, list):
        state["status"] = "failed"
        state["error"] = "Invalid plan format"
        return state

    document_id = state.get("document_id")
    command = state.get("command")
    if document_id:
        for step in plan:
            if isinstance(step, dict):
                _normalize_step_args(step, document_id, command)
    else:
        for step in plan:
            if isinstance(step, dict):
                _normalize_step_args(step, None, command)

    try:
        validate_tool_plan(plan)
    except MCPValidationError as error:
        state["status"] = "failed"
        state["error"] = str(error)
        return state

    state["status"] = "validated"
    return state
