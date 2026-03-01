from typing import Any

import fitz

from app.domain.tools.locator_utils import select_exact_match_rects, union_rects


def replace_text_with_reflow(
    executor: Any,
    pdf_doc: fitz.Document,
    old_text: str,
    new_text: str,
    fontsize: float = 11,
    fontname: str = "helv",
    color: tuple[float, float, float] = (0, 0, 0),
    line_height_override: float | None = None,
    paragraph_gap_override: float | None = None,
    preferred_page_number: int | None = None,
    restrict_page_number: int | None = None,
) -> int:
    anchor = executor._locate_semantic_anchor(pdf_doc, old_text, preferred_page_number=preferred_page_number)
    if not anchor:
        return 0
    if restrict_page_number is not None and anchor["page"].number + 1 != restrict_page_number:
        return 0

    page = anchor["page"]

    exact_matches = executor._find_all_matches_on_page(page, old_text)
    target_rects = select_exact_match_rects(exact_matches, anchor["rects"])
    full_match_rect = union_rects(target_rects)

    start_line_info = executor._find_line_for_rect(page, target_rects[0])
    end_line_info = executor._find_line_for_rect(page, target_rects[-1])
    if start_line_info:
        start_line_rect, start_baseline_y = start_line_info
    else:
        start_line_rect = fitz.Rect(full_match_rect)
        start_baseline_y = anchor["baseline_y"]
    if end_line_info:
        end_line_rect, _ = end_line_info
    else:
        end_line_rect = fitz.Rect(full_match_rect)

    block_rect = anchor.get("block_rect") or fitz.Rect(start_line_rect.x0, start_line_rect.y0, end_line_rect.x1, end_line_rect.y1)

    same_line_tail_tokens: list[tuple[float, str]] = []
    words = page.get_text("words")
    for word in words:
        wx0, wy0, _, wy1, wtext = word[:5]
        if wy1 <= end_line_rect.y0 or wy0 >= end_line_rect.y1:
            continue
        if wx0 >= full_match_rect.x1 - 0.5:
            same_line_tail_tokens.append((float(wx0), str(wtext)))

    same_line_tail = ""
    if same_line_tail_tokens:
        same_line_tail_tokens.sort(key=lambda item: item[0])
        same_line_tail = " ".join(token for _, token in same_line_tail_tokens).strip()

    below_line_tail_parts: list[str] = []
    block_dict = page.get_text("dict", clip=block_rect)
    for blk in block_dict.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []):
            lbox = line.get("bbox")
            if not lbox:
                continue
            if float(lbox[1]) > end_line_rect.y1 + 0.5:
                line_text = "".join(str(span.get("text", "")) for span in line.get("spans", [])).strip()
                if line_text:
                    below_line_tail_parts.append(line_text)

    inline_tail = " ".join(part for part in [same_line_tail, " ".join(below_line_tail_parts).strip()] if part).strip()

    captured_blocks = executor._capture_rest_of_document_data(
        pdf_doc,
        page.number,
        y_threshold=block_rect.y1 + 2.0,
        gap_reference_y=block_rect.y1,
    )

    block_dict_for_redact = page.get_text("dict", clip=block_rect)
    for blk in block_dict_for_redact.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []):
            lbox = line.get("bbox")
            if not lbox:
                continue
            lrect = fitz.Rect(lbox)
            if lrect.y1 < start_line_rect.y0 - 0.5:
                continue

            if lrect.intersects(start_line_rect):
                rx0 = target_rects[0].x0
            else:
                rx0 = block_rect.x0
            rx1 = max(rx0 + 1.0, lrect.x1)
            page.add_redact_annot(fitz.Rect(rx0, lrect.y0, rx1, lrect.y1), fill=(1, 1, 1))
    page.apply_redactions()

    base_lh_detected, base_pg_detected = executor._infer_vertical_rhythm(page, anchor["fontsize"])
    target_lh = executor._line_height(fontsize)
    edited_lh = max(line_height_override or base_lh_detected, target_lh)
    base_lh = base_lh_detected
    pg = paragraph_gap_override or base_pg_detected

    start_pt = fitz.Point(target_rects[0].x0, start_baseline_y)
    res = executor._insert_wrapped_text(
        pdf_doc=pdf_doc,
        start_page=page,
        start_point=start_pt,
        text=new_text,
        fontsize=fontsize,
        fontname=fontname,
        color=color,
        respect_start_y=True,
        line_height_override=edited_lh,
        continuation_x=anchor["block_x"],
    )

    if inline_tail:
        res = executor._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=res.final_page,
            start_point=fitz.Point(res.final_point.x, res.final_point.y),
            text=inline_tail,
            fontsize=anchor["fontsize"],
            fontname=anchor["fontname"],
            color=anchor["color"],
            respect_start_y=True,
            line_height_override=base_lh,
            continuation_x=anchor["block_x"],
        )

    executor._reflow_remaining_blocks(pdf_doc, res, captured_blocks, base_lh, pg)
    return 1
