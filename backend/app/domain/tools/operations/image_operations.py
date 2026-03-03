import fitz
import requests
import re
from typing import Any


def _fit_rect_preserve_aspect(
    image_width: int,
    image_height: int,
    target_x: float,
    target_y: float,
    max_width: float,
    max_height: float,
) -> fitz.Rect:
    if image_width <= 0 or image_height <= 0:
        return fitz.Rect(target_x, target_y, target_x + max_width, target_y + max_height)

    scale = min(max_width / image_width, max_height / image_height)
    scaled_w = max(1.0, image_width * scale)
    scaled_h = max(1.0, image_height * scale)
    return fitz.Rect(target_x, target_y, target_x + scaled_w, target_y + scaled_h)


def _find_anchor_y(page: fitz.Page, anchor_text: str) -> float | None:
    rect = _find_anchor_rect(page, anchor_text)
    if rect is None:
        return None
    return float(rect.y0)


def _find_anchor_bottom_y(page: fitz.Page, anchor_text: str) -> float | None:
    rect = _find_anchor_rect(page, anchor_text)
    if rect is None:
        return None
    return float(rect.y1)


def _normalize_for_match(text: str) -> str:
    lowered = text.lower().strip()
    return re.sub(r"[^a-z0-9]+", "", lowered)


def _find_anchor_rect(page: fitz.Page, anchor_text: str) -> fitz.Rect | None:
    if not anchor_text.strip():
        return None

    # Fast path: exact search first.
    exact_matches = page.search_for(anchor_text)
    if exact_matches:
        return exact_matches[0]

    # Fallback: normalized line-level fuzzy matching.
    anchor_clean = _normalize_for_match(anchor_text)
    if not anchor_clean:
        return None

    anchor_tokens = [token for token in re.findall(r"[a-z0-9]+", anchor_text.lower()) if token]
    anchor_digits = "".join(re.findall(r"\d", anchor_text))
    best_rect: fitz.Rect | None = None
    best_score = 0.0

    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            bbox = line.get("bbox")
            if not bbox:
                continue

            line_text = "".join(str(span.get("text", "")) for span in line.get("spans", [])).strip()
            if not line_text:
                continue

            line_clean = _normalize_for_match(line_text)
            if not line_clean:
                continue

            if anchor_digits and len(anchor_digits) >= 6:
                line_digits = "".join(re.findall(r"\d", line_text))
                if line_digits and anchor_digits in line_digits:
                    return fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])

            if anchor_clean in line_clean or line_clean in anchor_clean:
                return fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])

            line_tokens = set(re.findall(r"[a-z0-9]+", line_text.lower()))
            if not anchor_tokens:
                continue
            overlap = sum(1 for token in anchor_tokens if token in line_tokens)
            score = overlap / max(1, len(anchor_tokens))
            if score > best_score:
                best_score = score
                best_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])

    if best_score >= 0.5:
        return best_rect
    return None


def _find_anchor_in_document(pdf_doc: fitz.Document, preferred_page_index: int, anchor_text: str) -> tuple[int, fitz.Rect] | None:
    if not anchor_text.strip():
        return None

    if 0 <= preferred_page_index < len(pdf_doc):
        rect = _find_anchor_rect(pdf_doc[preferred_page_index], anchor_text)
        if rect is not None:
            return preferred_page_index, rect

    for page_index in range(len(pdf_doc)):
        if page_index == preferred_page_index:
            continue
        rect = _find_anchor_rect(pdf_doc[page_index], anchor_text)
        if rect is not None:
            return page_index, rect

    return None


def _reflow_text_below_insertion(
    executor: Any,
    pdf_doc: fitz.Document,
    page_index: int,
    shift_start_y: float,
    insert_rect: fitz.Rect,
) -> None:
    page = pdf_doc[page_index]

    style = None
    try:
        style = executor._infer_page_text_style(page)
    except Exception:
        style = None

    base_fontsize = float(style["fontsize"]) if isinstance(style, dict) and isinstance(style.get("fontsize"), (int, float)) else 11.0
    try:
        active_lh, active_pg = executor._infer_vertical_rhythm(page, base_fontsize)
    except Exception:
        active_lh = executor._line_height(base_fontsize)
        active_pg = active_lh * 1.4

    captured_blocks = executor._capture_rest_of_document_data(
        pdf_doc,
        page_index,
        y_threshold=shift_start_y,
        gap_reference_y=shift_start_y,
    )

    if not captured_blocks:
        return

    class _Anchor:
        pass

    anchor = _Anchor()
    anchor.final_page = page
    anchor.final_point = fitz.Point(insert_rect.x0, insert_rect.y1)

    executor._reflow_remaining_blocks(pdf_doc, anchor, captured_blocks, active_lh, active_pg)


def apply_image_operations(executor, pdf_doc: fitz.Document, tool_name: str, args: dict[str, Any]) -> int:
    if tool_name == "insert_image":
        page_number_str = args.get("page_number")
        if not isinstance(page_number_str, str) or not page_number_str.isdigit():
            raise ValueError("Invalid page_number for insert_image")
        pno = int(page_number_str) - 1
        if pno < 0 or pno >= len(pdf_doc):
            raise ValueError("Invalid page_number for insert_image")
        image_url = args.get("image_url")
        x = float(args.get("x", 0) or 0)
        y = float(args.get("y", 0) or 0)
        width_raw = args.get("width")
        height_raw = args.get("height")
        width = float(width_raw) if isinstance(width_raw, (int, float)) else None
        height = float(height_raw) if isinstance(height_raw, (int, float)) else None
        position = str(args.get("position", "top") or "top").lower()
        anchor_text = str(args.get("anchor_text", "") or "")
        # Fetch image
        response = requests.get(image_url)
        if response.status_code != 200:
            raise ValueError("Failed to fetch image")
        stream = response.content

        page = pdf_doc[pno]
        margin = 24.0
        max_width = width if width is not None else max(80.0, page.rect.width - (margin * 2))
        max_height = height if height is not None else min(page.rect.height * 0.25, 220.0)

        pix = fitz.Pixmap(stream)
        image_w = int(pix.width)
        image_h = int(pix.height)

        if position == "bottom":
            y = max(margin, page.rect.height - margin - max_height)
            x = margin
        elif position == "above":
            anchor_y = _find_anchor_y(page, anchor_text) if anchor_text else None
            if anchor_y is None:
                anchor_y = margin + max_height + 8
            y = max(margin, anchor_y - max_height - 8)
            x = margin
        elif position == "below":
            resolved_anchor = _find_anchor_in_document(pdf_doc, pno, anchor_text) if anchor_text else None
            if resolved_anchor is None:
                raise ValueError("Anchor text not found for below image insertion")
            resolved_page_index, anchor_rect = resolved_anchor
            if resolved_page_index != pno:
                pno = resolved_page_index
                page = pdf_doc[pno]
                max_width = width if width is not None else max(80.0, page.rect.width - (margin * 2))
                max_height = height if height is not None else min(page.rect.height * 0.25, 220.0)
            y = max(margin, float(anchor_rect.y1) + 8)
            x = margin
        else:
            y = margin
            x = margin

        rect = _fit_rect_preserve_aspect(
            image_width=image_w,
            image_height=image_h,
            target_x=x,
            target_y=y,
            max_width=max_width,
            max_height=max_height,
        )

        # Always center image horizontally on the page.
        centered_x = max(margin, (page.rect.width - rect.width) / 2.0)
        rect = fitz.Rect(centered_x, rect.y0, centered_x + rect.width, rect.y1)

        # Shift text below insertion point using reflow so overflow continues to next pages.
        if position in {"top", "above", "below"}:
            shift_start_y = float(rect.y0)
            _reflow_text_below_insertion(executor, pdf_doc, pno, shift_start_y, rect)

        pdf_doc[pno].insert_image(rect, stream=stream)
        return 1
    elif tool_name == "resize_image":
        page_number_str = args.get("page_number")
        if not isinstance(page_number_str, str) or not page_number_str.isdigit():
            raise ValueError("Invalid page_number for resize_image")
        pno = int(page_number_str) - 1
        if pno < 0 or pno >= len(pdf_doc):
            raise ValueError("Invalid page_number for resize_image")
        image_index_str = args.get("image_index")
        if not isinstance(image_index_str, str) or not image_index_str.isdigit():
            raise ValueError("Invalid image_index for resize_image")
        idx = int(image_index_str)
        new_width = args.get("new_width")
        new_height = args.get("new_height")
        page = pdf_doc[pno]
        annots = list(page.annots())
        if idx >= len(annots):
            raise ValueError("Invalid image_index")
        annot = annots[idx]
        if annot.type[0] != 14:  # not image annotation
            raise ValueError("Annotation is not an image")
        rect = annot.rect
        annot.set_rect(fitz.Rect(rect.x0, rect.y0, rect.x0 + new_width, rect.y0 + new_height))
        return 1
    elif tool_name == "rotate_image":
        page_number_str = args.get("page_number")
        if not isinstance(page_number_str, str) or not page_number_str.isdigit():
            raise ValueError("Invalid page_number for rotate_image")
        pno = int(page_number_str) - 1
        if pno < 0 or pno >= len(pdf_doc):
            raise ValueError("Invalid page_number for rotate_image")
        image_index_str = args.get("image_index")
        if not isinstance(image_index_str, str) or not image_index_str.isdigit():
            raise ValueError("Invalid image_index for rotate_image")
        idx = int(image_index_str)
        angle = args.get("angle")
        page = pdf_doc[pno]
        annots = list(page.annots())
        if idx >= len(annots):
            raise ValueError("Invalid image_index")
        annot = annots[idx]
        if annot.type[0] != 14:  # not image annotation
            raise ValueError("Annotation is not an image")
        annot.set_rotation(angle)
        return 1
    else:
        raise ValueError(f"Unsupported image tool: {tool_name}")
