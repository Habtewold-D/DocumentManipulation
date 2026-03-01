from typing import Any

import fitz


def apply_annotations(executor: Any, pdf_doc: fitz.Document, tool_name: str, args: dict[str, Any]) -> int:
    changed = 0
    target_text = str(args.get("target_text", ""))
    for page in pdf_doc:
        rects = page.search_for(target_text)
        for rect in rects:
            if tool_name == "highlight_text":
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=executor._color_tuple(str(args.get("color", "yellow"))))
                annot.update()
            elif tool_name == "underline_text":
                page.add_underline_annot(rect)
            else:
                page.add_strikeout_annot(rect)
            changed += 1
    return changed
