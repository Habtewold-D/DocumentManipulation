from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.orchestration.nodes.execute_tools import execute_tools
from app.orchestration.nodes.finalize_draft import finalize_draft
from app.orchestration.nodes.parse_command import parse_command
from app.orchestration.nodes.validate_plan import validate_plan


class CommandState(TypedDict, total=False):
    document_id: str
    command: str
    plan: list[dict[str, Any]]
    status: str
    error: str
    executed_tools: list[dict[str, Any]]
    draft_version_id: str


class CommandGraph:
    def __init__(self) -> None:
        workflow = StateGraph(CommandState)

        workflow.add_node("parse_command", parse_command)
        workflow.add_node("validate_plan", validate_plan)
        workflow.add_node("execute_tools", execute_tools)
        workflow.add_node("finalize_draft", finalize_draft)

        workflow.add_edge(START, "parse_command")
        workflow.add_edge("parse_command", "validate_plan")
        workflow.add_edge("validate_plan", "execute_tools")
        workflow.add_edge("execute_tools", "finalize_draft")
        workflow.add_edge("finalize_draft", END)

        self._graph = workflow.compile()

    def run(self, document_id: str, command: str) -> dict:
        initial_state: CommandState = {
            "document_id": document_id,
            "command": command,
            "plan": [],
            "status": "pending",
        }
        result = self._graph.invoke(initial_state)
        return dict(result)
