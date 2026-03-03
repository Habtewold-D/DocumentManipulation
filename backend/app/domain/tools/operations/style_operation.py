from typing import Any

import fitz


def _resolve_target_text_for_style(executor: Any, pdf_doc: fitz.Document, args: dict[str, Any]) -> str:
    target_text = str(args.get("target_text", "") or "")
    if target_text and target_text != "__paragraph_target__":
        return target_text
    if target_text != "__paragraph_target__":
        return ""

    page_number_raw = args.get("page_number")
    page_number = int(page_number_raw) if isinstance(page_number_raw, int | float) and int(page_number_raw) > 0 else None
    paragraph_raw = args.get("paragraph_index")
    paragraph_index = int(paragraph_raw) if isinstance(paragraph_raw, int | float) and int(paragraph_raw) > 0 else 1

    if page_number is None or page_number < 1 or page_number > len(pdf_doc):
        return ""

    page = pdf_doc[page_number - 1]
    text_dict = page.get_text("dict")
    paragraphs: list[str] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines: list[str] = []
        for line in block.get("lines", []):
            line_text = "".join(str(span.get("text", "")) for span in line.get("spans", [])).strip()
            if line_text:
                lines.append(line_text)
        if lines:
            paragraphs.append(" ".join(lines))

    if paragraph_index <= len(paragraphs):
        return paragraphs[paragraph_index - 1]
    return ""


def apply_text_style_change(executor: Any, pdf_doc: fitz.Document, tool_name: str, args: dict[str, Any]) -> int:
    source_target = str(args.get("target_text", "") or "")
    target_text = _resolve_target_text_for_style(executor, pdf_doc, args)
    if not target_text:
        return 0

    transformed = target_text

    anchor = executor._locate_semantic_anchor(pdf_doc, target_text)
    existing_style = {
        "fontsize": anchor["fontsize"],
        "fontname": anchor["fontname"],
        "color": anchor["color"],
    } if anchor else {"fontsize": 11.0, "fontname": "helv", "color": (0, 0, 0)}

    if tool_name == "convert_case":
        case_mode = str(args.get("case", "lower"))
        if case_mode == "upper":
            transformed = target_text.upper()
        elif case_mode == "capitalize":
            transformed = target_text.capitalize()
        else:
            transformed = target_text.lower()

    raw_font_size = args.get("font_size")
    font_size = float(raw_font_size if raw_font_size is not None else existing_style["fontsize"])

    font_name = str(existing_style["fontname"])

    raw_color = args.get("color")
    color = executor._color_tuple(str(raw_color)) if raw_color else existing_style["color"]

    scope = str(args.get("scope", "all")).lower()
    page_number_raw = args.get("page_number")
    page_number = int(page_number_raw) if isinstance(page_number_raw, int | float) and int(page_number_raw) > 0 else None
    occurrence_raw = args.get("occurrence")
    occurrence = int(occurrence_raw) if isinstance(occurrence_raw, int | float) and int(occurrence_raw) > 0 else None
    paragraph_raw = args.get("paragraph_index")
    paragraph_index = int(paragraph_raw) if isinstance(paragraph_raw, int | float) and int(paragraph_raw) > 0 else None

    if tool_name == "set_text_style":
        style = str(args.get("style", ""))
        curr_font = existing_style["fontname"]
        is_currently_bold = curr_font in ["hebo", "hebi", "tibo", "cobo"]
        is_currently_italic = curr_font in ["heit", "hebi", "tiit", "coit"]
        target_bold = is_currently_bold or (style == "bold")
        target_italic = is_currently_italic or (style == "italic")
        if target_bold and target_italic:
            font_name = "hebi"
        elif target_bold:
            font_name = "hebo"
        elif target_italic:
            font_name = "heit"
        else:
            font_name = "helv"

    rhythm_page = pdf_doc[(page_number - 1) if page_number is not None and 1 <= page_number <= len(pdf_doc) else 0]
    try:
        active_lh, active_pg = executor._infer_vertical_rhythm(rhythm_page, existing_style["fontsize"])
    except Exception:
        active_lh, active_pg = None, None

    is_color_only = (tool_name == "change_font_color") or (
        tool_name == "set_text_style" and font_size == existing_style["fontsize"] and font_name == existing_style["fontname"]
    )

    if is_color_only:
        if scope == "page" and page_number is not None:
            return executor._replace_text(
                pdf_doc,
                old_text=target_text,
                new_text=transformed,
                fontsize=font_size,
                fontname=font_name,
                color=color,
                preferred_page_number=page_number,
                restrict_page_number=page_number,
                paragraph_index=paragraph_index,
                occurrence_index=occurrence,
            )
        if occurrence is not None or paragraph_index is not None:
            return executor._replace_text(
                pdf_doc,
                old_text=target_text,
                new_text=transformed,
                fontsize=font_size,
                fontname=font_name,
                color=color,
                paragraph_index=paragraph_index,
                occurrence_index=occurrence,
            )
        return executor._modify_text_inline(
            pdf_doc,
            target_text=target_text,
            fontsize=font_size,
            fontname=font_name,
            color=color,
        )

    override_lh = active_lh
    override_pg = active_pg

    if source_target == "__paragraph_target__" and tool_name == "change_font_size":
        resized_lh = executor._line_height(font_size)
        inferred_pg = float(active_pg) if active_pg is not None else resized_lh * 1.4
        override_lh = max(float(active_lh) if active_lh is not None else resized_lh, resized_lh)
        override_pg = max(inferred_pg, resized_lh * 1.4)

    return executor._replace_text(
        pdf_doc,
        old_text=target_text,
        new_text=transformed,
        fontsize=font_size,
        fontname=font_name,
        color=color,
        line_height_override=override_lh,
        paragraph_gap_override=override_pg,
        preferred_page_number=page_number if scope == "page" else None,
        restrict_page_number=page_number if scope == "page" else None,
        paragraph_index=paragraph_index,
        occurrence_index=occurrence,
    )
