import fitz


def union_rects(rects: list[fitz.Rect]) -> fitz.Rect:
    merged = fitz.Rect(rects[0])
    for rect in rects[1:]:
        merged |= rect
    return merged


def select_exact_match_rects(
    all_matches: list[list[fitz.Rect]],
    fallback_rects: list[fitz.Rect],
) -> list[fitz.Rect]:
    if all_matches:
        return all_matches[0]
    return fallback_rects
