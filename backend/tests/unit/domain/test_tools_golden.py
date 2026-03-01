import fitz

from app.domain.tools.executor import ToolExecutor
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