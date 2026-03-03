from app.orchestration.planners.tool_planner import ToolPlanner


def test_create_plan_insert_image_top_of_first_page_with_in_phrase() -> None:
    planner = ToolPlanner()

    result = planner.create_plan(
        "insert this image in the top of the first page",
        image_url="https://example.com/a.jpg",
    )

    assert result["status"] == "fallback"
    assert result["plan"][0]["tool"] == "insert_image"
    args = result["plan"][0]["args"]
    assert args["image_url"] == "https://example.com/a.jpg"
    assert args["page_number"] == "1"
    assert args["position"] == "top"


def test_create_plan_insert_image_top_of_first_page_with_at_phrase() -> None:
    planner = ToolPlanner()

    result = planner.create_plan(
        "insert this image at the top of the first page",
        image_url="https://example.com/a.jpg",
    )

    assert result["status"] == "fallback"
    assert result["plan"][0]["tool"] == "insert_image"
    args = result["plan"][0]["args"]
    assert args["page_number"] == "1"
    assert args["position"] == "top"


def test_create_plan_insert_image_on_second_page_defaults_top() -> None:
    planner = ToolPlanner()

    result = planner.create_plan(
        "put this image on second page",
        image_url="https://example.com/a.jpg",
    )

    assert result["status"] == "fallback"
    assert result["plan"][0]["tool"] == "insert_image"
    args = result["plan"][0]["args"]
    assert args["image_url"] == "https://example.com/a.jpg"
    assert args["page_number"] == "2"
    assert args["position"] == "top"


def test_create_plan_insert_image_above_paragraph_captures_anchor_text() -> None:
    planner = ToolPlanner()

    result = planner.create_plan(
        "insert this image above this paragraph Object-Oriented Programming",
        image_url="https://example.com/a.jpg",
    )

    assert result["status"] == "fallback"
    assert result["plan"][0]["tool"] == "insert_image"
    args = result["plan"][0]["args"]
    assert args["position"] == "above"
    assert args["anchor_text"] == "Object-Oriented Programming"


def test_create_plan_insert_image_below_anchor_text() -> None:
    planner = ToolPlanner()

    result = planner.create_plan(
        "add this image below Phone number: +251901026608",
        image_url="https://example.com/a.jpg",
    )

    assert result["status"] == "fallback"
    assert result["plan"][0]["tool"] == "insert_image"
    args = result["plan"][0]["args"]
    assert args["position"] == "below"
    assert args["anchor_text"] == "Phone number: +251901026608"


def test_create_plan_insert_image_end_of_second_page_maps_to_bottom() -> None:
    planner = ToolPlanner()

    result = planner.create_plan(
        "add this image at the end of the second page",
        image_url="https://example.com/a.jpg",
    )

    assert result["status"] == "fallback"
    assert result["plan"][0]["tool"] == "insert_image"
    args = result["plan"][0]["args"]
    assert args["page_number"] == "2"
    assert args["position"] == "bottom"
