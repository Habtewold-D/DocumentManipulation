from app.orchestration.planners.tool_planner import ToolPlanner


def parse_command(state: dict) -> dict:
    planner = ToolPlanner()
    plan_result = planner.create_plan(state["command"], state.get("imageUrl"))
    state["plan"] = plan_result.get("plan", [])
    state["status"] = "planned"
    return state
