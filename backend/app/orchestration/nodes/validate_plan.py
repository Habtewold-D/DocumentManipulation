from app.mcp.validators import MCPValidationError, validate_tool_plan


def _normalize_step_args(step: dict, document_id: str | None) -> None:
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


def validate_plan(state: dict) -> dict:
    plan = state.get("plan")
    if not isinstance(plan, list):
        state["status"] = "failed"
        state["error"] = "Invalid plan format"
        return state

    document_id = state.get("document_id")
    if document_id:
        for step in plan:
            if isinstance(step, dict):
                _normalize_step_args(step, document_id)
    else:
        for step in plan:
            if isinstance(step, dict):
                _normalize_step_args(step, None)

    try:
        validate_tool_plan(plan)
    except MCPValidationError as error:
        state["status"] = "failed"
        state["error"] = str(error)
        return state

    state["status"] = "validated"
    return state
