from app.domain.tools.executor import ToolExecutor


def execute_tools(state: dict) -> dict:
    if state.get("status") == "failed":
        return state

    executor = ToolExecutor()
    executed_tools = []
    document_id = state.get("document_id")
    current_asset_id = state.get("source_asset_id")

    for step in state.get("plan", []):
        tool_name = step.get("tool", "unknown") if isinstance(step, dict) else "unknown"
        args = step.get("args", {}) if isinstance(step, dict) else {}
        if document_id and "document_id" not in args:
            args["document_id"] = document_id
        if current_asset_id and "source_asset_id" not in args:
            args["source_asset_id"] = current_asset_id
        result = executor.execute(tool_name, args)
        output = result.get("output", {}) if isinstance(result, dict) else {}
        if isinstance(output, dict) and output.get("asset_id"):
            current_asset_id = output["asset_id"]
        executed_tools.append(result)

    state["executed_tools"] = executed_tools
    state["result_asset_id"] = current_asset_id
    state["status"] = "executed"
    return state
