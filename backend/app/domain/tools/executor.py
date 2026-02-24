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

    def _search_for_text_robust(self, page: fitz.Page, text: str) -> list[fitz.Rect]:
        if not text.strip():
            return []
        # Path 1: Exact
        rects = page.search_for(text)
        if rects:
            return rects
        # Path 2: Line-break insensitive
        if "\n" in text:
            rects = page.search_for(text.replace("\n", " "))
            if rects:
                return rects
        # Path 3: Normalized whitespace
        normalized = " ".join(text.split())
        if normalized != text:
            rects = page.search_for(normalized)
            if rects:
                return rects
        return []

    def _collect_and_clear_page_after(self, page: fitz.Page, y_threshold: float) -> str:
        """Collects all text below y_threshold and redacts it from the page."""
        blocks = page.get_text("blocks")
        # Blocks format: (x0, y0, x1, y1, "text", block_no, block_type)
        # We look for text blocks (type 0) whose top (y0) is below the threshold
        remaining_blocks = [b for b in blocks if b[1] >= y_threshold - 2 and b[6] == 0]
        if not remaining_blocks:
            return ""
        
        # Sort by vertical position
        remaining_blocks.sort(key=lambda b: b[1])
        captured_text = "\n\n".join(b[4].strip() for b in remaining_blocks)
        
        # Redact the area
        for b in remaining_blocks:
            page.add_redact_annot(b[:4], fill=(1, 1, 1))
        page.apply_redactions()
        return captured_text

    def _capture_rest_of_document_data(self, pdf_doc: fitz.Document, start_page_idx: int, y_threshold: float, x_threshold: float | None = None) -> list[dict[str, Any]]:
        """Captures structured text blocks and tails for continuous reflow."""
        captured_blocks: list[dict[str, Any]] = []
        
        def process_page(page: fitz.Page, y_min: float, x_min_on_first_line: float | None = None):
            text_dict = page.get_text("dict")
            blocks = sorted(text_dict.get("blocks", []), key=lambda b: b["bbox"][1])
            
            for block in blocks:
                if block.get("type") != 0: continue
                bbox = block.get("bbox")
                
                # Case 1: Strictly above the line of interest
                if bbox[3] < y_min - 2: continue
                
                # Case 2: Intersecting the line (The block containing our target)
                # This mode handles both mid-line tails and full vertical splits.
                if bbox[1] < y_min + 2 and bbox[3] > y_min - 2:
                    tail_text_parts = []
                    is_actual_tail = False
                    for line in block.get("lines", []):
                        lbox = line.get("bbox")
                        
                        # 1. The specific split line (intersects y_min)
                        if lbox[1] < y_min + 2 and lbox[3] > y_min - 2:
                            if x_min_on_first_line is not None:
                                # Mid-sentence split: capture only text to the RIGHT of x_min
                                spans_after = [s for s in line.get("spans", []) if s["bbox"][0] > x_min_on_first_line + 1.0]
                                if spans_after:
                                    tail_text_parts.append("".join(s.get("text", "") for s in spans_after))
                                    is_actual_tail = True
                                    for s in spans_after:
                                        page.add_redact_annot(s["bbox"], fill=(1, 1, 1))
                            else:
                                # Vertical split: capture the ENTIRE line if it's below or at y_min
                                line_text = "".join(s.get("text", "") for s in line.get("spans", []))
                                if line_text:
                                    tail_text_parts.append(line_text)
                                    page.add_redact_annot(lbox, fill=(1, 1, 1))
                        
                        # 2. Lines strictly BELOW the split line within the same block
                        elif lbox[1] >= y_min + 2:
                            line_text = "".join(s.get("text", "") for s in line.get("spans", []))
                            if line_text:
                                # Ensure it starts on a new line relative to the tail/split-line
                                prefix = "\n" if tail_text_parts else ""
                                tail_text_parts.append(prefix + line_text)
                                page.add_redact_annot(lbox, fill=(1, 1, 1))
                    
                    combined_tail = "".join(tail_text_parts).strip()
                    if combined_tail:
                        first_span = block["lines"][0]["spans"][0] if block["lines"] else None
                        captured_blocks.append({
                            "text": combined_tail,
                            "x0": float(bbox[0]),
                            "x1": float(bbox[2]),
                            "fontsize": float(first_span["size"]) if first_span else 11.0,
                            "fontname": self._map_span_font_to_base14(str(first_span["font"])) if first_span else "helv",
                            "color": self._color_tuple_from_int(first_span["color"]) if first_span else (0,0,0),
                            "continuation_x": float(block["lines"][1]["bbox"][0]) if len(block["lines"]) > 1 else float(bbox[0]),
                            "is_tail": is_actual_tail
                        })
                    continue

                # Case 3: Strictly below the line/threshold
                if bbox[1] < y_min - 2: continue
                
                block_text = page.get_text("text", clip=bbox).strip()
                if not block_text: continue
                
                # Mark for removal
                page.add_redact_annot(bbox, fill=(1, 1, 1))

                # Infer continuation_x (base margin) from second line if available
                # This preserves first-line indents correctly.
                cont_x = float(bbox[0])
                if len(block.get("lines", [])) > 1:
                    cont_x = float(block["lines"][1]["bbox"][0])

                first_span = [s for line in block.get("lines", []) for s in line.get("spans", [])][0]
                captured_blocks.append({
                    "text": block_text,
                    "x0": float(bbox[0]),
                    "x1": float(bbox[2]),
                    "fontsize": float(first_span["size"]) if first_span else 11.0,
                    "fontname": self._map_span_font_to_base14(str(first_span["font"])) if first_span else "helv",
                    "color": self._color_tuple_from_int(first_span["color"]) if first_span else (0,0,0),
                    "continuation_x": cont_x
                })

            # ACTUALLY APPLY REDACTIONS TO CLEAR THE PAGE
            page.apply_redactions(images=0, graphics=0)
            
        # Process starting page
        process_page(pdf_doc[start_page_idx], y_threshold, x_threshold)

        # Process subsequent pages
        for p_idx in range(start_page_idx + 1, len(pdf_doc)):
            process_page(pdf_doc[p_idx], 0)
            
        return captured_blocks

    @staticmethod
    def _color_tuple_from_int(color_int: int) -> tuple[float, float, float]:
        # Convert fitz integer color to RGB tuple
        return (
            ((color_int >> 16) & 0xFF) / 255.0,
            ((color_int >> 8) & 0xFF) / 255.0,
            (color_int & 0xFF) / 255.0
        )

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
        p = 0
        while p < len(pdf_doc):
            page = pdf_doc[p]
            rects = self._search_for_text_robust(page, old_text)
            if not rects:
                p += 1
                continue
            
            # Process the first rect. Shifting content will invalidate subsequent rects.
            rect = rects[0]
            
            # 1. Capture rest of document using structured data
            # Mid-line replacement: capture only text to the right of the anchor's end-X on the first line.
            captured_blocks = self._capture_rest_of_document_data(pdf_doc, p, rect.y1, rect.x1)
            
            # 2. Redact target
            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()
            
            # 3. Insert new text
            raw_new_text = new_text.strip()
            line_info = self._find_line_for_rect(page, rect)
            line_h = self._line_height(fontsize)

            if line_info:
                line_rect, baseline_y = line_info
                # Start exactly where the old text was
                start_point = fitz.Point(rect.x0, baseline_y)
                respect_start_y = True
                
                # Base margin for wrapped lines should be the block's margin,
                # not necessarily the current line's x0 (which might be an indent).
                continuation_x = line_rect.x0
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    if fitz.Rect(block["bbox"]).intersects(rect):
                        if len(block.get("lines", [])) > 1:
                            continuation_x = float(block["lines"][1]["bbox"][0])
                        else:
                            continuation_x = float(block["bbox"][0])
                        break
            else:
                baseline_y = rect.y1 - 1 if preserve_line_baseline else max(36, rect.y0 + fontsize)
                start_point = fitz.Point(rect.x0, baseline_y)
                respect_start_y = preserve_line_baseline
                continuation_x = rect.x0

            res = self._insert_wrapped_text_ext(
                pdf_doc=pdf_doc,
                start_page=page,
                start_point=start_point,
                text=new_text,
                fontsize=fontsize,
                fontname=fontname,
                color=color,
                avoid_overlay=False,
                respect_start_y=respect_start_y,
                continuation_x=continuation_x
            )
            
            # 4. Progressively reflow all captured structured blocks
            current_page = res.final_page
            
            for i, block in enumerate(captured_blocks):
                block_line_h = self._line_height(block["fontsize"])
                
                # Logic: Only a captured 'tail' (mid-line continuation) can follow on the SAME line.
                # Everything else MUST start a new paragraph.
                if i == 0 and block.get("is_tail"):
                    start_pt = res.final_point
                    resp_y = True
                    # If we are continuing on the SAME line, add a joining space
                    if not res.ended_with_newline:
                        if not new_text.endswith((' ', '\n')) and not block["text"].startswith((' ', '\n')):
                            block["text"] = " " + block["text"]
                else:
                    # Subsequent blocks or non-tails start with a paragraph gap
                    start_pt = fitz.Point(block["x0"], res.final_point.y + (block_line_h * 1.5))
                    resp_y = True

                block_res = self._insert_wrapped_text_ext(
                    pdf_doc=pdf_doc,
                    start_page=current_page,
                    start_point=start_pt,
                    text=block["text"],
                    fontsize=block["fontsize"],
                    fontname=block["fontname"],
                    color=block["color"],
                    avoid_overlay=False,
                    respect_start_y=resp_y,
                    line_height_override=block_line_h,
                    right_limit_x=block["x1"],
                    continuation_x=block.get("continuation_x", block["x0"])
                )
                current_page = block_res.final_page
                res = block_res # Update reference for next gap
            
            replacements += 1
            continue 
            
        return replacements

    @staticmethod
    def _line_height(fontsize: float) -> float:
        return max(12.0, fontsize * 1.35)

    @staticmethod
    def _wrap_text_to_width(text: str, fontname: str, fontsize: float, max_width: float) -> list[str]:
        # Split by paragraphs first to preserve structure
        paragraphs = text.split('\n')
        final_lines: list[str] = []
        
        for p in paragraphs:
            p_clean = p.strip()
            if not p_clean:
                final_lines.append("") # Empty line placeholder for paragraph gap
                continue
                
            words = p_clean.split()
            if not words:
                continue
                
            current_line = words[0]
            for word in words[1:]:
                candidate = f"{current_line} {word}"
                if fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) <= max_width:
                    current_line = candidate
                else:
                    final_lines.append(current_line)
                    current_line = word
            final_lines.append(current_line)
            
        return final_lines

    class WrappedTextResult:
        def __init__(self, overflow: str, final_page: fitz.Page, final_point: fitz.Point, ended_with_newline: bool = False):
            self.overflow = overflow
            self.final_page = final_page
            self.final_point = final_point
            self.ended_with_newline = ended_with_newline

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
        # Wrapper for backward compatibility
        result = self._insert_wrapped_text_ext(
            pdf_doc, start_page, start_point, text, fontsize, fontname, color,
            avoid_overlay, respect_start_y, line_height_override, right_limit_x, continuation_x
        )
        return result.overflow

    def _insert_wrapped_text_ext(
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
    ) -> WrappedTextResult:
        margin = 36.0
        page = start_page
        line_height = line_height_override if line_height_override is not None else self._line_height(fontsize)

        y = start_point.y if respect_start_y else max(start_point.y, margin + line_height)
        curr_x = start_point.x
        
        # CONTINUOUS STREAM: Avoid forcing a newline if starting mid-sentence
        respecting_initial_x = respect_start_y and curr_x > margin + 1.0
        
        paragraphs = text.split('\n')
        last_x, last_y = curr_x, y
        
        ended_with_newline = text.endswith('\n') or (len(paragraphs) > 1 and not paragraphs[-1].strip())
        
        for p_idx, p_text in enumerate(paragraphs):
            p_clean = p_text.strip()
            if not p_clean:
                # Actual empty line / paragraph gap
                y += line_height * 0.7
                curr_x = continuation_x if continuation_x is not None else margin
                last_y = y
                last_x = curr_x
                continue
            
            words = p_clean.split()
            current_line_words = []
            
            for word in words:
                while True:
                    bottom_limit = page.rect.height - margin
                    if y > bottom_limit:
                        next_idx = page.number + 1
                        if next_idx < len(pdf_doc):
                            page = pdf_doc[next_idx]
                        else:
                            page = pdf_doc.new_page()
                        y = margin + line_height
                        curr_x = continuation_x if continuation_x is not None else margin
                    
                    eff_right = min(page.rect.width - margin, right_limit_x) if right_limit_x is not None else page.rect.width - margin
                    max_w = max(50.0, eff_right - curr_x)
                    
                    test_line = " ".join(current_line_words + [word])
                    if fitz.get_text_length(test_line, fontname=fontname, fontsize=fontsize) <= max_w:
                        current_line_words.append(word)
                        break
                    else:
                        # Flush current line
                        if current_line_words:
                            line_str = " ".join(current_line_words)
                            page.insert_text((curr_x, y), line_str, fontsize=fontsize, fontname=fontname, color=color)
                            last_y = y
                            last_x = curr_x + fitz.get_text_length(line_str, fontname=fontname, fontsize=fontsize)
                        
                        y += line_height
                        curr_x = continuation_x if continuation_x is not None else margin
                        current_line_words = []
                        # Continue to retry 'word' on the new line
            
            # Flush final line of paragraph
            if current_line_words:
                line_str = " ".join(current_line_words)
                page.insert_text((curr_x, y), line_str, fontsize=fontsize, fontname=fontname, color=color)
                last_y = y
                last_x = curr_x + fitz.get_text_length(line_str, fontname=fontname, fontsize=fontsize)
                
            # Move to next line for start of next paragraph
            if p_idx < len(paragraphs) - 1:
                y += line_height
                curr_x = continuation_x if continuation_x is not None else margin
                last_y = y
                last_x = curr_x

        return self.WrappedTextResult(
            overflow="",
            final_page=page,
            final_point=fitz.Point(last_x, last_y),
            ended_with_newline=ended_with_newline
        )

    @staticmethod
    def _infer_style_from_reference(pdf_doc: fitz.Document, reference_text: str) -> dict:
        """Extracts fontname, fontsize, and color from the first match of reference_text."""
        token = reference_text.strip()
        if not token:
            return {}

        lower_token = token.lower()
        for page in pdf_doc:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = str(span.get("text", ""))
                        if lower_token in span_text.lower():
                            return {
                                "fontsize": float(span.get("size", 11.0)),
                                "fontname": str(span.get("font", "helv")),
                                "color": span.get("color", (0, 0, 0))
                            }
        return {}

    @staticmethod
    def _infer_font_size_from_reference(pdf_doc: fitz.Document, reference_text: str) -> float | None:

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

    def _get_block_geometry(self, page: fitz.Page, rect: fitz.Rect) -> tuple[float, float, fitz.Rect | None]:
        """Returns (first_line_x0, block_x0, block_rect) for the block containing the rect."""
        text_dict = page.get_text("dict")
        style = self._infer_page_text_style(page)
        global_margin = float(style["left_x"]) if style else 72.0
        
        # Default to global margin
        best_first_x = global_margin
        best_block_x = global_margin

        for block in text_dict.get("blocks", []):
            bbox = block.get("bbox")
            block_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            # Tolerance Check: Use intersection for higher reliability
            if block_rect.intersects(rect) or (
                bbox[0] <= rect.x0 + 5 and bbox[1] <= rect.y0 + 5 and 
                bbox[2] >= rect.x1 - 5 and bbox[3] >= rect.y1 - 5
            ):
                lines = block.get("lines", [])
                if lines:
                    det_first_x = float(lines[0]["bbox"][0])
                    det_block_x = float(bbox[0])
                    
                    # SANITY CHECK: Fall back if detected indent is extreme
                    if abs(det_block_x - global_margin) > 150:
                        det_block_x = global_margin
                    if abs(det_first_x - global_margin) > 150:
                        det_first_x = global_margin
                        
                    return (det_first_x, det_block_x, block_rect)
                return (float(bbox[0]), float(bbox[0]), block_rect)
        return (best_first_x, best_block_x, None)

    def _find_line_for_rect(
        self, page: fitz.Page, rect: fitz.Rect
    ) -> tuple[fitz.Rect, float] | None:
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                bbox = line.get("bbox")
                line_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                # Intersect or contain
                if not (line_rect.y0 <= rect.y1 and line_rect.y1 >= rect.y0):
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
        
        # INHERIT GEOMETRY: Look at the paragraph block containing the anchor
        first_line_x, block_x, block_rect = self._get_block_geometry(page, anchor_rect)
        left_x = first_line_x
        right_x = float(style["right_x"]) if style else page.rect.width - margin

        # SPLIT POINT: For "Below" commands, we should ALWAYS split below the ENTIRE block 
        # to avoid dissecting the paragraph the user is pointing to.
        if block_rect:
            anchor_line_bottom = block_rect.y1
        else:
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

        # 1. Capture structured blocks
        # PURE VERTICAL SPLIT: Set x_threshold=None to capture full lines below the anchor.
        # Add a strict safety offset (+4.0) to ensure we don't accidentally capture the last line of the anchor itself.
        captured_blocks = self._capture_rest_of_document_data(pdf_doc, page.number, anchor_line_bottom + 4.0, None)

        left_x = max(margin, min(left_x, page.rect.width - margin - 80))
        right_x = max(left_x + 80, min(right_x, page.rect.width - margin))
        # 2. Insert new paragraph (Inherit indentation from anchor)
        # Use anchor's x0 as the margin/continuation_x to preserve document layout
        res = self._insert_wrapped_text_ext(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=self._clamp_start_point(page, fitz.Point(left_x, start_y), resolved_fontsize),
            text=text,
            fontsize=resolved_fontsize,
            fontname=resolved_fontname,
            color=color,
            avoid_overlay=False,
            respect_start_y=True,
            line_height_override=resolved_line_height,
            right_limit_x=right_x,
            continuation_x=block_x, # Wrap subsequent lines to block margin
        )
        
        # Reflow subsequent blocks
        curr_pg = res.final_page
        for i, block in enumerate(captured_blocks):
            block_line_h = self._line_height(block["fontsize"])
            
            # TAIL STITCHING: If it's a tail of the current paragraph, 
            # insert it with NO gap (spacing=0).
            spacing = 0 if block.get("is_tail") else (block_line_h * 1.5)
            
            block_res = self._insert_wrapped_text_ext(
                pdf_doc=pdf_doc,
                start_page=curr_pg,
                start_point=fitz.Point(block["x0"], res.final_point.y + spacing),
                text=block["text"],
                fontsize=block["fontsize"],
                fontname=block["fontname"],
                color=block["color"],
                avoid_overlay=False,
                respect_start_y=True,
                line_height_override=block_line_h,
                right_limit_x=block["x1"],
                continuation_x=block.get("continuation_x", block["x0"])
            )
            curr_pg = block_res.final_page
            res = block_res
        inserted = True

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

    def _find_anchor_rect(
        self,
        pdf_doc: fitz.Document,
        anchor_text: str,
        preferred_page_number: int | None = None,
        prefer_last: bool = False,
    ) -> tuple[fitz.Page, list[fitz.Rect]] | None:
        if not anchor_text.strip():
            return None

        # 1. CLEANING: Trim common leading fluff that users might add
        clean_text = anchor_text.strip()
        
        # 2. MULTI-PASS SEARCH STRATEGY
        # We try the full anchor first, then progressively smaller chunks.
        words = clean_text.split()
        
        # Create a list of candidates: full, start-clipped, and end-clipped
        search_candidates = [
            " ".join(words),                     # Full 15-word window
            " ".join(words[1:]) if len(words) > 1 else None, # Skip leading "this/is"
            " ".join(words[:8]) if len(words) > 8 else None, # First 8 words
            " ".join(words[:4]) if len(words) > 4 else None, # First 4 words
            " ".join(words[-6:]) if len(words) > 6 else None, # Last 6 words
        ]
        
        # Deduplicate candidates while preserving order
        unique_candidates = []
        for c in search_candidates:
            if c and c not in unique_candidates:
                unique_candidates.append(c)

        for candidate in unique_candidates:
            # Scan pages with directional preference
            pages_to_scan = list(pdf_doc)
            if prefer_last:
                pages_to_scan = list(reversed(pages_to_scan))

            for page in pages_to_scan:
                rects = self._search_for_text_robust(page, candidate)
                if rects:
                    # PyMuPDF returns a list of rects. For a single match covering N lines,
                    # it returns N rects. We treat the whole list as the match for our specific candidates.
                    return (page, rects)

        return None

    def _find_anchor_line(
        self,
        pdf_doc: fitz.Document,
        anchor_text: str,
        preferred_page_number: int | None = None,
        prefer_last: bool = False,
    ) -> tuple[fitz.Page, fitz.Rect, float] | None:
        if not anchor_text.strip():
            return None

        words = anchor_text.strip().split()
        search_candidates = [
            " ".join(words).lower(),
            " ".join(words[1:]).lower() if len(words) > 1 else None,
            " ".join(words[:4]).lower() if len(words) > 4 else None,
            " ".join(words[-4:]).lower() if len(words) > 4 else None,
        ]
        
        unique_candidates = []
        for c in search_candidates:
            if c and c not in unique_candidates:
                unique_candidates.append(c)

        for token in unique_candidates:
            # Scan pages with directional preference
            pages_to_scan = list(pdf_doc)
            if prefer_last:
                pages_to_scan = list(reversed(pages_to_scan))

            # Re-prioritize preferred page if not reverse-searching
            if not prefer_last and preferred_page_number and 1 <= preferred_page_number <= len(pdf_doc):
                pref_page = pdf_doc[preferred_page_number - 1]
                if pref_page in pages_to_scan:
                    pages_to_scan.remove(pref_page)
                    pages_to_scan.insert(0, pref_page)

            for page in pages_to_scan:
                text_dict = page.get_text("dict")
                blocks = text_dict.get("blocks", [])
                if prefer_last:
                    blocks = sorted(blocks, key=lambda b: b["bbox"][1], reverse=True)
                else:
                    blocks = sorted(blocks, key=lambda b: b["bbox"][1])

                for block in blocks:
                    lines = block.get("lines", [])
                    if prefer_last:
                        lines = list(reversed(lines))

                    for line in lines:
                        spans = line.get("spans", [])
                        if not spans: continue

                        line_text = " ".join(str(span.get("text", "")) for span in spans).strip().lower()
                        if token in line_text:
                            bbox = line.get("bbox")
                            line_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                            span_bottoms = [float(s["bbox"][3]) for s in spans if "bbox" in s]
                            baseline_y = (max(span_bottoms) - 1.0) if span_bottoms else (line_rect.y1 - 1.0)
                            return (page, line_rect, baseline_y)

        return None

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

        if tool_name in {"replace_text", "search_replace"}:
            old_text = str(args.get("old_text", "") or args.get("search", ""))
            new_text = str(args.get("new_text", "") or args.get("replace", ""))
            
            # Infer style from the text being replaced
            inferred_size = self._infer_font_size_from_reference(pdf_doc, old_text)
            style = self._infer_page_text_style(pdf_doc[0]) # Default style from first page
            
            style_fontsize = style.get("fontsize") if style else 11.0
            style_fontname = style.get("fontname") if style else "helv"
            
            fontsize = float(args.get("font_size") or inferred_size or style_fontsize)
            fontname = str(args.get("font_family") or style_fontname)
            color_raw = args.get("color")
            color = self._color_tuple(str(color_raw)) if color_raw else (0, 0, 0)

            changed = self._replace_text(
                pdf_doc, 
                old_text=old_text, 
                new_text=new_text,
                fontsize=fontsize,
                fontname=fontname,
                color=color
            )
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
                # TRUNCATE ANCHOR: Use a 15-word window to uniquely identify the context.
                search_anchor = " ".join(anchor_text.split()[:15])
                # PREFER LAST: For insertions, prefer the match closest to the bottom of the doc (Academic vs Intro).
                anchor = self._find_anchor_rect(pdf_doc, anchor_text=search_anchor, preferred_page_number=page_number or None, prefer_last=True)
                if anchor:
                    anchor_text = search_anchor
                    page, rects = anchor
                    # Use the last rect for horizontal terminal point, 
                    # use the bounding box of all rects for overall block logic.
                    rect = rects[-1] 
                    full_match_rect = fitz.Rect(rects[0])
                    for r in rects: full_match_rect |= r
                    
                    user_intent = str(args.get("intent", "paragraph")).lower()
                    
                    # Log for debugging dispatcher behavior
                    print(f"[ToolExecutor] Dispatching: Intent='{user_intent}', Position='{position}'")
                    
                    # Dispatch to inline mode if intent is 'text' OR position implies horizontal horizontal flow
                    is_inline = (user_intent == "text") or any(kw in position for kw in ["text", "next to", "beside", "after"])
                    
                    if is_inline:
                        # Inline Append (Same-line reflow)
                        # THE REPLACE CLONE: Redact anchor and re-write (Anchor + Content) for stability.
                        style = self._infer_style_from_reference(pdf_doc, search_anchor)
                        resolved_fontsize = fontsize or style.get("fontsize", 11.0)
                        resolved_fontname = fontname or style.get("fontname", "helv")
                        resolved_color = color or style.get("color", (0, 0, 0))
                        
                        # REDACT ANCHOR: We redact the entire match area to clear the way for the re-write
                        page.add_redact_annot(full_match_rect, fill=(1, 1, 1))
                        page.apply_redactions()
                        
                        line_info = self._find_line_for_rect(page, rects[0])
                        if line_info:
                            line_rect, baseline_y = line_info
                            # Start exactly where the anchor was
                            start_pt = fitz.Point(rects[0].x0, baseline_y)
                        else:
                            start_pt = fitz.Point(rects[0].x0, rects[0].y1 - 1.0)
                        
                        # Join-Space Detection: ensure we don't word-smash
                        content_to_add = text.strip()
                        if not content_to_add.startswith(" ") and not search_anchor.endswith(" "):
                             content_to_add = " " + content_to_add
                        
                        # COMBINED PAYLOAD: The anchor is part of the reflow for perfect alignment
                        full_payload = search_anchor + content_to_add

                        # Infer logical geometry for wrapping relative to the anchor's block
                        _, block_x, block_rect = self._get_block_geometry(page, rects[0])
                        right_limit = block_rect.x1 if block_rect else page.rect.width - 36.0
                        
                        # Capture rest of document starting from the REDACTED anchor's end
                        captured_blocks = self._capture_rest_of_document_data(pdf_doc, page.number, full_match_rect.y1, full_match_rect.x1)
                        
                        res = self._insert_wrapped_text_ext(
                            pdf_doc=pdf_doc,
                            start_page=page,
                            start_point=start_pt,
                            text=full_payload,
                            fontsize=resolved_fontsize,
                            fontname=resolved_fontname,
                            color=resolved_color,
                            respect_start_y=True,
                            right_limit_x=right_limit,
                            continuation_x=block_x
                        )
                        # Reflow subsequent blocks
                        curr_pg = res.final_page
                        prev_res = res
                        for idx, blk in enumerate(captured_blocks):
                            blk_line_h = self._line_height(blk["fontsize"])
                            start_pt = prev_res.final_point if (idx == 0 and blk.get("is_tail")) else fitz.Point(blk["x0"], prev_res.final_point.y + (blk_line_h * 1.5))
                            blk_res = self._insert_wrapped_text_ext(
                                pdf_doc=pdf_doc,
                                start_page=curr_pg,
                                start_point=start_pt,
                                text=blk["text"],
                                fontsize=blk["fontsize"],
                                fontname=blk["fontname"],
                                color=blk["color"],
                                respect_start_y=True,
                                line_height_override=blk_line_h,
                                continuation_x=blk.get("continuation_x", blk["x0"])
                            )
                            curr_pg = blk_res.final_page
                            prev_res = blk_res
                    else:
                        # Full Paragraph Vertical Push
                        self._insert_paragraph_below_anchor(
                            pdf_doc=pdf_doc,
                            page=page,
                            anchor_rect=full_match_rect,
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
