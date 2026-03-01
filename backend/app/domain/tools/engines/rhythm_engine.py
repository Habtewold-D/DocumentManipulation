from typing import Any
import statistics

import fitz


def infer_vertical_rhythm(executor: Any, page: fitz.Page, fontsize: float) -> tuple[float, float]:
    text_dict = page.get_text("dict")
    all_distances: list[float] = []

    prev_baseline_y = None
    blocks = sorted(text_dict.get("blocks", []), key=lambda b: b["bbox"][1])

    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue

            curr_baseline_y = spans[0]["origin"][1]
            if prev_baseline_y is not None:
                dist = curr_baseline_y - prev_baseline_y
                if 0.5 * fontsize < dist < 8.0 * fontsize:
                    all_distances.append(round(dist * 2) / 2)
            prev_baseline_y = curr_baseline_y

    if not all_distances:
        lh = executor._line_height(fontsize)
        return lh, lh * 1.4

    candidate_lhs = [d for d in all_distances if d > fontsize * 0.8]
    if candidate_lhs:
        counts = statistics.multimode(candidate_lhs)
        lh = float(min(counts))
    else:
        lh = float(statistics.median(all_distances))

    larger_gaps = [d for d in all_distances if d >= lh + 1.0]
    if larger_gaps:
        pg_counts = statistics.multimode(larger_gaps)
        pg = float(min(pg_counts))
    else:
        pg = lh * 1.4

    return lh, pg
