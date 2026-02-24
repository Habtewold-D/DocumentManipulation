from typing import Any
import hashlib
import statistics

import fitz

from app.storage.asset_service import AssetService
from app.storage.cloudinary_client import CloudinaryClient


class ToolExecutionResult(dict):
    pass


class ToolExecutor:
    def __init__(self) -> None:
        self.cloudinary = CloudinaryClient()
        self.asset_service = AssetService(self.cloudinary)

    @staticmethod
    def _color_tuple(color: str | None) -> tuple[float, float, float]:
        if not color:
            return (0, 0, 0)
        value = color.strip().lower()
        named = {
            "black": (0, 0, 0),
            "red": (1, 0, 0),
            "green": (0, 0.6, 0),
            "blue": (0, 0, 1),
            "yellow": (1, 1, 0),
        }
        if value in named:
            return named[value]
        if value.startswith("#") and len(value) == 7:
            r = int(value[1:3], 16) / 255
            g = int(value[3:5], 16) / 255
            b = int(value[5:7], 16) / 255
            return (r, g, b)
        return (0, 0, 0)

    def _load_doc(self, asset_id: str) -> fitz.Document:
        file_bytes = self.cloudinary.download_asset_bytes(asset_id)
        return fitz.open(stream=file_bytes, filetype="pdf")

    def _save_new_version(self, document_id: str, pdf_doc: fitz.Document) -> dict[str, Any]:
        output_bytes = pdf_doc.tobytes(garbage=4, deflate=True)
        upload = self.asset_service.upload_version_pdf(output_bytes, document_id=document_id)
        return {
            "asset_id": upload.get("asset_id"),
            "url": upload.get("secure_url"),
        }

    @staticmethod
    def _build_preview_manifest(pdf_doc: fitz.Document) -> dict[str, Any]:
        pages: list[dict[str, Any]] = []
        for index, page in enumerate(pdf_doc, start=1):
            content = page.get_text("text")
            page_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            pages.append({"page": index, "hash": page_hash})
        return {"pages": pages}

    def _replace_text(
        self,
        pdf_doc: fitz.Document,
        old_text: str,
        new_text: str,
        fontsize: float = 11,
        fontname: str = "helv",
        color: tuple[float, float, float] = (0, 0, 0),
        preserve_line_baseline: bool = False,
    ) -> int:
        replacements = 0
        for page in pdf_doc:
            rects = page.search_for(old_text)
            for rect in rects:
                page.add_redact_annot(rect, fill=(1, 1, 1))
            if rects:
                page.apply_redactions()
            for rect in rects:
                long_paragraph_replace = len(new_text.strip()) > 80 and len(new_text.strip()) > max(20, len(old_text.strip()) * 2)
                line_info = self._find_line_for_rect(page, rect)

                if line_info and (preserve_line_baseline or long_paragraph_replace):
                    line_rect, baseline_y = line_info
                    start_x = line_rect.x0 if long_paragraph_replace else rect.x0
                    start_point = fitz.Point(start_x, baseline_y)
                    respect_start_y = True
                else:
                    baseline_y = rect.y1 - 1 if preserve_line_baseline else max(36, rect.y0 + fontsize)
                    start_point = fitz.Point(rect.x0, baseline_y)
                    respect_start_y = preserve_line_baseline

                overflow = self._insert_wrapped_text(
                    pdf_doc=pdf_doc,
                    start_page=page,
                    start_point=start_point,
                    text=new_text,
                    fontsize=fontsize,
                    fontname=fontname,
                    color=color,
                    avoid_overlay=True,
                    respect_start_y=respect_start_y,
                )
                if overflow:
                    self._append_text_to_new_pages(
                        pdf_doc=pdf_doc,
                        text=overflow,
                        fontsize=fontsize,
                        fontname=fontname,
                        color=color,
                    )
                replacements += 1
        return replacements

    @staticmethod
    def _line_height(fontsize: float) -> float:
        return max(12.0, fontsize * 1.35)

    @staticmethod
    def _wrap_text_to_width(text: str, fontname: str, fontsize: float, max_width: float) -> list[str]:
        words = text.split()
        if not words:
            return []

        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _insert_wrapped_text(
        self,
        pdf_doc: fitz.Document,
        start_page: fitz.Page,
        start_point: fitz.Point,
        text: str,
        fontsize: float,
        fontname: str,
        color: tuple[float, float, float],
        avoid_overlay: bool = False,
        respect_start_y: bool = False,
        line_height_override: float | None = None,
        right_limit_x: float | None = None,
        continuation_x: float | None = None,
    ) -> str:
        margin = 36.0
        page = start_page
        page_index = page.number
        line_height = line_height_override if line_height_override is not None else self._line_height(fontsize)

        y = start_point.y if respect_start_y else max(start_point.y, margin + line_height)
        effective_right_x = min(page.rect.width - margin, right_limit_x) if right_limit_x is not None else page.rect.width - margin
        max_width = max(80.0, effective_right_x - start_point.x)
        lines = self._wrap_text_to_width(text, fontname=fontname, fontsize=fontsize, max_width=max_width)

        occupied_cache: dict[int, list[fitz.Rect]] = {}
        remaining_lines: list[str] = []
        for line in lines:
            while True:
                bottom_limit = page.rect.height - margin
                if y > bottom_limit:
                    page_index += 1
                    if page_index < len(pdf_doc):
                        page = pdf_doc[page_index]
                    else:
                        page = pdf_doc.new_page()
                    y = margin + line_height
                    next_x = continuation_x if continuation_x is not None else margin
                    effective_right_x = (
                        min(page.rect.width - margin, right_limit_x) if right_limit_x is not None else page.rect.width - margin
                    )
                    max_width = max(80.0, effective_right_x - next_x)

                if y > page.rect.height - margin:
                    remaining_lines.append(line)
                    break

                x = start_point.x if page.number == start_page.number else (continuation_x if continuation_x is not None else margin)
                if avoid_overlay:
                    if page.number not in occupied_cache:
                        occupied_cache[page.number] = [
                            fitz.Rect(w[0], w[1], w[2], w[3]) for w in page.get_text("words")
                        ]
                    y = self._resolve_non_overlapping_y(
                        occupied_rects=occupied_cache[page.number],
                        x=x,
                        y=y,
                        line=line,
                        fontsize=fontsize,
                        fontname=fontname,
                        line_height=line_height,
                        bottom_limit=bottom_limit,
                    )
                    if y > bottom_limit:
                        page_index += 1
                        if page_index < len(pdf_doc):
                            page = pdf_doc[page_index]
                        else:
                            page = pdf_doc.new_page()
                        y = margin + line_height
                        next_x = continuation_x if continuation_x is not None else margin
                        effective_right_x = (
                            min(page.rect.width - margin, right_limit_x) if right_limit_x is not None else page.rect.width - margin
                        )
                        max_width = max(80.0, effective_right_x - next_x)
                        continue

                page.insert_text(
                    point=(x, y),
                    text=line,
                    fontsize=fontsize,
                    fontname=fontname,
                    color=color,
                )
                if avoid_overlay:
                    line_width = fitz.get_text_length(line, fontname=fontname, fontsize=fontsize)
                    occupied_cache[page.number].append(
                        fitz.Rect(x, y - line_height * 0.9, x + line_width, y + line_height * 0.2)
                    )
                y += line_height
                break

        return " ".join(remaining_lines).strip()

    @staticmethod
    def _infer_font_size_from_reference(pdf_doc: fitz.Document, reference_text: str) -> float | None:
        token = reference_text.strip()
        if not token:
            return None

        lower_token = token.lower()
        for page in pdf_doc:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = str(span.get("text", ""))
                        if lower_token in span_text.lower():
                            size = span.get("size")
                            if isinstance(size, (int, float)):
                                return float(size)

        for page in pdf_doc:
            rects = page.search_for(token)
            if rects:
                estimated = rects[0].height * 0.9
                if estimated > 0:
                    return float(estimated)

        return None

    @staticmethod
    def _map_span_font_to_base14(span_font: str | None) -> str:
        token = (span_font or "").lower()
        is_bold = "bold" in token
        is_italic = any(flag in token for flag in ("italic", "oblique"))

        if "times" in token:
            if is_bold and is_italic:
                return "tibo"
            if is_bold:
                return "tibo"
            if is_italic:
                return "tiit"
            return "tiro"
        if "courier" in token:
            if is_bold and is_italic:
                return "cobo"
            if is_bold:
                return "cobo"
            if is_italic:
                return "coit"
            return "cour"

        if is_bold:
            return "hebo"
        if is_italic:
            return "heit"
        return "helv"

    def _infer_page_text_style(self, page: fitz.Page) -> dict[str, float | str] | None:
        text_dict = page.get_text("dict")
        last_span: dict[str, Any] | None = None
        
        # Result lists to be populated
        line_bboxes: list[tuple[float, float, float, float]] = []
        size_values: list[float] = []
        left_values: list[float] = []
        right_values: list[float] = []

        # Pass 1: Collect font sizes to determine the primary size for the page
        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_text = str(span.get("text", "")).strip()
                    if not span_text:
                        continue
                    last_span = span
                    size = span.get("size")
                    if isinstance(size, (int, float)):
                        size_values.append(float(size))

        if not last_span:
            return None

        primary_fontsize = float(statistics.median(size_values)) if size_values else 11.0
        fontname = self._map_span_font_to_base14(str(last_span.get("font", "")))

        # Pass 2: Calculate line spacings and layout boundaries using detected font size
        prev_line_baseline: float | None = None
        inter_line_distances: list[float] = []

        for block in text_dict.get("blocks", []):
            block_lines = block.get("lines", [])
            prev_line_baseline = None
            for line in block_lines:
                line_bbox = line.get("bbox")
                spans = line.get("spans", [])
                merged_text = " ".join(str(span.get("text", "")).strip() for span in spans).strip()
                
                if isinstance(line_bbox, (list, tuple)) and len(line_bbox) == 4:
                    line_bbox_tuple = (float(line_bbox[0]), float(line_bbox[1]), float(line_bbox[2]), float(line_bbox[3]))
                    line_bboxes.append(line_bbox_tuple)
                    
                    # Detect line baseline
                    curr_baseline: float | None = None
                    for span in spans:
                        if str(span.get("text", "")).strip():
                            origin = span.get("origin")
                            if isinstance(origin, (list, tuple)) and len(origin) == 2:
                                curr_baseline = float(origin[1])
                                break
                    
                    if curr_baseline is None:
                        curr_baseline = line_bbox_tuple[3] # Fallback

                    if prev_line_baseline is not None:
                        dist = curr_baseline - prev_line_baseline
                        # Valid line skip should be roughly between 0.9x and 3.5x font size
                        if primary_fontsize * 0.9 <= dist <= primary_fontsize * 3.5:
                            inter_line_distances.append(dist)
                    
                    prev_line_baseline = curr_baseline

                    if len(merged_text) >= 25:
                        left_values.append(line_bbox_tuple[0])
                        right_values.append(line_bbox_tuple[2])

        fontsize = primary_fontsize

        if not last_span:
            return None

        size = last_span.get("size")
        if size_values:
            fontsize = float(statistics.median(size_values))
        else:
            fontsize = float(size) if isinstance(size, (int, float)) else 11.0
        fontname = self._map_span_font_to_base14(str(last_span.get("font", "")))

        if inter_line_distances:
            # Use the median of observed line-to-line distances for accurate leading
            line_height = float(statistics.median(inter_line_distances))
        elif line_bboxes:
            # Fallback to bbox height with a 1.2x multiplier if single line
            median_bbox_height = float(statistics.median([b[3]-b[1] for b in line_bboxes]))
            line_height = max(self._line_height(fontsize), median_bbox_height * 1.2)
        else:
            line_height = self._line_height(fontsize)

        left_x = float(statistics.median(left_values)) if left_values else 36.0
        right_x = float(statistics.median(right_values)) if right_values else page.rect.width - 36.0
        if right_x - left_x < 120:
            left_x = 36.0
            right_x = page.rect.width - 36.0

        return {
            "fontsize": fontsize,
            "fontname": fontname,
            "line_height": line_height,
            "left_x": left_x,
            "right_x": right_x,
        }

    @staticmethod
    def _find_line_for_rect(page: fitz.Page, rect: fitz.Rect) -> tuple[fitz.Rect, float] | None:
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                bbox = line.get("bbox")
                if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                    continue

                line_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                if not line_rect.intersects(rect):
                    continue

                span_bottoms = []
                for span in line.get("spans", []):
                    span_bbox = span.get("bbox")
                    if isinstance(span_bbox, (list, tuple)) and len(span_bbox) == 4:
                        span_bottoms.append(float(span_bbox[3]))
                baseline_y = (max(span_bottoms) - 1.0) if span_bottoms else (line_rect.y1 - 1.0)
                return (line_rect, baseline_y)
        return None

    def _insert_paragraph_below_anchor(
        self,
        pdf_doc: fitz.Document,
        page: fitz.Page,
        anchor_rect: fitz.Rect,
        text: str,
        fontsize: float | None,
        fontname: str | None,
        color: tuple[float, float, float],
    ) -> None:
        margin = 36.0
        style = self._infer_page_text_style(page)
        resolved_fontsize = float(style["fontsize"]) if style and fontsize is None else float(fontsize or 11.0)
        resolved_fontname = str(style["fontname"]) if style and not fontname else (fontname or "helv")
        resolved_line_height = float(style["line_height"]) if style else self._line_height(resolved_fontsize)
        left_x = float(style["left_x"]) if style else margin
        right_x = float(style["right_x"]) if style else page.rect.width - margin

        line_info = self._find_line_for_rect(page, anchor_rect)
        anchor_line_bottom = line_info[0].y1 if line_info else anchor_rect.y1
        # Use a paragraph spacing that feels natural (usually 1.5x to 2x the line height)
        paragraph_spacing = resolved_line_height * 1.5
        start_y = anchor_line_bottom + paragraph_spacing

        bottom_limit = page.rect.height - margin
        lines_fit = int(max(0.0, (bottom_limit - start_y)) / max(1.0, resolved_line_height))
        if lines_fit < 3:
            page = pdf_doc.new_page()
            style_new = self._infer_page_text_style(page)
            if style_new:
                left_x = float(style_new["left_x"])
                right_x = float(style_new["right_x"])
            start_y = margin + resolved_line_height

        left_x = max(margin, min(left_x, page.rect.width - margin - 80))
        right_x = max(left_x + 80, min(right_x, page.rect.width - margin))
        start_point = self._clamp_start_point(page, fitz.Point(left_x, start_y), resolved_fontsize)
        overflow = self._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=start_point,
            text=text,
            fontsize=resolved_fontsize,
            fontname=resolved_fontname,
            color=color,
            avoid_overlay=True,
            line_height_override=resolved_line_height,
            right_limit_x=right_x,
            continuation_x=left_x,
        )
        if overflow:
            self._append_text_to_new_pages(pdf_doc, overflow, resolved_fontsize, resolved_fontname, color)

    def _append_text_to_new_pages(
        self,
        pdf_doc: fitz.Document,
        text: str,
        fontsize: float,
        fontname: str,
        color: tuple[float, float, float],
    ) -> None:
        if not text.strip():
            return

        margin = 36.0
        page = pdf_doc.new_page()
        overflow = self._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=fitz.Point(margin, margin + self._line_height(fontsize)),
            text=text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
        )
        if overflow:
            self._append_text_to_new_pages(pdf_doc, overflow, fontsize, fontname, color)

    @staticmethod
    def _resolve_non_overlapping_y(
        occupied_rects: list[fitz.Rect],
        x: float,
        y: float,
        line: str,
        fontsize: float,
        fontname: str,
        line_height: float,
        bottom_limit: float,
    ) -> float:
        line_width = fitz.get_text_length(line, fontname=fontname, fontsize=fontsize)
        candidate_y = y
        max_iterations = 200
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            candidate = fitz.Rect(
                x,
                candidate_y - line_height * 0.9,
                x + line_width,
                candidate_y + line_height * 0.2,
            )
            overlaps = [rect for rect in occupied_rects if rect.intersects(candidate)]
            if not overlaps:
                return candidate_y

            # Push the baseline down by the height needed to clear the obstacle
            # Text box starts at y - 0.9h. So new_y - 0.9h >= rect.y1
            candidate_y = max(rect.y1 for rect in overlaps) + (line_height * 0.9)
            if candidate_y > bottom_limit:
                return candidate_y

        return candidate_y

    def _append_text_to_page_end(
        self,
        pdf_doc: fitz.Document,
        page_number: int,
        text: str,
        fontsize: float | None,
        fontname: str | None,
        color: tuple[float, float, float],
    ) -> None:
        margin = 36.0
        page_index = max(0, min(page_number - 1, len(pdf_doc) - 1))
        page = pdf_doc[page_index]
        style = self._infer_page_text_style(page)
        resolved_fontsize = float(style["fontsize"]) if style and fontsize is None else float(fontsize or 11.0)
        resolved_fontname = str(style["fontname"]) if style and not fontname else (fontname or "helv")
        resolved_line_height = float(style["line_height"]) if style else self._line_height(resolved_fontsize)
        left_x = float(style["left_x"]) if style else margin
        right_x = float(style["right_x"]) if style else page.rect.width - margin

        words = page.get_text("words")

        if words:
            last_bottom = max(float(w[3]) for w in words)
            # Add a gap after existing content that matches the inferred vertical rhythm
            start_y = last_bottom + (resolved_line_height * 1.5)
        else:
            start_y = margin + resolved_line_height

        bottom_limit = page.rect.height - margin
        lines_fit = int(max(0.0, (bottom_limit - start_y)) / max(1.0, resolved_line_height))
        if lines_fit < 3 and words:
            page = pdf_doc.new_page()
            style_new_page = self._infer_page_text_style(page)
            if style_new_page:
                left_x = float(style_new_page["left_x"])
                right_x = float(style_new_page["right_x"])
            start_y = margin + resolved_line_height

        left_x = max(margin, min(left_x, page.rect.width - margin - 80))
        right_x = max(left_x + 80, min(right_x, page.rect.width - margin))

        start_point = self._clamp_start_point(page, fitz.Point(left_x, start_y), resolved_fontsize)
        overflow = self._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=start_point,
            text=text,
            fontsize=resolved_fontsize,
            fontname=resolved_fontname,
            color=color,
            avoid_overlay=True,
            line_height_override=resolved_line_height,
            right_limit_x=right_x,
            continuation_x=left_x,
        )
        if overflow:
            self._append_text_to_new_pages(pdf_doc, overflow, resolved_fontsize, resolved_fontname, color)

    @staticmethod
    def _first_non_empty_string(*values: Any) -> str:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _clamp_start_point(page: fitz.Page, point: fitz.Point, fontsize: float) -> fitz.Point:
        margin = 36.0
        min_width = 80.0
        min_x = margin
        max_x = max(min_x, page.rect.width - margin - min_width)
        min_y = margin + ToolExecutor._line_height(fontsize)
        max_y = max(min_y, page.rect.height - margin)
        x = min(max(point.x, min_x), max_x)
        y = min(max(point.y, min_y), max_y)
        return fitz.Point(x, y)

    @staticmethod
    def _find_anchor_rect(
        pdf_doc: fitz.Document,
        anchor_text: str,
        preferred_page_number: int | None = None,
    ) -> tuple[fitz.Page, fitz.Rect] | None:
        if not anchor_text.strip():
            return None

        if preferred_page_number and 1 <= preferred_page_number <= len(pdf_doc):
            page = pdf_doc[preferred_page_number - 1]
            rects = page.search_for(anchor_text)
            if rects:
                return (page, rects[0])

        for page in pdf_doc:
            rects = page.search_for(anchor_text)
            if rects:
                return (page, rects[0])

        return None

    @staticmethod
    def _find_anchor_line(
        pdf_doc: fitz.Document,
        anchor_text: str,
        preferred_page_number: int | None = None,
    ) -> tuple[fitz.Page, fitz.Rect, float] | None:
        token = anchor_text.strip().lower()
        if not token:
            return None

        pages_to_scan: list[fitz.Page] = []
        if preferred_page_number and 1 <= preferred_page_number <= len(pdf_doc):
            pages_to_scan.append(pdf_doc[preferred_page_number - 1])
        pages_to_scan.extend(page for page in pdf_doc if page not in pages_to_scan)

        for page in pages_to_scan:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue

                    line_text = " ".join(str(span.get("text", "")) for span in spans).strip().lower()
                    if token not in line_text:
                        continue

                    bbox = line.get("bbox")
                    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                        continue

                    line_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                    span_bottoms = []
                    for span in spans:
                        span_bbox = span.get("bbox")
                        if isinstance(span_bbox, (list, tuple)) and len(span_bbox) == 4:
                            span_bottoms.append(float(span_bbox[3]))
                    baseline_y = (max(span_bottoms) - 1.0) if span_bottoms else (line_rect.y1 - 1.0)
                    return (page, line_rect, baseline_y)

        return None

    def execute(self, tool_name: str, args: dict[str, Any]) -> ToolExecutionResult:
        document_id = str(args.get("document_id", ""))
        source_asset_id = str(args.get("source_asset_id", ""))

        if tool_name == "extract_text":
            pdf_doc = self._load_doc(source_asset_id)
            scope = args.get("scope", "all")
            if scope == "page" and args.get("page_number") is not None:
                page_number = max(1, int(args["page_number"]))
                if page_number > len(pdf_doc):
                    text = ""
                else:
                    text = pdf_doc[page_number - 1].get_text()
            else:
                text = "\n".join(page.get_text() for page in pdf_doc)

            return ToolExecutionResult(
                {
                    "tool": tool_name,
                    "status": "success",
                    "success": True,
                    "output": {"text": text},
                }
            )

        pdf_doc = self._load_doc(source_asset_id)
        changed = 0

        if tool_name == "replace_text":
            changed = self._replace_text(pdf_doc, str(args.get("old_text", "")), str(args.get("new_text", "")))
        elif tool_name == "search_replace":
            changed = self._replace_text(pdf_doc, str(args.get("search", "")), str(args.get("replace", "")))
        elif tool_name == "add_text":
            text = self._first_non_empty_string(args.get("text"), args.get("new_text"), args.get("content"), args.get("value"))
            if not text:
                return ToolExecutionResult(
                    {
                        "tool": tool_name,
                        "status": "failed",
                        "success": False,
                        "output": {},
                        "error": "add_text requires non-empty text",
                    }
                )

            raw_font_size = args.get("font_size")
            fontsize = float(raw_font_size) if raw_font_size is not None else None
            color = self._color_tuple(args.get("color"))
            fontname = self._first_non_empty_string(args.get("font_family")) or None
            position = self._first_non_empty_string(args.get("position"), args.get("placement")).lower()
            command = self._first_non_empty_string(args.get("command"), args.get("instruction")).lower()
            anchor_text = self._first_non_empty_string(
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
                self._append_text_to_page_end(
                    pdf_doc=pdf_doc,
                    page_number=page_number,
                    text=text,
                    fontsize=fontsize,
                    fontname=fontname,
                    color=color,
                )
                inserted = True

            if anchor_text:
                anchor = self._find_anchor_rect(pdf_doc, anchor_text=anchor_text, preferred_page_number=page_number or None)
                if anchor:
                    page, rect = anchor
                    inline_requested = any(
                        key in f"{position} {command}"
                        for key in ("next", "right", "beside", "same line", "inline", "on same line")
                    )

                    if inline_requested:
                        line_anchor = self._find_anchor_line(
                            pdf_doc,
                            anchor_text=anchor_text,
                            preferred_page_number=page_number or None,
                        )
                        if line_anchor:
                            page, line_rect, baseline_y = line_anchor
                            raw_x = line_rect.x1 + 8
                            raw_y = baseline_y
                        else:
                            raw_x = rect.x1 + 8
                            raw_y = rect.y1 - 1

                        right_limit = page.rect.width - 36 - 80
                        if raw_x > right_limit:
                            raw_point = fitz.Point(36, raw_y + self._line_height(fontsize))
                        else:
                            raw_point = fitz.Point(raw_x, raw_y)
                        start_point = fitz.Point(
                            min(max(raw_point.x, 36), max(36.0, page.rect.width - 36 - 80)),
                            min(max(raw_point.y, 36), page.rect.height - 36),
                        )
                        overflow = self._insert_wrapped_text(
                            pdf_doc=pdf_doc,
                            start_page=page,
                            start_point=start_point,
                            text=text,
                            fontsize=fontsize or 11.0,
                            fontname=fontname or "helv",
                            color=color,
                            avoid_overlay=False,
                            respect_start_y=True,
                        )
                        if overflow:
                            self._append_text_to_new_pages(
                                pdf_doc=pdf_doc,
                                text=overflow,
                                fontsize=fontsize or 11.0,
                                fontname=fontname or "helv",
                                color=color,
                            )
                        inserted = True
                    elif "next" in position or "right" in position or "beside" in position:
                        raw_point = fitz.Point(rect.x1 + 8, rect.y1)
                        start_point = self._clamp_start_point(page, raw_point, fontsize or 11.0)
                        overflow = self._insert_wrapped_text(
                            pdf_doc=pdf_doc,
                            start_page=page,
                            start_point=start_point,
                            text=text,
                            fontsize=fontsize or 11.0,
                            fontname=fontname or "helv",
                            color=color,
                            avoid_overlay=True,
                        )
                        if overflow:
                            self._append_text_to_new_pages(
                                pdf_doc=pdf_doc,
                                text=overflow,
                                fontsize=fontsize or 11.0,
                                fontname=fontname or "helv",
                                color=color,
                            )
                        inserted = True
                    elif "above" in position:
                        raw_point = fitz.Point(rect.x0, rect.y0 - 4)
                        start_point = self._clamp_start_point(page, raw_point, fontsize or 11.0)
                        overflow = self._insert_wrapped_text(
                            pdf_doc=pdf_doc,
                            start_page=page,
                            start_point=start_point,
                            text=text,
                            fontsize=fontsize or 11.0,
                            fontname=fontname or "helv",
                            color=color,
                            avoid_overlay=True,
                        )
                        if overflow:
                            self._append_text_to_new_pages(
                                pdf_doc=pdf_doc,
                                text=overflow,
                                fontsize=fontsize or 11.0,
                                fontname=fontname or "helv",
                                color=color,
                            )
                        inserted = True
                    else:
                        self._insert_paragraph_below_anchor(
                            pdf_doc=pdf_doc,
                            page=page,
                            anchor_rect=rect,
                            text=text,
                            fontsize=fontsize,
                            fontname=fontname,
                            color=color,
                        )
                        inserted = True

            if not inserted and page_number > 0 and page_number <= len(pdf_doc) and has_coordinates:
                page = pdf_doc[page_number - 1]
                raw_point = fitz.Point(float(args.get("x", 72)), float(args.get("y", 72)))
                start_point = self._clamp_start_point(page, raw_point, fontsize or 11.0)
                overflow = self._insert_wrapped_text(
                    pdf_doc=pdf_doc,
                    start_page=page,
                    start_point=start_point,
                    text=text,
                    fontsize=fontsize or 11.0,
                    fontname=fontname or "helv",
                    color=color,
                    avoid_overlay=True,
                )
                if overflow:
                    self._append_text_to_new_pages(
                        pdf_doc=pdf_doc,
                        text=overflow,
                        fontsize=fontsize or 11.0,
                        fontname=fontname or "helv",
                        color=color,
                    )
                inserted = True

            if not inserted:
                self._append_text_to_page_end(
                    pdf_doc=pdf_doc,
                    page_number=max(1, len(pdf_doc)),
                    text=text,
                    fontsize=fontsize,
                    fontname=fontname,
                    color=color,
                )
            changed = 1
        elif tool_name in {"change_font_size", "change_font_type", "change_font_color", "set_text_style", "convert_case"}:
            target_text = str(args.get("target_text", ""))
            transformed = target_text
            if tool_name == "convert_case":
                case_mode = str(args.get("case", "lower"))
                if case_mode == "upper":
                    transformed = target_text.upper()
                elif case_mode == "capitalize":
                    transformed = target_text.capitalize()
                else:
                    transformed = target_text.lower()

            raw_font_size = args.get("font_size")
            inferred_font_size = None
            if tool_name == "change_font_size" and raw_font_size is None:
                inferred_font_size = self._infer_font_size_from_reference(
                    pdf_doc,
                    str(args.get("reference_text", "")),
                )
            font_size = float(raw_font_size if raw_font_size is not None else (inferred_font_size or 11))
            font_name = str(args.get("font_family", "helv"))
            color = self._color_tuple(str(args.get("color", "black")))

            if tool_name == "change_font_size" and raw_font_size is None and inferred_font_size is None:
                return ToolExecutionResult(
                    {
                        "tool": tool_name,
                        "status": "failed",
                        "success": False,
                        "output": {},
                        "error": "Missing 'font_size'. Provide a number or reference_text (e.g. same as word X).",
                    }
                )

            if tool_name == "set_text_style":
                style = str(args.get("style", ""))
                if style == "bold":
                    font_name = "hebo"
                elif style == "italic":
                    font_name = "heit"

            changed = self._replace_text(
                pdf_doc,
                old_text=target_text,
                new_text=transformed,
                fontsize=font_size,
                fontname=font_name,
                color=color,
                preserve_line_baseline=tool_name in {"change_font_size", "set_text_style", "change_font_type", "change_font_color"},
            )
        elif tool_name in {"highlight_text", "underline_text", "strikethrough_text"}:
            target_text = str(args.get("target_text", ""))
            for page in pdf_doc:
                rects = page.search_for(target_text)
                for rect in rects:
                    if tool_name == "highlight_text":
                        annot = page.add_highlight_annot(rect)
                        annot.set_colors(stroke=self._color_tuple(str(args.get("color", "yellow"))))
                        annot.update()
                    elif tool_name == "underline_text":
                        page.add_underline_annot(rect)
                    else:
                        page.add_strikeout_annot(rect)
                    changed += 1
        else:
            return ToolExecutionResult(
                {
                    "tool": tool_name,
                    "status": "failed",
                    "success": False,
                    "output": {},
                    "error": f"Unsupported tool: {tool_name}",
                }
            )

        version_asset = self._save_new_version(document_id=document_id, pdf_doc=pdf_doc)
        preview_manifest = self._build_preview_manifest(pdf_doc)
        return ToolExecutionResult(
            {
                "tool": tool_name,
                "status": "success",
                "success": True,
                "output": {
                    "changes": changed,
                    "asset_id": version_asset.get("asset_id"),
                    "url": version_asset.get("url"),
                    "preview_manifest": preview_manifest,
                },
            }
        )
