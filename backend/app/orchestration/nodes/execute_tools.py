def execute_tools(state: dict) -> dict:
    if state.get("status") == "failed":
        return state

    executed_tools = []
    for step in state.get("plan", []):
        tool_name = step.get("tool", "unknown") if isinstance(step, dict) else "unknown"
        executed_tools.append({"tool": tool_name, "status": "stubbed"})

    state["executed_tools"] = executed_tools
    state["status"] = "executed"
    return state
