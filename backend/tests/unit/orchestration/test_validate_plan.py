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


def test_validate_plan_normalizes_remove_text_aliases() -> None:
    state = {
        "document_id": "doc-1",
        "plan": [
            {
                "tool": "remove_text",
                "args": {"target_text": "Confidential"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["old_text"] == "Confidential"
    assert args["scope"] == "all"
    assert args["document_id"] == "doc-1"


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


def test_validate_plan_add_text_extracts_end_position_from_last_part_command() -> None:
    state = {
        "document_id": "doc-1",
        "command": "add this paragraph to the last part",
        "plan": [
            {
                "tool": "add_text",
                "args": {
                    "text": "New paragraph",
                },
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["position"] == "end"


def test_validate_plan_normalizes_invalid_extract_scope() -> None:
    state = {
        "document_id": "doc-1",
        "plan": [
            {
                "tool": "extract_text",
                "args": {"scope": "paragraph"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["scope"] == "all"
    assert args["document_id"] == "doc-1"


def test_validate_plan_parses_page_and_occurrence_from_command() -> None:
    state = {
        "document_id": "doc-1",
        "command": "on first page remove the second occurrence of Habtewold Degfie",
        "plan": [
            {
                "tool": "remove_text",
                "args": {"old_text": "Habtewold Degfie"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["scope"] == "page"
    assert args["page_number"] == 1
    assert args["occurrence"] == 2


def test_validate_plan_parses_paragraph_ordinal_as_paragraph_index() -> None:
    state = {
        "document_id": "doc-1",
        "command": "from the first page replace text in the first paragraph",
        "plan": [
            {
                "tool": "replace_text",
                "args": {"old_text": "A", "new_text": "B"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["scope"] == "page"
    assert args["page_number"] == 1
    assert args["paragraph_index"] == 1


def test_validate_plan_parses_paragraph_word_order_paragraph_three() -> None:
    state = {
        "document_id": "doc-1",
        "command": "change the font size of paragraph three of the first page to 15",
        "plan": [
            {
                "tool": "change_font_size",
                "args": {"font_size": 15},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["scope"] == "page"
    assert args["page_number"] == 1
    assert args["paragraph_index"] == 3
    assert args["target_text"] == "__paragraph_target__"


def test_validate_plan_parses_reversed_occurrence_wording() -> None:
    state = {
        "document_id": "doc-1",
        "command": "change the font size of occurrence first of the word that from the second page to 15",
        "plan": [
            {
                "tool": "change_font_size",
                "args": {"target_text": "that", "font_size": 15},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["scope"] == "page"
    assert args["page_number"] == 2
    assert args["occurrence"] == 1


def test_validate_plan_parses_page_target_for_change_font_color() -> None:
    state = {
        "document_id": "doc-1",
        "command": "on second page change the color of My name is Habtewold Degfie to red",
        "plan": [
            {
                "tool": "change_font_color",
                "args": {"target_text": "My name is Habtewold Degfie", "color": "red"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["scope"] == "page"
    assert args["page_number"] == 2


def test_validate_plan_allows_font_size_first_paragraph_without_explicit_target_text() -> None:
    state = {
        "document_id": "doc-1",
        "command": "change the font size of the first paragraph of the first page to 14",
        "plan": [
            {
                "tool": "change_font_size",
                "args": {},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["target_text"] == "__paragraph_target__"
    assert args["font_size"] == 14
    assert args["scope"] == "page"
    assert args["page_number"] == 1
    assert args["paragraph_index"] == 1


def test_validate_plan_parses_combined_page_paragraph_occurrence() -> None:
    state = {
        "document_id": "doc-1",
        "command": "from first page second paragraph third occurrence change color of Habtewold to red",
        "plan": [
            {
                "tool": "change_font_color",
                "args": {"target_text": "Habtewold", "color": "red"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["scope"] == "page"
    assert args["page_number"] == 1
    assert args["paragraph_index"] == 2
    assert args["occurrence"] == 3


def test_validate_plan_extracts_target_text_from_occurrence_phrase_for_highlight() -> None:
    state = {
        "document_id": "doc-1",
        "command": "from page one second paragraph highlight the second occurrence of I",
        "plan": [
            {
                "tool": "highlight_text",
                "args": {"scope": "from page one second paragraph"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["target_text"] == "I"
    assert args["scope"] == "page"
    assert args["page_number"] == 1
    assert args["paragraph_index"] == 2
    assert args["occurrence"] == 2


def test_validate_plan_extracts_target_text_for_change_font_color_from_occurrence_phrase() -> None:
    state = {
        "document_id": "doc-1",
        "command": "from page one second paragraph change the color of the second occurrence of I to red",
        "plan": [
            {
                "tool": "change_font_color",
                "args": {"color": "red", "scope": "from page one second paragraph"},
            }
        ],
    }

    result = validate_plan(state)

    assert result["status"] == "validated"
    args = result["plan"][0]["args"]
    assert args["target_text"] == "I"
    assert args["scope"] == "page"
    assert args["page_number"] == 1
    assert args["paragraph_index"] == 2
    assert args["occurrence"] == 2
