from typing import Any

import fitz


def reflow_remaining_blocks(
    executor: Any,
    pdf_doc: fitz.Document,
    last_res: Any,
    captured_blocks: list[dict[str, Any]],
    active_lh: float,
    active_pg: float,
) -> Any:
    curr_res = last_res
    for block in captured_blocks:
        original_gap = float(block.get("original_gap", 0) or 0)
        block_lh = float(block.get("original_baseline_height") or active_lh)

        if block.get("is_tail"):
            spacing = 0
        elif block.get("same_paragraph"):
            spacing = block_lh
        elif original_gap > 0:
            spacing = max(original_gap, block_lh, active_pg)
        else:
            spacing = active_pg

        start_pt = fitz.Point(block["x0"], curr_res.final_point.y + spacing)
        curr_res = executor._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=curr_res.final_page,
            start_point=start_pt,
            text=block["text"],
            fontsize=block["fontsize"],
            fontname=block["fontname"],
            color=block["color"],
            respect_start_y=True,
            line_height_override=block.get("original_baseline_height") or active_lh,
            paragraph_gap_override=active_pg,
            continuation_x=block.get("continuation_x", block["x0"]),
        )
    return curr_res
