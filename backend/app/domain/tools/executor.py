from typing import Any
import hashlib
import statistics

import fitz

from app.storage.asset_service import AssetService
from app.storage.cloudinary_client import CloudinaryClient
from app.domain.tools.engines import infer_vertical_rhythm, reflow_remaining_blocks
from app.domain.tools.engines import (
    append_text_to_new_pages,
    append_text_to_page_end,
    capture_rest_of_document_data,
    find_all_matches_on_page,
    find_line_for_rect,
    get_block_geometry,
    locate_semantic_anchor,
    insert_paragraph_below_anchor,
    resolve_non_overlapping_y,
)
from app.domain.tools.operations import apply_add_text, apply_annotations, apply_text_style_change, replace_text_with_reflow


class ToolExecutionResult(dict):
    pass


class WrappedTextResult:
    def __init__(self, overflow: str, final_page: fitz.Page, final_point: fitz.Point, ended_with_newline: bool = False):
        self.overflow = overflow
        self.final_page = final_page
        self.final_point = final_point
        self.ended_with_newline = ended_with_newline


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
    def _locate_semantic_anchor(
        self,
        pdf_doc: fitz.Document,
        anchor_text: str,
        preferred_page_number: int | None = None,
        prefer_last: bool = False,
    ) -> dict[str, Any] | None:
        return locate_semantic_anchor(self, pdf_doc, anchor_text, preferred_page_number, prefer_last)

    def _reflow_remaining_blocks(
        self,
        pdf_doc: fitz.Document,
        last_res: WrappedTextResult,
        captured_blocks: list[dict[str, Any]],
        active_lh: float,
        active_pg: float
    ) -> WrappedTextResult:
        return reflow_remaining_blocks(self, pdf_doc, last_res, captured_blocks, active_lh, active_pg)

    def _find_all_matches_on_page(self, page: fitz.Page, text: str) -> list[list[fitz.Rect]]:
        return find_all_matches_on_page(page, text)

    def _capture_rest_of_document_data(self, pdf_doc: fitz.Document, start_page_idx: int, y_threshold: float, x_threshold: float | None = None, gap_reference_y: float | None = None) -> list[dict[str, Any]]:
        return capture_rest_of_document_data(self, pdf_doc, start_page_idx, y_threshold, x_threshold, gap_reference_y)

    @staticmethod
    def _color_tuple_from_int(color_int: int) -> tuple[float, float, float]:
        # Convert fitz integer color to RGB tuple
        return (
            ((color_int >> 16) & 0xFF) / 255.0,
            ((color_int >> 8) & 0xFF) / 255.0,
            (color_int & 0xFF) / 255.0
        )

    def _modify_text_inline(
        self,
        pdf_doc: fitz.Document,
        target_text: str,
        fontsize: float,
        fontname: str,
        color: tuple[float, float, float],
    ) -> int:
        """Applies style or casing changes in-place without reflowing the document.
        Used for dimension-invariant changes (color).
        """
        modifications = 0
        for page in pdf_doc:
            matches = self._find_all_matches_on_page(page, target_text)
            if not matches:
                continue
            
            for m_rects in matches:
                # 1. Capture the exact line geometry to preserve baseline
                rect = m_rects[-1]
                line_info = self._find_line_for_rect(page, rect)
                if line_info:
                    line_rect, baseline_y = line_info
                    start_point = fitz.Point(m_rects[0].x0, baseline_y)
                else:
                    start_point = fitz.Point(m_rects[0].x0, rect.y1 - 1.0)
                
                # 2. Redact only the target words
                for r in m_rects:
                    page.add_redact_annot(r, fill=(1, 1, 1))
                page.apply_redactions()
                
                # 3. Rewrite strictly in the redacted space
                page.insert_text(start_point, target_text, fontsize=fontsize, fontname=fontname, color=color)
                modifications += 1
            
        return modifications

    def _replace_text(
        self,
        pdf_doc: fitz.Document,
        old_text: str,
        new_text: str,
        fontsize: float = 11,
        fontname: str = "helv",
        color: tuple[float, float, float] = (0, 0, 0),
        line_height_override: float | None = None,
        paragraph_gap_override: float | None = None,
        preferred_page_number: int | None = None,
        restrict_page_number: int | None = None,
        paragraph_index: int | None = None,
        occurrence_index: int | None = None,
    ) -> int:
        return replace_text_with_reflow(
            self,
            pdf_doc=pdf_doc,
            old_text=old_text,
            new_text=new_text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
            line_height_override=line_height_override,
            paragraph_gap_override=paragraph_gap_override,
            preferred_page_number=preferred_page_number,
            restrict_page_number=restrict_page_number,
            paragraph_index=paragraph_index,
            occurrence_index=occurrence_index,
        )

    @staticmethod
    def _line_height(fontsize: float) -> float:
        """Returns the default line height for a given font size.
        v29.0: Tightened factor to 1.2x for professional document rhythm.
        """
        return fontsize * 1.2

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
        paragraph_gap_override: float | None = None,
        right_limit_x: float | None = None,
        continuation_x: float | None = None,
    ) -> WrappedTextResult:
        margin = 36.0
        page = start_page
        line_height = line_height_override if line_height_override is not None else self._line_height(fontsize)

        y = start_point.y if respect_start_y else max(start_point.y, margin + line_height)
        curr_x = start_point.x
        
        paragraphs = text.split('\n')
        last_x, last_y = curr_x, y
        
        ended_with_newline = text.endswith('\n') or (len(paragraphs) > 1 and not paragraphs[-1].strip())
        
        for p_idx, p_text in enumerate(paragraphs):
            p_clean = p_text.strip()
            if not p_clean:
                # Default to a standard 1.4x paragraph gap if not detected
                y += paragraph_gap_override if paragraph_gap_override is not None else (line_height * 1.4)
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
                
            if p_idx < len(paragraphs) - 1:
                y += paragraph_gap_override if paragraph_gap_override is not None else (line_height * 1.4)
        
        return WrappedTextResult("", page, fitz.Point(last_x, last_y), ended_with_newline)

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
    def _map_span_font_to_base14(span_font: str | None) -> str:
        token = (span_font or "").lower()
        
        # v32.5: Recognize existing Base14 names to prevent accidental re-mapping.
        base14 = {"helv", "hebo", "heit", "hebi", "tiro", "tibo", "tiit", "tibi", "cour", "cobo", "coit", "cobi", "symb", "zabd"}
        if token in base14:
            return token

        is_bold = "bold" in token
        is_italic = any(flag in token for flag in ("italic", "oblique"))

        if "times" in token or "roman" in token:
            if is_bold and is_italic:
                return "tibo"
            if is_bold:
                return "tibo"
            if is_italic:
                return "tiit"
            return "tiro"
        if "courier" in token or "mono" in token:
            if is_bold and is_italic:
                return "cobo"
            if is_bold:
                return "cobo"
            if is_italic:
                return "coit"
            return "cour"

        if is_bold and is_italic:
            return "hebi"
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

        # Pass 3: Finalize and Delegate Rhythm Detection
        primary_style = {
            "fontsize": primary_fontsize,
            "fontname": fontname,
            "left_x": float(statistics.median(left_values)) if left_values else 36.0,
            "right_x": float(statistics.median(right_values)) if right_values else page.rect.width - 36.0,
        }
        
        # Consolidation: Use the specialized rhythm engine instead of repeating logic here
        lh, pg = self._infer_vertical_rhythm(page, primary_fontsize)
        primary_style["line_height"] = lh
        
        if primary_style["right_x"] - primary_style["left_x"] < 120:
            primary_style["left_x"] = 36.0
            primary_style["right_x"] = page.rect.width - 36.0

        return primary_style

    def _infer_vertical_rhythm(self, page: fitz.Page, fontsize: float) -> tuple[float, float]:
        return infer_vertical_rhythm(self, page, fontsize)


    @staticmethod
    def _find_line_for_rect(page: fitz.Page, rect: fitz.Rect) -> tuple[fitz.Rect, float] | None:
        return find_line_for_rect(page, rect)

    def _get_block_geometry(self, page: fitz.Page, rect: fitz.Rect) -> tuple[float, float, fitz.Rect | None]:
        return get_block_geometry(self, page, rect)


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
        insert_paragraph_below_anchor(self, pdf_doc, page, anchor_rect, text, fontsize, fontname, color)

    def _append_text_to_new_pages(
        self,
        pdf_doc: fitz.Document,
        text: str,
        fontsize: float,
        fontname: str,
        color: tuple[float, float, float],
    ) -> None:
        append_text_to_new_pages(self, pdf_doc, text, fontsize, fontname, color)

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
        return resolve_non_overlapping_y(occupied_rects, x, y, line, fontsize, fontname, line_height, bottom_limit)

    def _append_text_to_page_end(
        self,
        pdf_doc: fitz.Document,
        page_number: int,
        text: str,
        fontsize: float | None,
        fontname: str | None,
        color: tuple[float, float, float],
    ) -> None:
        append_text_to_page_end(self, pdf_doc, page_number, text, fontsize, fontname, color)

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



        return None

    def execute(self, tool_name: str, args: dict[str, Any]) -> ToolExecutionResult:
        try:
            return self._execute_internal(tool_name, args)
        except Exception as e:
            # v32.5: Clean error formatting for user. 
            # This prevents raw library exceptions (like PyMuPDF ValueErrors) from crashing the graph.
            return ToolExecutionResult(
                {
                    "tool": tool_name,
                    "status": "failed",
                    "success": False,
                    "output": {},
                    "error": str(e),
                }
            )

    def _execute_internal(self, tool_name: str, args: dict[str, Any]) -> ToolExecutionResult:
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

        if tool_name in {"replace_text", "search_replace", "remove_text"}:
            old_text = str(
                args.get("old_text", "")
                or args.get("search", "")
                or args.get("target_text", "")
                or args.get("text", "")
            )
            new_text = "" if tool_name == "remove_text" else str(args.get("new_text", "") or args.get("replace", ""))
            
            # v32.0: Unified Style & Rhythm Inference
            anchor = self._locate_semantic_anchor(pdf_doc, old_text)
            style = self._infer_page_text_style(pdf_doc[0])
            
            fontsize = float(args.get("font_size") or (anchor["fontsize"] if anchor else None) or (style["fontsize"] if style else 11.0))
            
            fontname = str((anchor["fontname"] if anchor else None) or (style["fontname"] if style else "helv"))

            color_raw = args.get("color")
            color = self._color_tuple(str(color_raw)) if color_raw else (anchor["color"] if anchor else (0, 0, 0))

            scope = str(args.get("scope", "all")).lower()
            page_number_raw = args.get("page_number")
            page_number = int(page_number_raw) if page_number_raw is not None else None
            paragraph_index_raw = args.get("paragraph_index")
            paragraph_index = int(paragraph_index_raw) if isinstance(paragraph_index_raw, int | float) and int(paragraph_index_raw) > 0 else None
            occurrence_raw = args.get("occurrence")
            occurrence = int(occurrence_raw) if isinstance(occurrence_raw, int | float) and int(occurrence_raw) > 0 else None

            if not old_text or (tool_name != "remove_text" and old_text == new_text):
                changed = 0
            else:
                if occurrence is not None:
                    changed = self._replace_text(
                        pdf_doc,
                        old_text=old_text,
                        new_text=new_text,
                        fontsize=fontsize,
                        fontname=fontname,
                        color=color,
                        preferred_page_number=page_number if scope == "page" else None,
                        restrict_page_number=page_number if scope == "page" else None,
                        paragraph_index=paragraph_index,
                        occurrence_index=occurrence,
                    )
                else:
                    changed = 0
                    max_replacements = 200
                    for _ in range(max_replacements):
                        replaced = self._replace_text(
                            pdf_doc,
                            old_text=old_text,
                            new_text=new_text,
                            fontsize=fontsize,
                            fontname=fontname,
                            color=color,
                            preferred_page_number=page_number if scope == "page" else None,
                            restrict_page_number=page_number if scope == "page" else None,
                            paragraph_index=paragraph_index,
                        )
                        if replaced <= 0:
                            break
                        changed += replaced
        elif tool_name == "add_text":
            try:
                changed = apply_add_text(self, pdf_doc, args)
            except ValueError as error:
                return ToolExecutionResult(
                    {
                        "tool": tool_name,
                        "status": "failed",
                        "success": False,
                        "output": {},
                        "error": str(error),
                    }
                )
        elif tool_name in {"change_font_size", "change_font_color", "set_text_style", "convert_case"}:
            changed = apply_text_style_change(self, pdf_doc, tool_name, args)
        elif tool_name in {"highlight_text", "underline_text", "strikethrough_text"}:
            changed = apply_annotations(self, pdf_doc, tool_name, args)
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
