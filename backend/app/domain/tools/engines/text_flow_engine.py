from typing import Any

import fitz


def insert_paragraph_below_anchor(
    executor: Any,
    pdf_doc: fitz.Document,
    page: fitz.Page,
    anchor_rect: fitz.Rect,
    text: str,
    fontsize: float | None,
    fontname: str | None,
    color: tuple[float, float, float],
) -> None:
    style = executor._infer_page_text_style(page)

    first_line_x, block_x, block_rect = executor._get_block_geometry(page, anchor_rect)
    est_fs = fontsize or (float(style["fontsize"]) if style else 11.0)
    lh, pg = executor._infer_vertical_rhythm(page, est_fs)

    line_info = executor._find_line_for_rect(page, anchor_rect)
    anchor_baseline = line_info[1] if line_info else (anchor_rect.y1 - (lh * 0.2))
    anchor_line_bottom = line_info[0].y1 if line_info else anchor_rect.y1

    if block_rect:
        anchor_line_bottom = block_rect.y1
        text_dict = page.get_text("dict", clip=block_rect)
        for block in text_dict.get("blocks", []):
            if block["lines"]:
                last_line = block["lines"][-1]
                if last_line["spans"]:
                    anchor_baseline = last_line["spans"][0]["origin"][1]

    captured_blocks = executor._capture_rest_of_document_data(
        pdf_doc, page.number, y_threshold=anchor_line_bottom + 2.0, gap_reference_y=anchor_baseline
    )

    start_pt = executor._clamp_start_point(page, fitz.Point(first_line_x, anchor_line_bottom + pg), est_fs)
    res = executor._insert_wrapped_text(
        pdf_doc=pdf_doc,
        start_page=page,
        start_point=start_pt,
        text=text,
        fontsize=est_fs,
        fontname=fontname or (str(style["fontname"]) if style else "helv"),
        color=color,
        respect_start_y=True,
        line_height_override=lh,
        continuation_x=block_x,
    )

    executor._reflow_remaining_blocks(pdf_doc, res, captured_blocks, lh, pg)


def append_text_to_new_pages(
    executor: Any,
    pdf_doc: fitz.Document,
    text: str,
    fontsize: float,
    fontname: str,
    color: tuple[float, float, float],
) -> None:
    if not text.strip():
        return

    margin = 36.0
    page = pdf_doc.new_page()
    res = executor._insert_wrapped_text(
        pdf_doc=pdf_doc,
        start_page=page,
        start_point=fitz.Point(margin, margin + executor._line_height(fontsize)),
        text=text,
        fontsize=fontsize,
        fontname=fontname,
        color=color,
        avoid_overlay=False,
        respect_start_y=True,
    )
    if res.overflow:
        executor._append_text_to_new_pages(pdf_doc, res.overflow, fontsize, fontname, color)


def resolve_non_overlapping_y(
    occupied_rects: list[fitz.Rect],
    x: float,
    y: float,
    line: str,
    fontsize: float,
    fontname: str,
    line_height: float,
    bottom_limit: float,
) -> float:
    line_width = fitz.get_text_length(line, fontname=fontname, fontsize=fontsize)
    candidate_y = y
    max_iterations = 200
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        candidate = fitz.Rect(
            x,
            candidate_y - line_height * 0.9,
            x + line_width,
            candidate_y + line_height * 0.2,
        )
        overlaps = [rect for rect in occupied_rects if rect.intersects(candidate)]
        if not overlaps:
            return candidate_y

        candidate_y = max(rect.y1 for rect in overlaps) + (line_height * 0.9)
        if candidate_y > bottom_limit:
            return candidate_y

    return candidate_y


def append_text_to_page_end(
    executor: Any,
    pdf_doc: fitz.Document,
    page_number: int,
    text: str,
    fontsize: float | None,
    fontname: str | None,
    color: tuple[float, float, float],
) -> None:
    margin = 36.0
    page_index = max(0, min(page_number - 1, len(pdf_doc) - 1))
    page = pdf_doc[page_index]
    style = executor._infer_page_text_style(page)
    resolved_fontsize = float(style["fontsize"]) if style and fontsize is None else float(fontsize or 11.0)
    resolved_fontname = str(style["fontname"]) if style and not fontname else (fontname or "helv")
    resolved_line_height = float(style["line_height"]) if style else executor._line_height(resolved_fontsize)
    left_x = float(style["left_x"]) if style else margin
    right_x = float(style["right_x"]) if style else page.rect.width - margin

    words = page.get_text("words")
    if words:
        last_bottom = max(float(word[3]) for word in words)
        start_y = last_bottom + (resolved_line_height * 1.5)
    else:
        start_y = margin + resolved_line_height

    bottom_limit = page.rect.height - margin
    lines_fit = int(max(0.0, (bottom_limit - start_y)) / max(1.0, resolved_line_height))
    if lines_fit < 3 and words:
        page = pdf_doc.new_page()
        style_new_page = executor._infer_page_text_style(page)
        if style_new_page:
            left_x = float(style_new_page["left_x"])
            right_x = float(style_new_page["right_x"])
        start_y = margin + resolved_line_height

    left_x = max(margin, min(left_x, page.rect.width - margin - 80))
    right_x = max(left_x + 80, min(right_x, page.rect.width - margin))

    start_point = executor._clamp_start_point(page, fitz.Point(left_x, start_y), resolved_fontsize)
    res = executor._insert_wrapped_text(
        pdf_doc=pdf_doc,
        start_page=page,
        start_point=start_point,
        text=text,
        fontsize=resolved_fontsize,
        fontname=resolved_fontname,
        color=color,
        avoid_overlay=True,
        respect_start_y=True,
        line_height_override=resolved_line_height,
        right_limit_x=right_x,
        continuation_x=left_x,
    )
    if res.overflow:
        executor._append_text_to_new_pages(pdf_doc, res.overflow, resolved_fontsize, resolved_fontname, color)
