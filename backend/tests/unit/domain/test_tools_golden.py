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