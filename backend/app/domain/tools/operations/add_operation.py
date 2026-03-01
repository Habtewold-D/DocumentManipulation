from typing import Any

import fitz


def apply_add_text(executor: Any, pdf_doc: fitz.Document, args: dict[str, Any]) -> int:
    text = executor._first_non_empty_string(args.get("text"), args.get("new_text"), args.get("content"), args.get("value"))
    if not text:
        raise ValueError("add_text requires non-empty text")

    raw_font_size = args.get("font_size")
    fontsize = float(raw_font_size) if raw_font_size is not None else None
    color = executor._color_tuple(args.get("color"))

    fontname = None

    position = executor._first_non_empty_string(args.get("position"), args.get("placement")).lower()
    command = executor._first_non_empty_string(args.get("command"), args.get("instruction")).lower()
    anchor_text = executor._first_non_empty_string(
        args.get("reference_text"),
        args.get("anchor_text"),
        args.get("relative_to"),
        args.get("target_text"),
        args.get("below_text"),
        args.get("next_to_text"),
    )

    page_number = int(args.get("page_number", 0) or 0)
    auto_coordinates = bool(args.get("_auto_coordinates"))
    has_coordinates = args.get("x") is not None and args.get("y") is not None and not auto_coordinates
    inserted = False
    place_at_end = (
        ("end" in position)
        or ("at end" in command)
        or ("last" in position)
        or ("append" in position)
        or ("end of" in command)
        or ("last part" in command)
        or ("at the last" in command)
        or ("to the last" in command)
    )

    if not anchor_text and page_number > 0 and place_at_end:
        executor._append_text_to_page_end(
            pdf_doc=pdf_doc,
            page_number=page_number,
            text=text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
        )
        inserted = True

    if anchor_text:
        anchor = executor._locate_semantic_anchor(pdf_doc, anchor_text=anchor_text, preferred_page_number=page_number or None, prefer_last=True)
        if anchor:
            user_intent = str(args.get("intent", "paragraph")).lower()
            is_inline = (user_intent == "text") or any(kw in position for kw in ["text", "next to", "beside", "after"])

            if is_inline:
                content_to_add = text.strip()
                if not content_to_add.startswith(" ") and not anchor["text"].strip().endswith(" "):
                    content_to_add = " " + content_to_add
                full_payload = anchor["text"] + content_to_add

                captured_blocks = executor._capture_rest_of_document_data(
                    pdf_doc,
                    anchor["page"].number,
                    y_threshold=anchor["line_bottom"] + 0.5,
                    gap_reference_y=anchor["baseline_y"],
                )
                for rect in anchor["rects"]:
                    anchor["page"].add_redact_annot(rect, fill=(1, 1, 1))
                anchor["page"].apply_redactions()

                lh, pg = executor._infer_vertical_rhythm(anchor["page"], anchor["fontsize"])
                start_pt = fitz.Point(anchor["rects"][0].x0, anchor["baseline_y"])
                res = executor._insert_wrapped_text(
                    pdf_doc=pdf_doc,
                    start_page=anchor["page"],
                    start_point=start_pt,
                    text=full_payload,
                    fontsize=fontsize or anchor["fontsize"],
                    fontname=fontname or anchor["fontname"],
                    color=color or anchor["color"],
                    respect_start_y=True,
                    line_height_override=lh,
                    continuation_x=anchor["block_x"],
                )
                executor._reflow_remaining_blocks(pdf_doc, res, captured_blocks, lh, pg)
            else:
                executor._insert_paragraph_below_anchor(
                    pdf_doc=pdf_doc,
                    page=anchor["page"],
                    anchor_rect=anchor["full_match_rect"],
                    text=text,
                    fontsize=fontsize or anchor["fontsize"],
                    fontname=fontname or anchor["fontname"],
                    color=color or anchor["color"],
                )
            inserted = True

    if not inserted and page_number > 0 and page_number <= len(pdf_doc) and has_coordinates:
        page = pdf_doc[page_number - 1]
        raw_point = fitz.Point(float(args.get("x", 72)), float(args.get("y", 72)))
        start_point = executor._clamp_start_point(page, raw_point, fontsize or 11.0)
        res = executor._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=start_point,
            text=text,
            fontsize=fontsize or 11.0,
            fontname=fontname or "helv",
            color=color,
            avoid_overlay=True,
            respect_start_y=True,
        )
        if res.overflow:
            executor._append_text_to_new_pages(
                pdf_doc=pdf_doc,
                text=res.overflow,
                fontsize=fontsize or 11.0,
                fontname=fontname or "helv",
                color=color,
            )
        inserted = True

    if not inserted:
        executor._append_text_to_page_end(
            pdf_doc=pdf_doc,
            page_number=max(1, len(pdf_doc)),
            text=text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
        )

    return 1
