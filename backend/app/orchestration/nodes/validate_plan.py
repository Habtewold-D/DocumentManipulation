def validate_plan(state: dict) -> dict:
    if not isinstance(state.get("plan"), list):
        state["status"] = "failed"
        state["error"] = "Invalid plan format"
        return state
    state["status"] = "validated"
    return state
