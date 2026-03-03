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
    paragraph_index: int | None = None,
    occurrence_index: int | None = None,
) -> int:
    def _paragraph_index_for_rect(target_page: fitz.Page, rect: fitz.Rect) -> int | None:
        text_dict = target_page.get_text("dict")
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
            if not bbox:
                continue
            if fitz.Rect(bbox).intersects(rect):
                return paragraph_counter
        return None

    deletion_mode = not new_text.strip()

    anchor = executor._locate_semantic_anchor(pdf_doc, old_text, preferred_page_number=preferred_page_number)
    page = anchor["page"] if anchor else None
    target_rects: list[fitz.Rect] | None = None

    if occurrence_index is not None and occurrence_index > 0:
        if restrict_page_number is not None:
            page_idx = restrict_page_number - 1
            if page_idx < 0 or page_idx >= len(pdf_doc):
                return 0
            page = pdf_doc[page_idx]
            exact_matches = executor._find_all_matches_on_page(page, old_text)
            filtered_matches = exact_matches
            if paragraph_index is not None:
                filtered_matches = [
                    match
                    for match in exact_matches
                    if _paragraph_index_for_rect(page, union_rects(match)) == paragraph_index
                ]
            if occurrence_index > len(filtered_matches):
                return 0
            target_rects = filtered_matches[occurrence_index - 1]
        else:
            seen = 0
            for candidate_page in pdf_doc:
                exact_matches = executor._find_all_matches_on_page(candidate_page, old_text)
                filtered_matches = exact_matches
                if paragraph_index is not None:
                    filtered_matches = [
                        match
                        for match in exact_matches
                        if _paragraph_index_for_rect(candidate_page, union_rects(match)) == paragraph_index
                    ]
                for match in filtered_matches:
                    seen += 1
                    if seen == occurrence_index:
                        page = candidate_page
                        target_rects = match
                        break
                if target_rects is not None:
                    break
            if target_rects is None:
                return 0
    else:
        if not anchor:
            return 0
        if restrict_page_number is not None and anchor["page"].number + 1 != restrict_page_number:
            return 0
        page = anchor["page"]
        exact_matches = executor._find_all_matches_on_page(page, old_text)
        if paragraph_index is not None:
            exact_matches = [
                match
                for match in exact_matches
                if _paragraph_index_for_rect(page, union_rects(match)) == paragraph_index
            ]
            if not exact_matches:
                return 0
            target_rects = exact_matches[0]
        else:
            target_rects = select_exact_match_rects(exact_matches, anchor["rects"])

    if page is None or not target_rects:
        return 0

    full_match_rect = union_rects(target_rects)

    start_line_info = executor._find_line_for_rect(page, target_rects[0])
    end_line_info = executor._find_line_for_rect(page, target_rects[-1])
    if start_line_info:
        start_line_rect, start_baseline_y = start_line_info
    else:
        start_line_rect = fitz.Rect(full_match_rect)
        start_baseline_y = (target_rects[0].y1 - 1.0)
    if end_line_info:
        end_line_rect, _ = end_line_info
    else:
        end_line_rect = fitz.Rect(full_match_rect)

    first_line_x, block_x, inferred_block_rect = executor._get_block_geometry(page, full_match_rect)
    block_rect = inferred_block_rect or fitz.Rect(start_line_rect.x0, start_line_rect.y0, end_line_rect.x1, end_line_rect.y1)

    text_dict = page.get_text("dict", clip=full_match_rect)
    block_spans = [
        span
        for blk in text_dict.get("blocks", [])
        for line in blk.get("lines", [])
        for span in line.get("spans", [])
    ]
    anchor_fontsize = float(block_spans[0].get("size", 11.0)) if block_spans else 11.0
    anchor_fontname = executor._map_span_font_to_base14(str(block_spans[0].get("font", "helv"))) if block_spans else "helv"
    anchor_color = executor._color_tuple_from_int(block_spans[0].get("color", 0)) if block_spans else (0, 0, 0)

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
            lrect = fitz.Rect(lbox)
            if lrect.intersects(end_line_rect):
                continue
            if float(lbox[1]) >= end_line_rect.y1 - 0.5:
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

    base_lh_detected, base_pg_detected = executor._infer_vertical_rhythm(page, anchor_fontsize)
    target_lh = executor._line_height(fontsize)
    edited_lh = max(line_height_override or base_lh_detected, target_lh)
    base_lh = base_lh_detected
    pg = paragraph_gap_override or base_pg_detected

    if deletion_mode and captured_blocks:
        gap_cap = max(float(pg), float(base_lh) * 1.2)
        first_content_block_adjusted = False
        for block in captured_blocks:
            if block.get("same_paragraph") or block.get("is_tail"):
                continue

            original_gap = float(block.get("original_gap", 0) or 0)
            if original_gap > gap_cap * 1.6:
                original_gap = gap_cap

            if not first_content_block_adjusted:
                if inline_tail:
                    block["original_gap"] = min(original_gap, float(pg))
                else:
                    block["original_gap"] = 0.0
                first_content_block_adjusted = True
            else:
                block["original_gap"] = original_gap

    anchor_y = start_baseline_y
    if deletion_mode and not inline_tail:
        margin = 36.0
        anchor_y = max(margin + base_lh, start_baseline_y - float(pg))

    replacement_text = new_text
    inline_gap_x = 0.0
    if inline_tail and replacement_text and not replacement_text.endswith((" ", "\n")) and inline_tail[0].isalnum():
        inline_gap_x = fitz.get_text_length(" ", fontname=anchor_fontname, fontsize=anchor_fontsize)

    start_pt = fitz.Point(target_rects[0].x0, anchor_y)
    if deletion_mode:
        class _DeletionAnchor:
            pass

        res = _DeletionAnchor()
        res.final_page = page
        res.final_point = start_pt
    else:
        res = executor._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=start_pt,
            text=replacement_text,
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
            start_point=fitz.Point(res.final_point.x + inline_gap_x, res.final_point.y),
            text=inline_tail,
            fontsize=anchor_fontsize,
            fontname=anchor_fontname,
            color=anchor_color,
            respect_start_y=True,
            line_height_override=base_lh,
            continuation_x=block_x,
        )

    executor._reflow_remaining_blocks(pdf_doc, res, captured_blocks, base_lh, pg)
    return 1
