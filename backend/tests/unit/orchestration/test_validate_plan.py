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


def test_validate_plan_normalizes_change_font_size_from_alias() -> None:
    state = {
        "document_id": "doc-1",
        "command": "change font size of Education to 22",
        "plan": [
            {
                "tool": "change_font_size",
                "args": {"target_text": "Education", "size": "22"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["font_size"] == 22


def test_validate_plan_normalizes_change_font_size_from_command_text() -> None:
    state = {
        "document_id": "doc-1",
        "command": "change the font size of this text Education to 22",
        "plan": [
            {
                "tool": "change_font_size",
                "args": {"target_text": "Education"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["font_size"] == 22


def test_validate_plan_normalizes_change_font_size_reference_from_command_text() -> None:
    state = {
        "document_id": "doc-1",
        "command": "make the font size of worku test the same as word Degfie",
        "plan": [
            {
                "tool": "change_font_size",
                "args": {"target_text": "worku test"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["reference_text"] == "Degfie"


def test_validate_plan_normalizes_change_font_size_reference_alias() -> None:
    state = {
        "document_id": "doc-1",
        "plan": [
            {
                "tool": "change_font_size",
                "args": {"target_text": "worku test", "reference_word": "Degfie"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["reference_text"] == "Degfie"


def test_validate_plan_normalizes_add_text_aliases() -> None:
    state = {
        "document_id": "doc-1",
        "plan": [
            {
                "tool": "add_text",
                "args": {
                    "content": "This is a new sentence.",
                    "target_text": "Education",
                    "placement": "below",
                    "page_number": 1,
                    "x": 72,
                    "y": 72,
                },
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["text"] == "This is a new sentence."
    assert args["reference_text"] == "Education"
    assert args["position"] == "below"


def test_validate_plan_add_text_includes_command_text() -> None:
    state = {
        "document_id": "doc-1",
        "command": 'add this text at the end of the second page "hello"',
        "plan": [
            {
                "tool": "add_text",
                "args": {
                    "text": "hello",
                    "page_number": 2,
                    "x": 72,
                    "y": 72,
                },
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["command"] == 'add this text at the end of the second page "hello"'


def test_validate_plan_add_text_extracts_same_line_anchor_from_command() -> None:
    state = {
        "document_id": "doc-1",
        "command": 'add this text "Role" next to "worku test" in the same line',
        "plan": [
            {
                "tool": "add_text",
                "args": {
                    "text": "Role",
                    "page_number": 1,
                    "x": 72,
                    "y": 72,
                },
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["position"] == "next"
    assert args["reference_text"] == "worku test"
