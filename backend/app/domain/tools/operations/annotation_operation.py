from typing import Any

import fitz


def apply_annotations(executor: Any, pdf_doc: fitz.Document, tool_name: str, args: dict[str, Any]) -> int:
    changed = 0
    target_text = str(args.get("target_text", ""))

    if not target_text.strip():
        return 0

    scope = str(args.get("scope", "all")).lower()
    page_number_raw = args.get("page_number")
    page_number = int(page_number_raw) if isinstance(page_number_raw, int | float) and int(page_number_raw) > 0 else None
    occurrence_raw = args.get("occurrence")
    occurrence = int(occurrence_raw) if isinstance(occurrence_raw, int | float) and int(occurrence_raw) > 0 else None
    paragraph_raw = args.get("paragraph_index")
    paragraph_index = int(paragraph_raw) if isinstance(paragraph_raw, int | float) and int(paragraph_raw) > 0 else None

    def _paragraph_index_for_rect(page: fitz.Page, rect: fitz.Rect) -> int | None:
        text_dict = page.get_text("dict")
        paragraph_counter = 0
        for blk in sorted(text_dict.get("blocks", []), key=lambda item: item.get("bbox", [0, 0, 0, 0])[1]):
            if blk.get("type") != 0:
                continue
            lines = blk.get("lines", [])
            if not lines:
                continue
            block_text = "".join(
                "".join(str(span.get("text", "")) for span in line.get("spans", []))
                for line in lines
            ).strip()
            if not block_text:
                continue
            paragraph_counter += 1
            bbox = blk.get("bbox")
            if bbox and fitz.Rect(bbox).intersects(rect):
                return paragraph_counter
        return None

    pages = [pdf_doc[page_number - 1]] if scope == "page" and page_number is not None and page_number <= len(pdf_doc) else list(pdf_doc)

    seen = 0
    for page in pages:
        rects = page.search_for(target_text)
        for rect in rects:
            if paragraph_index is not None and _paragraph_index_for_rect(page, rect) != paragraph_index:
                continue

            seen += 1
            if occurrence is not None and seen != occurrence:
                continue

            if tool_name == "highlight_text":
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=executor._color_tuple(str(args.get("color", "yellow"))))
                annot.update()
            elif tool_name == "underline_text":
                page.add_underline_annot(rect)
            else:
                page.add_strikeout_annot(rect)
            changed += 1

            if occurrence is not None:
                return changed
    return changed
