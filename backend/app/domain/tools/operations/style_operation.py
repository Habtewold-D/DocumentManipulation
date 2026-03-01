from typing import Any

import fitz


def apply_text_style_change(executor: Any, pdf_doc: fitz.Document, tool_name: str, args: dict[str, Any]) -> int:
    target_text = str(args.get("target_text", ""))
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

    try:
        active_lh, active_pg = executor._infer_vertical_rhythm(pdf_doc[0], existing_style["fontsize"])
    except Exception:
        active_lh, active_pg = None, None

    is_color_only = (tool_name == "change_font_color") or (
        tool_name == "set_text_style" and font_size == existing_style["fontsize"] and font_name == existing_style["fontname"]
    )

    if is_color_only:
        return executor._modify_text_inline(
            pdf_doc,
            target_text=target_text,
            fontsize=font_size,
            fontname=font_name,
            color=color,
        )

    if tool_name == "change_font_size":
        override_lh = None
        override_pg = None
    else:
        override_lh = active_lh
        override_pg = active_pg

    return executor._replace_text(
        pdf_doc,
        old_text=target_text,
        new_text=transformed,
        fontsize=font_size,
        fontname=font_name,
        color=color,
        line_height_override=override_lh,
        paragraph_gap_override=override_pg,
    )
