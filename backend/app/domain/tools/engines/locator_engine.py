from typing import Any
import statistics

import fitz


def locate_semantic_anchor(
    executor: Any,
    pdf_doc: fitz.Document,
    anchor_text: str,
    preferred_page_number: int | None = None,
    prefer_last: bool = False,
) -> dict[str, Any] | None:
    if not anchor_text.strip():
        return None
    clean_text = anchor_text.strip()
    words = clean_text.split()

    search_candidates = [
        " ".join(words),
        " ".join(words[1:]) if len(words) > 1 else None,
        " ".join(words[:8]) if len(words) > 8 else None,
        " ".join(words[-6:]) if len(words) > 6 else None,
    ]
    unique_candidates = [candidate for candidate in search_candidates if candidate]

    page_indices = list(range(len(pdf_doc)))
    if prefer_last:
        page_indices = list(reversed(page_indices))
    elif preferred_page_number and 1 <= preferred_page_number <= len(pdf_doc):
        pref_index = preferred_page_number - 1
        page_indices = [pref_index] + [index for index in page_indices if index != pref_index]

    pages_to_scan = [pdf_doc[index] for index in page_indices]

    for candidate in unique_candidates:
        for page in pages_to_scan:
            matches = executor._find_all_matches_on_page(page, candidate)
            if not matches:
                continue

            rects = matches[0] if not prefer_last else matches[-1]
            full_match_rect = fitz.Rect(rects[0])
            for rect in rects:
                full_match_rect |= rect

            start_line_info = executor._find_line_for_rect(page, rects[0])
            end_line_info = executor._find_line_for_rect(page, rects[-1])
            first_line_x, block_x, block_rect = executor._get_block_geometry(page, full_match_rect)

            text_dict = page.get_text("dict", clip=full_match_rect)
            block_spans = [
                span
                for block in text_dict.get("blocks", [])
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            ]
            if not block_spans:
                continue

            return {
                "page": page,
                "rects": rects,
                "full_match_rect": full_match_rect,
                "baseline_y": start_line_info[1] if start_line_info else (rects[0].y1 - 1.0),
                "first_line_x": first_line_x,
                "block_x": block_x,
                "block_rect": block_rect,
                "fontsize": float(block_spans[0]["size"]),
                "fontname": executor._map_span_font_to_base14(str(block_spans[0].get("font", "helv"))),
                "color": executor._color_tuple_from_int(block_spans[0].get("color", 0)),
                "line_bottom": end_line_info[0].y1 if end_line_info else rects[-1].y1,
                "text": candidate,
            }
    return None


def find_all_matches_on_page(page: fitz.Page, text: str) -> list[list[fitz.Rect]]:
    if not text.strip():
        return []

    target_words = text.split()
    if not target_words:
        return []

    page_words = page.get_text("words")
    matches: list[list[fitz.Rect]] = []

    index = 0
    while index <= len(page_words) - len(target_words):
        match = True
        for j in range(len(target_words)):
            page_word = page_words[index + j][4].lower().strip(".,!?;:()[]'\"")
            target_word = target_words[j].lower().strip(".,!?;:()[]'\"")
            if page_word != target_word:
                match = False
                break

        if match:
            match_rects = [fitz.Rect(page_words[index + j][:4]) for j in range(len(target_words))]
            matches.append(match_rects)
            index += len(target_words)
        else:
            index += 1

    return matches


def find_line_for_rect(page: fitz.Page, rect: fitz.Rect) -> tuple[fitz.Rect, float] | None:
    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            bbox = line.get("bbox")
            line_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])

            if not line_rect.intersects(rect):
                continue

            span_origins: list[float] = []
            span_bottoms: list[float] = []
            for span in line.get("spans", []):
                origin = span.get("origin")
                if isinstance(origin, (list, tuple)) and len(origin) == 2:
                    span_origins.append(float(origin[1]))

                span_bbox = span.get("bbox")
                if isinstance(span_bbox, (list, tuple)) and len(span_bbox) == 4:
                    span_bottoms.append(float(span_bbox[3]))

            if span_origins:
                baseline_y = statistics.median(span_origins)
            else:
                baseline_y = (max(span_bottoms) - 1.0) if span_bottoms else (line_rect.y1 - 1.0)

            return (line_rect, baseline_y)
    return None


def get_block_geometry(executor: Any, page: fitz.Page, rect: fitz.Rect) -> tuple[float, float, fitz.Rect | None]:
    text_dict = page.get_text("dict")
    style = executor._infer_page_text_style(page)
    global_margin = float(style["left_x"]) if style else 72.0

    best_first_x = global_margin
    best_block_x = global_margin

    for block in text_dict.get("blocks", []):
        bbox = block.get("bbox")
        block_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        if block_rect.intersects(rect) or (
            bbox[0] <= rect.x0 + 5
            and bbox[1] <= rect.y0 + 5
            and bbox[2] >= rect.x1 - 5
            and bbox[3] >= rect.y1 - 5
        ):
            lines = block.get("lines", [])
            if lines:
                det_first_x = float(lines[0]["bbox"][0])
                det_block_x = float(bbox[0])

                if abs(det_block_x - global_margin) > 150:
                    det_block_x = global_margin
                if abs(det_first_x - global_margin) > 150:
                    det_first_x = global_margin

                return (det_first_x, det_block_x, block_rect)
            return (float(bbox[0]), float(bbox[0]), block_rect)
    return (best_first_x, best_block_x, None)


def capture_rest_of_document_data(
    executor: Any,
    pdf_doc: fitz.Document,
    start_page_idx: int,
    y_threshold: float,
    x_threshold: float | None = None,
    gap_reference_y: float | None = None,
) -> list[dict[str, Any]]:
    captured_blocks: list[dict[str, Any]] = []
    last_block_text = ""

    def process_page(page: fitz.Page, y_min: float, x_min_on_first_line: float | None = None, is_first_page: bool = False) -> None:
        nonlocal last_block_text
        text_dict = page.get_text("dict")
        blocks = sorted(text_dict.get("blocks", []), key=lambda block: block["bbox"][1])

        prev_block_baseline = gap_reference_y if gap_reference_y is not None else y_min
        is_first_block_on_page = True

        for block in blocks:
            if block.get("type") != 0:
                continue
            bbox = block.get("bbox")

            if bbox[3] < y_min - 2:
                continue

            is_same_para = False

            if bbox[1] < y_min + 2 and bbox[3] > y_min - 2:
                tail_text_parts: list[str] = []
                is_actual_tail = False
                for line in block.get("lines", []):
                    lbox = line.get("bbox")

                    if lbox[1] < y_min + 2 and lbox[3] > y_min - 2:
                        if x_min_on_first_line is not None:
                            spans_after = [span for span in line.get("spans", []) if span["bbox"][0] > x_min_on_first_line + 1.0]
                            if spans_after:
                                tail_text_parts.append("".join(span.get("text", "") for span in spans_after))
                                is_actual_tail = True
                                for span in spans_after:
                                    page.add_redact_annot(span["bbox"], fill=(1, 1, 1))
                        else:
                            line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                            if line_text:
                                tail_text_parts.append(line_text)
                                page.add_redact_annot(lbox, fill=(1, 1, 1))
                    elif lbox[1] >= y_min + 2:
                        line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                        if line_text:
                            prefix = "\n" if tail_text_parts else ""
                            tail_text_parts.append(prefix + line_text)
                            page.add_redact_annot(lbox, fill=(1, 1, 1))

                combined_tail_raw = "".join(tail_text_parts).strip()
                if combined_tail_raw:
                    combined_tail = " ".join(combined_tail_raw.splitlines())
                    first_span = block["lines"][0]["spans"][0] if block["lines"] else None
                    captured_blocks.append(
                        {
                            "text": combined_tail,
                            "x0": float(bbox[0]),
                            "x1": float(bbox[2]),
                            "fontsize": float(first_span["size"]) if first_span else 11.0,
                            "fontname": executor._map_span_font_to_base14(str(first_span["font"])) if first_span else "helv",
                            "color": executor._color_tuple_from_int(first_span["color"]) if first_span else (0, 0, 0),
                            "continuation_x": float(block["lines"][1]["bbox"][0]) if len(block["lines"]) > 1 else float(bbox[0]),
                            "is_tail": is_actual_tail,
                            "same_paragraph": False,
                            "original_baseline_height": float(executor._infer_vertical_rhythm(page, first_span["size"])[0]) if first_span else 12.1,
                        }
                    )

                last_line = block["lines"][-1] if block.get("lines") else None
                prev_block_baseline = last_line["spans"][0]["origin"][1] if last_line and last_line.get("spans") else bbox[3]
                continue

            if bbox[1] < y_min - 2:
                continue

            block_text_raw = page.get_text("text", clip=bbox).strip()
            if not block_text_raw:
                continue
            block_text = " ".join(block_text_raw.splitlines())

            page.add_redact_annot(bbox, fill=(1, 1, 1))

            block_spans = [span for line in block.get("lines", []) for span in line.get("spans", [])]
            if not block_spans:
                continue
            fs = float(block_spans[0].get("size", 11.0))
            fontname = executor._map_span_font_to_base14(str(block_spans[0].get("font", "helv")))
            color = executor._color_tuple_from_int(block_spans[0].get("color", 0))

            cont_x = float(bbox[0])
            if len(block.get("lines", [])) > 1:
                cont_x = float(block["lines"][1]["bbox"][0])

            first_line = block["lines"][0] if block.get("lines") else None
            curr_first_baseline = first_line["spans"][0]["origin"][1] if first_line and first_line.get("spans") else bbox[3]

            curr_gap = curr_first_baseline - prev_block_baseline
            force_new_para = False
            if is_first_block_on_page and not is_first_page:
                curr_gap = 0
                if last_block_text.strip().endswith((".", "!", "?", ":")):
                    force_new_para = True

            is_first_block_on_page = False
            lh, pg = executor._infer_vertical_rhythm(page, fs)

            original_lh = lh
            if len(block.get("lines", [])) > 1:
                line_dists: list[float] = []
                for idx in range(1, len(block["lines"])):
                    prev_line = block["lines"][idx - 1]
                    curr_line = block["lines"][idx]
                    if prev_line.get("spans") and curr_line.get("spans"):
                        line_dists.append(curr_line["spans"][0]["origin"][1] - prev_line["spans"][0]["origin"][1])
                if line_dists:
                    original_lh = float(statistics.median(line_dists))

            midpoint = (lh + pg) / 2
            is_same_para_geometric = (curr_gap < midpoint) and (not force_new_para)

            terminators = (".", "!", "?", ":", ";")
            style_match = False
            if captured_blocks:
                prev = captured_blocks[-1]
                style_match = (
                    abs(prev["fontsize"] - fs) < 0.1
                    and prev["fontname"] == fontname
                    and prev["color"] == color
                )

            is_lowercase_start = block_text.strip() and block_text.strip()[0].islower()
            lexical_continuation = last_block_text.strip() and not last_block_text.strip().endswith(terminators)

            is_same_para = is_same_para_geometric or (
                style_match
                and lexical_continuation
                and curr_gap < lh * 2.2
                and (is_lowercase_start or len(last_block_text) > 60)
            )

            if is_same_para and captured_blocks:
                prev = captured_blocks[-1]
                if abs(prev["fontsize"] - fs) < 0.1 and prev["fontname"] == fontname and prev["color"] == color:
                    prev["text"] += " " + block_text
                    prev["x1"] = max(prev["x1"], float(bbox[2]))
                    last_line = block["lines"][-1] if block.get("lines") else None
                    prev_block_baseline = last_line["spans"][0]["origin"][1] if last_line and last_line.get("spans") else bbox[3]
                    last_block_text = block_text
                    continue

            captured_blocks.append(
                {
                    "text": block_text,
                    "x0": float(bbox[0]),
                    "x1": float(bbox[2]),
                    "fontsize": fs,
                    "fontname": fontname,
                    "color": color,
                    "continuation_x": cont_x,
                    "same_paragraph": is_same_para,
                    "original_gap": float(curr_gap),
                    "original_baseline_height": original_lh,
                }
            )
            last_line = block["lines"][-1] if block.get("lines") else None
            prev_block_baseline = last_line["spans"][0]["origin"][1] if last_line and last_line.get("spans") else bbox[3]
            last_block_text = block_text

        page.apply_redactions(images=0, graphics=0)

    process_page(pdf_doc[start_page_idx], y_threshold, x_threshold, is_first_page=True)

    for p_idx in range(start_page_idx + 1, len(pdf_doc)):
        process_page(pdf_doc[p_idx], 0, is_first_page=False)

    return captured_blocks
