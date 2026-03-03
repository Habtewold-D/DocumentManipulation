import fitz

from app.domain.tools.executor import ToolExecutor
from app.domain.tools.operations.style_operation import apply_text_style_change
from app.domain.tools.operations.replace_operation import replace_text_with_reflow


class _TestToolExecutor(ToolExecutor):
    def __init__(self) -> None:
        pass  # Avoid network; tests only exercise formatting helpers.


def _build_three_line_document() -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 72.0
    for line in (
        "Executive Summary",
        "Target phrase to replace",
        "Following text continues after the target",
    ):
        page.insert_text((72.0, y), line, fontsize=11, fontname="helv")
        y += 18.0
    return doc


def _build_two_paragraph_document() -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    first_paragraph = (
        "When I began university, I had almost no programming experience. "
        "My interest in coding was sparked during my second semester when I took Fundamentals of Programming. "
        "That course changed the direction of my life. I immediately became fascinated by how logical"
    )
    second_paragraph = (
        "Now I focus on building practical software systems and improving code quality every semester."
    )

    page.insert_textbox(fitz.Rect(72, 72, 520, 240), first_paragraph, fontsize=11, fontname="helv")
    page.insert_textbox(fitz.Rect(72, 280, 520, 360), second_paragraph, fontsize=11, fontname="helv")
    return doc


def _build_multi_paragraph_flow_document() -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    first_paragraph = (
        "When I began university, I had almost no programming experience. "
        "My interest in coding was sparked during my second semester when I took Fundamentals of Programming. "
        "That course changed the direction of my life."
    )
    second_paragraph = (
        "Object-Oriented Programming, Data Structures and Algorithms, and Web Development. "
        "A recent hands-on web development project during last semester solidified my passion."
    )
    third_paragraph = (
        "Looking ahead, my long-term goal is to contribute to impactful technological solutions for society."
    )

    page.insert_textbox(fitz.Rect(72, 72, 520, 220), first_paragraph, fontsize=11, fontname="helv")
    page.insert_textbox(fitz.Rect(72, 255, 520, 390), second_paragraph, fontsize=11, fontname="helv")
    page.insert_textbox(fitz.Rect(72, 430, 520, 520), third_paragraph, fontsize=11, fontname="helv")
    return doc


def _build_four_paragraph_flow_document() -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    first_paragraph = "Paragraph one discusses background and motivation for the document."
    second_paragraph = "Paragraph two covers technical preparation and previous project experience."
    third_paragraph = "Paragraph three explains current focus areas and future implementation details."
    fourth_paragraph = "Paragraph four summarizes expected outcomes and the next practical milestone."

    page.insert_textbox(fitz.Rect(72, 72, 520, 130), first_paragraph, fontsize=11, fontname="helv")
    page.insert_textbox(fitz.Rect(72, 168, 520, 226), second_paragraph, fontsize=11, fontname="helv")
    page.insert_textbox(fitz.Rect(72, 264, 520, 322), third_paragraph, fontsize=11, fontname="helv")
    page.insert_textbox(fitz.Rect(72, 360, 520, 420), fourth_paragraph, fontsize=11, fontname="helv")
    return doc


def _build_repeated_phrase_document() -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 72.0
    for line in (
        "Python is powerful for backend work.",
        "We use Python for automation and tools.",
        "Python can also support data pipelines.",
    ):
        page.insert_text((72.0, y), line, fontsize=11, fontname="helv")
        y += 22.0
    return doc


def _build_two_page_repeat_document() -> fitz.Document:
    doc = fitz.open()
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text((72.0, 72.0), "My name is Habtewold Degfie", fontsize=11, fontname="helv", color=(0, 0, 0))

    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((72.0, 72.0), "My name is Habtewold Degfie", fontsize=11, fontname="helv", color=(0, 0, 0))
    return doc


def _normalized_document_text(pdf_doc: fitz.Document) -> str:
    texts: list[str] = []
    for page in pdf_doc:
        page_text = page.get_text("text")
        trimmed = page_text.strip()
        if not trimmed:
            continue
        texts.append(trimmed.replace("\n", " "))
    combined = " ".join(texts)
    return " ".join(combined.split())


def _raw_document_text(pdf_doc: fitz.Document) -> str:
    return "\n".join(page.get_text("text") for page in pdf_doc)


def test_replace_text_with_reflow_persists_tail_lines() -> None:
    doc = _build_three_line_document()
    executor = _TestToolExecutor()

    result = replace_text_with_reflow(
        executor=executor,
        pdf_doc=doc,
        old_text="Target phrase to replace",
        new_text="Comprehensive replacement content to exercise the reflow engine thoroughly",
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
    )

    normalized_text = _normalized_document_text(doc)

    assert result == 1
    assert "Comprehensive replacement content to exercise the reflow engine thoroughly" in normalized_text
    assert "Following text continues after the target" in normalized_text


def test_replace_text_with_reflow_can_remove_target_text() -> None:
    doc = _build_three_line_document()
    executor = _TestToolExecutor()

    result = replace_text_with_reflow(
        executor=executor,
        pdf_doc=doc,
        old_text="Target phrase to replace",
        new_text="",
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
    )

    normalized_text = _normalized_document_text(doc)

    assert result == 1
    assert "Target phrase to replace" not in normalized_text
    assert "Following text continues after the target" in normalized_text


def test_replace_text_with_reflow_removes_large_paragraph_naturally() -> None:
    doc = _build_two_paragraph_document()
    executor = _TestToolExecutor()

    removed_text = (
        "When I began university, I had almost no programming experience. "
        "My interest in coding was sparked during my second semester when I took Fundamentals of Programming. "
        "That course changed the direction of my life. I immediately became fascinated by how logical"
    )

    result = replace_text_with_reflow(
        executor=executor,
        pdf_doc=doc,
        old_text=removed_text,
        new_text="",
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
    )

    normalized_text = _normalized_document_text(doc)
    raw_text = _raw_document_text(doc)

    assert result == 1
    assert "When I began university" not in normalized_text
    assert "Now I focus on building practical software systems" in normalized_text
    assert "\n\n\n" not in raw_text


def test_remove_text_from_middle_of_paragraph_preserves_flow() -> None:
    doc = _build_multi_paragraph_flow_document()
    executor = _TestToolExecutor()

    removed_text = "My interest in coding was sparked during my second semester when I took Fundamentals of Programming."

    result = replace_text_with_reflow(
        executor=executor,
        pdf_doc=doc,
        old_text=removed_text,
        new_text="",
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
    )

    normalized_text = _normalized_document_text(doc)
    raw_text = _raw_document_text(doc)

    assert result == 1
    assert removed_text not in normalized_text
    assert "When I began university, I had almost no programming experience." in normalized_text
    assert "course changed the direction of my life." in normalized_text
    assert "\n\n\n" not in raw_text


def test_remove_text_from_start_of_paragraph_avoids_large_gap() -> None:
    doc = _build_multi_paragraph_flow_document()
    executor = _TestToolExecutor()

    removed_text = "When I began university, I had almost no programming experience."

    result = replace_text_with_reflow(
        executor=executor,
        pdf_doc=doc,
        old_text=removed_text,
        new_text="",
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
    )

    normalized_text = _normalized_document_text(doc)
    raw_text = _raw_document_text(doc)

    assert result == 1
    assert removed_text not in normalized_text
    assert "My interest in coding was sparked during my second semester" in normalized_text
    assert "\n\n\n" not in raw_text


def test_remove_full_paragraph_avoids_double_gap() -> None:
    doc = _build_multi_paragraph_flow_document()
    executor = _TestToolExecutor()

    removed_text = (
        "Object-Oriented Programming, Data Structures and Algorithms, and Web Development. "
        "A recent hands-on web development project during last semester solidified my passion."
    )

    result = replace_text_with_reflow(
        executor=executor,
        pdf_doc=doc,
        old_text=removed_text,
        new_text="",
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
    )

    normalized_text = _normalized_document_text(doc)
    raw_text = _raw_document_text(doc)

    assert result == 1
    assert "Object-Oriented Programming" not in normalized_text
    assert "That course changed the direction of my life." in normalized_text
    assert "Looking ahead, my long-term goal" in normalized_text
    assert "\n\n\n" not in raw_text


def test_replace_text_with_reflow_targets_specific_occurrence_only() -> None:
    doc = _build_repeated_phrase_document()
    executor = _TestToolExecutor()

    result = replace_text_with_reflow(
        executor=executor,
        pdf_doc=doc,
        old_text="Python",
        new_text="Django",
        fontsize=11,
        fontname="helv",
        color=(0, 0, 0),
        occurrence_index=2,
    )

    normalized_text = _normalized_document_text(doc)

    assert result == 1
    assert "Python is powerful for backend work." in normalized_text
    assert "We use Django for automation and tools." in normalized_text
    assert "Python can also support data pipelines." in normalized_text


def test_change_font_color_page_scope_applies_only_on_target_page() -> None:
    doc = _build_two_page_repeat_document()
    executor = _TestToolExecutor()

    changed = apply_text_style_change(
        executor,
        doc,
        "change_font_color",
        {
            "target_text": "My name is Habtewold Degfie",
            "color": "red",
            "scope": "page",
            "page_number": 2,
        },
    )

    page1_text = doc[0].get_text("text")
    page2_text = doc[1].get_text("text")

    assert changed == 1
    assert "My name is Habtewold Degfie" in page1_text
    assert "My name is Habtewold Degfie" in page2_text


def test_change_font_size_first_paragraph_preserves_gap_to_next_paragraph() -> None:
    doc = _build_multi_paragraph_flow_document()
    executor = _TestToolExecutor()

    page = doc[0]
    first_para_tail_before = page.search_for("life.")
    second_para_head_before = page.search_for("Object-Oriented")
    assert first_para_tail_before and second_para_head_before
    before_gap = second_para_head_before[0].y0 - first_para_tail_before[-1].y1

    changed = apply_text_style_change(
        executor,
        doc,
        "change_font_size",
        {
            "target_text": "__paragraph_target__",
            "font_size": 14,
            "scope": "page",
            "page_number": 1,
            "paragraph_index": 1,
        },
    )

    page_after = doc[0]
    first_para_tail_after = page_after.search_for("life.")
    second_para_head_after = page_after.search_for("Object-Oriented")

    assert changed == 1
    assert first_para_tail_after and second_para_head_after

    after_gap = second_para_head_after[0].y0 - first_para_tail_after[-1].y1
    assert after_gap > 4.0
    assert after_gap >= before_gap * 0.4


def test_change_font_size_without_target_text_does_not_modify_first_paragraph() -> None:
    doc = _build_multi_paragraph_flow_document()
    executor = _TestToolExecutor()

    before_text = _normalized_document_text(doc)

    changed = apply_text_style_change(
        executor,
        doc,
        "change_font_size",
        {
            "font_size": 15,
            "scope": "page",
            "page_number": 1,
        },
    )

    after_text = _normalized_document_text(doc)

    assert changed == 0
    assert after_text == before_text


def test_change_font_size_third_paragraph_preserves_gap_to_next_paragraph() -> None:
    doc = _build_four_paragraph_flow_document()
    executor = _TestToolExecutor()

    page = doc[0]
    third_para_tail_before = page.search_for("details.")
    fourth_para_head_before = page.search_for("Paragraph four")
    assert third_para_tail_before and fourth_para_head_before
    before_gap = fourth_para_head_before[0].y0 - third_para_tail_before[-1].y1

    changed = apply_text_style_change(
        executor,
        doc,
        "change_font_size",
        {
            "target_text": "__paragraph_target__",
            "font_size": 16,
            "scope": "page",
            "page_number": 1,
            "paragraph_index": 3,
        },
    )

    page_after = doc[0]
    third_para_tail_after = page_after.search_for("details.")
    fourth_para_head_after = page_after.search_for("Paragraph four")

    assert changed == 1
    assert third_para_tail_after and fourth_para_head_after

    after_gap = fourth_para_head_after[0].y0 - third_para_tail_after[-1].y1
    assert after_gap > 4.0
    assert after_gap >= before_gap * 0.4


def test_add_page_before_first():
    doc = _build_three_line_document()
    original_len = len(doc)
    executor = _TestToolExecutor()
    executor._load_doc = lambda asset_id: doc
    executor._save_new_version = lambda document_id, pdf_doc: {"asset_id": "test", "url": "test"}
    executor._build_preview_manifest = lambda pdf_doc: {"pages": []}

    result = executor._execute_internal("add_page", {
        "document_id": "test",
        "position": "before",
        "page_number": "1",
        "source_page": None
    })

    assert result["success"] == True
    assert len(doc) == original_len + 1
    assert result["output"]["changes"] == 1


def test_add_page_after_last():
    doc = _build_three_line_document()
    original_len = len(doc)
    executor = _TestToolExecutor()
    executor._load_doc = lambda asset_id: doc
    executor._save_new_version = lambda document_id, pdf_doc: {"asset_id": "test", "url": "test"}
    executor._build_preview_manifest = lambda pdf_doc: {"pages": []}

    result = executor._execute_internal("add_page", {
        "document_id": "test",
        "position": "after",
        "page_number": str(original_len),
        "source_page": None
    })

    assert result["success"] == True
    assert len(doc) == original_len + 1
    assert result["output"]["changes"] == 1


def test_add_page_with_source():
    doc = _build_three_line_document()
    original_len = len(doc)
    executor = _TestToolExecutor()
    executor._load_doc = lambda asset_id: doc
    executor._save_new_version = lambda document_id, pdf_doc: {"asset_id": "test", "url": "test"}
    executor._build_preview_manifest = lambda pdf_doc: {"pages": []}

    result = executor._execute_internal("add_page", {
        "document_id": "test",
        "position": "after",
        "page_number": "1",
        "source_page": "1"
    })

    assert result["success"] == True
    assert len(doc) == original_len + 1
    assert result["output"]["changes"] == 1


def test_add_page_invalid_position():
    doc = _build_three_line_document()
    executor = _TestToolExecutor()
    executor._load_doc = lambda asset_id: doc

    result = executor._execute_internal("add_page", {
        "document_id": "test",
        "position": "invalid",
        "page_number": "1"
    })

    assert result["success"] == False
    assert "Invalid position" in result["error"]


def test_delete_page():
    doc = _build_three_line_document()
    # Add a second page for testing
    doc.new_page()
    original_len = len(doc)
    executor = _TestToolExecutor()
    executor._load_doc = lambda asset_id: doc
    executor._save_new_version = lambda document_id, pdf_doc: {"asset_id": "test", "url": "test"}
    executor._build_preview_manifest = lambda pdf_doc: {"pages": []}

    result = executor._execute_internal("delete_page", {
        "document_id": "test",
        "page_number": "2"
    })

    assert result["success"] == True
    assert len(doc) == original_len - 1
    assert result["output"]["changes"] == 1


def test_delete_page_invalid():
    doc = _build_three_line_document()
    executor = _TestToolExecutor()
    executor._load_doc = lambda asset_id: doc

    result = executor._execute_internal("delete_page", {
        "document_id": "test",
        "page_number": "2"  # only 1 page
    })

    assert result["success"] == False
    assert "Invalid page_number" in result["error"]


def test_reorder_pages():
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i+1}")
    original_len = len(doc)
    executor = _TestToolExecutor()
    executor._load_doc = lambda asset_id: doc
    executor._save_new_version = lambda document_id, pdf_doc: {"asset_id": "test", "url": "test"}
    executor._build_preview_manifest = lambda pdf_doc: {"pages": []}

    result = executor._execute_internal("reorder_pages", {
        "document_id": "test",
        "page_order": ["3", "1", "2"]
    })

    assert result["success"] == True
    assert len(doc) == original_len
    assert result["output"]["changes"] == original_len
    # Check content reordered
    assert "Page 3" in doc[0].get_text()
    assert "Page 1" in doc[1].get_text()
    assert "Page 2" in doc[2].get_text()


def test_reorder_pages_invalid():
    doc = _build_three_line_document()
    executor = _TestToolExecutor()
    executor._load_doc = lambda asset_id: doc

    result = executor._execute_internal("reorder_pages", {
        "document_id": "test",
        "page_order": ["1", "2"]  # wrong length
    })

    assert result["success"] == False
    assert "Invalid page_order" in result["error"]