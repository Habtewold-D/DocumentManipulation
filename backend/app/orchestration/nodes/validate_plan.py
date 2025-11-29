from app.mcp.validators import MCPValidationError, validate_tool_plan


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
                args = step.setdefault("args", {})
                if isinstance(args, dict) and "document_id" not in args:
                    args["document_id"] = document_id

    try:
        validate_tool_plan(plan)
    except MCPValidationError as error:
        state["status"] = "failed"
        state["error"] = str(error)
        return state

    state["status"] = "validated"
    return state
