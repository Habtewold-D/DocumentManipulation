from uuid import uuid4


def finalize_draft(state: dict) -> dict:
    if state.get("status") == "failed":
        return state

    state["draft_version_id"] = str(uuid4())
    state["status"] = "draft_ready"
    return state
