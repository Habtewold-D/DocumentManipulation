from app.orchestration.nodes.validate_plan import validate_plan


def test_validate_plan_normalizes_target_text_alias_for_underline() -> None:
    state = {
        "document_id": "doc-1",
        "plan": [
            {
                "tool": "underline_text",
                "args": {"text": "Habtewold Degfie Worku"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    assert result["plan"][0]["args"]["target_text"] == "Habtewold Degfie Worku"
    assert result["plan"][0]["args"]["document_id"] == "doc-1"


def test_validate_plan_normalizes_search_replace_aliases() -> None:
    state = {
        "document_id": "doc-1",
        "plan": [
            {
                "tool": "search_replace",
                "args": {"old_text": "A", "new_text": "B"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["search"] == "A"
    assert args["replace"] == "B"


def test_validate_plan_normalizes_change_font_color_aliases() -> None:
    state = {
        "document_id": "doc-1",
        "plan": [
            {
                "tool": "change_font_color",
                "args": {"word": "Education", "font_color": "green"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["target_text"] == "Education"
    assert args["color"] == "green"
