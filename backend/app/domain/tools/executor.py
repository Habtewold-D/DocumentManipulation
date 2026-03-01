from typing import Any
import hashlib
import statistics

import fitz

from app.storage.asset_service import AssetService
from app.storage.cloudinary_client import CloudinaryClient


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
        """Unified semantic search: Consolidates search, geometry, and style inference."""
        if not anchor_text.strip(): return None
        clean_text = anchor_text.strip()
        words = clean_text.split()
        
        # 1. SEARCH STRATEGY: Full, Skip-1, First-8, Last-6
        search_candidates = [
            " ".join(words),
            " ".join(words[1:]) if len(words) > 1 else None,
            " ".join(words[:8]) if len(words) > 8 else None,
            " ".join(words[-6:]) if len(words) > 6 else None,
        ]
        unique_candidates = [c for c in search_candidates if c]

        # 2. SCANNING PREFERENCE
        pages_to_scan = list(pdf_doc)
        if prefer_last:
            pages_to_scan = list(reversed(pages_to_scan))
        elif preferred_page_number and 1 <= preferred_page_number <= len(pdf_doc):
            pref_page = pdf_doc[preferred_page_number - 1]
            if pref_page in pages_to_scan:
                pages_to_scan.remove(pref_page)
                pages_to_scan.insert(0, pref_page)

        for candidate in unique_candidates:
            for page in pages_to_scan:
                # Use robust matching to handle multi-line wraps in original PDF
                matches = self._find_all_matches_on_page(page, candidate)
                if not matches: continue
                
                # Take primary match (first or last based on preference)
                rects = matches[0] if not prefer_last else matches[-1]
                
                # Found it! Extract geometry and style
                full_match_rect = fitz.Rect(rects[0])
                for r in rects: full_match_rect |= r
                
                # Style & Geometry
                start_line_info = self._find_line_for_rect(page, rects[0])
                end_line_info = self._find_line_for_rect(page, rects[-1])
                first_line_x, block_x, block_rect = self._get_block_geometry(page, full_match_rect)
                
                # Extract style from dict
                text_dict = page.get_text("dict", clip=full_match_rect)
                block_spans = [s for b in text_dict.get("blocks", []) for l in b.get("lines", []) for s in l.get("spans", [])]
                if not block_spans: continue
                
                return {
                    "page": page,
                    "rects": rects,
                    "full_match_rect": full_match_rect,
                    "baseline_y": start_line_info[1] if start_line_info else (rects[0].y1 - 1.0),
                    "first_line_x": first_line_x,
                    "block_x": block_x,
                    "block_rect": block_rect,
                    "fontsize": float(block_spans[0]["size"]),
                    "fontname": self._map_span_font_to_base14(str(block_spans[0].get("font", "helv"))),
                    "color": self._color_tuple_from_int(block_spans[0].get("color", 0)),
                    "line_bottom": end_line_info[0].y1 if end_line_info else rects[-1].y1,
                    "text": candidate
                }
        return None

    def _reflow_remaining_blocks(
        self,
        pdf_doc: fitz.Document,
        last_res: WrappedTextResult,
        captured_blocks: list[dict[str, Any]],
        active_lh: float,
        active_pg: float
    ) -> WrappedTextResult:
        """Unified 'Push-Down' reflow loop: Standardizes vertical rhythm across all tools."""
        curr_res = last_res
        for i, block in enumerate(captured_blocks):
            original_gap = float(block.get("original_gap", 0) or 0)
            block_lh = float(block.get("original_baseline_height") or active_lh)

            if block.get("is_tail"):
                spacing = 0
            elif block.get("same_paragraph"):
                spacing = block_lh
            elif original_gap > 0:
                spacing = max(original_gap, block_lh)
            else:
                spacing = active_pg
                
            start_pt = fitz.Point(block["x0"], curr_res.final_point.y + spacing)
            
            curr_res = self._insert_wrapped_text(
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
                continuation_x=block.get("continuation_x", block["x0"])
            )
        return curr_res

    def _find_all_matches_on_page(self, page: fitz.Page, text: str) -> list[list[fitz.Rect]]:
        """Finds all occurrences of text on page, supporting multi-line word sequences."""
        if not text.strip():
            return []
        
        target_words = text.split()
        if not target_words:
            return []
        
        # We use words to handle cross-line matches precisely
        page_words = page.get_text("words")  # (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        matches = []
        
        i = 0
        while i <= len(page_words) - len(target_words):
            match = True
            for j in range(len(target_words)):
                page_word = page_words[i + j][4].lower().strip(".,!?;:()[]'\"")
                target_word = target_words[j].lower().strip(".,!?;:()[]'\"")
                if page_word != target_word:
                    match = False
                    break
            
            if match:
                match_rects = [fitz.Rect(page_words[i+j][:4]) for j in range(len(target_words))]
                matches.append(match_rects)
                i += len(target_words)  # Skip past this match
            else:
                i += 1
                
        return matches

    def _capture_rest_of_document_data(self, pdf_doc: fitz.Document, start_page_idx: int, y_threshold: float, x_threshold: float | None = None, gap_reference_y: float | None = None) -> list[dict[str, Any]]:
        """Captures structured text blocks and tails for continuous reflow.
        gap_reference_y: The y-coordinate to measure the first gap from (usually anchor bottom).
        """
        captured_blocks: list[dict[str, Any]] = []
        last_block_text = ""
        
        def process_page(page: fitz.Page, y_min: float, x_min_on_first_line: float | None = None, is_first_page: bool = False):
            nonlocal last_block_text
            text_dict = page.get_text("dict")
            blocks = sorted(text_dict.get("blocks", []), key=lambda b: b["bbox"][1])
            
            # Use BASELINE TRACKING for absolute spatial precision
            # prev_block_baseline: the BASELINE Y of the LAST line of the previous block
            prev_block_baseline = gap_reference_y if gap_reference_y is not None else y_min 
            is_first_block_on_page = True
            
            for block in blocks:
                if block.get("type") != 0: continue
                bbox = block.get("bbox")
                
                # Case 1: Strictly above the line of interest
                if bbox[3] < y_min - 2: continue
                
                # Logic for "Same Paragraph" detection
                # If the gap between this block and the previous one is small (e.g. < 0.3x fontsize),
                # it's likely a continuation of the same text flow (sentence), not a new paragraph.
                is_same_para = False
                
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
                    
                    combined_tail_raw = "".join(tail_text_parts).strip()
                    if combined_tail_raw:
                        # Normalize tail: Join internal newlines into spaces for fluid reflow
                        combined_tail = " ".join(combined_tail_raw.splitlines())
                        first_span = block["lines"][0]["spans"][0] if block["lines"] else None
                        captured_blocks.append({
                            "text": combined_tail,
                            "x0": float(bbox[0]),
                            "x1": float(bbox[2]),
                            "fontsize": float(first_span["size"]) if first_span else 11.0,
                            "fontname": self._map_span_font_to_base14(str(first_span["font"])) if first_span else "helv",
                            "color": self._color_tuple_from_int(first_span["color"]) if first_span else (0,0,0),
                            "continuation_x": float(block["lines"][1]["bbox"][0]) if len(block["lines"]) > 1 else float(bbox[0]),
                            "is_tail": is_actual_tail,
                            "same_paragraph": False, # Tails always start the fresh flow
                            "original_baseline_height": float(self._infer_vertical_rhythm(page, first_span["size"])[0]) if first_span else 12.1
                        })
                    # Track baseline of the last line processed in this block
                    last_line = block["lines"][-1] if block.get("lines") else None
                    prev_block_baseline = last_line["spans"][0]["origin"][1] if last_line and last_line.get("spans") else bbox[3]
                    continue

                # Case 3: Strictly below the line/threshold
                if bbox[1] < y_min - 2: continue
                
                block_text_raw = page.get_text("text", clip=bbox).strip()
                if not block_text_raw: continue
                # Normalize block: Join internal newlines into spaces for fluid reflow
                block_text = " ".join(block_text_raw.splitlines())

                # Mark for removal
                page.add_redact_annot(bbox, fill=(1, 1, 1))

                # Extract typography metrics from correctly scoped block spans
                block_spans = [s for line in block.get("lines", []) for s in line.get("spans", [])]
                if not block_spans: continue
                fs = float(block_spans[0].get("size", 11.0))
                fontname = self._map_span_font_to_base14(str(block_spans[0].get("font", "helv")))
                color = self._color_tuple_from_int(block_spans[0].get("color", 0))

                # MARGIN SANITIZATION:
                cont_x = float(bbox[0])
                if len(block.get("lines", [])) > 1:
                    cont_x = float(block["lines"][1]["bbox"][0])

                # BASELINE-TO-BASELINE RHYTHM:
                # Capture the exact mathematical distance between line baselines.
                first_line = block["lines"][0] if block.get("lines") else None
                curr_first_baseline = first_line["spans"][0]["origin"][1] if first_line and first_line.get("spans") else bbox[3]
                
                curr_gap = curr_first_baseline - prev_block_baseline
                force_new_para = False
                
                if is_first_block_on_page and not is_first_page:
                    curr_gap = 0
                    if last_block_text.strip().endswith((".", "!", "?", ":")):
                        force_new_para = True
                
                is_first_block_on_page = False
                
                # Update rhythm for this block
                lh, pg = self._infer_vertical_rhythm(page, fs)
                
                # MICRO-PRECISION: Capture exact baseline leading for this specific block
                original_lh = lh
                if len(block.get("lines", [])) > 1:
                    line_dists = []
                    for idx in range(1, len(block["lines"])):
                        prev_l = block["lines"][idx-1]
                        curr_l = block["lines"][idx]
                        if prev_l.get("spans") and curr_l.get("spans"):
                            line_dists.append(curr_l["spans"][0]["origin"][1] - prev_l["spans"][0]["origin"][1])
                    if line_dists:
                        original_lh = float(statistics.median(line_dists))

                # BIMODAL THRESHOLD: Midpoint between Leading (LH) and Paragraph (PG) 
                midpoint = (lh + pg) / 2
                is_same_para_geometric = (curr_gap < midpoint) and (not force_new_para)

                # v31.9: SEMANTIC SEPARATION: Don't bridge lexically if the current block
                # looks like a new sentence or label (starts with an uppercase letter).
                terminators = (".", "!", "?", ":", ";")
                style_match = False
                if captured_blocks:
                    prev = captured_blocks[-1]
                    style_match = (
                        abs(prev["fontsize"] - fs) < 0.1 and 
                        prev["fontname"] == fontname and 
                        prev["color"] == color
                    )

                # Only bridge if it's a lowercase start (strong signal for a wrap)
                # OR if the previous block was already a substantial paragraph (> 60 chars).
                is_lowercase_start = block_text.strip() and block_text.strip()[0].islower()
                lexical_continuation = last_block_text.strip() and not last_block_text.strip().endswith(terminators)
                
                is_same_para = is_same_para_geometric or (
                    style_match and lexical_continuation and curr_gap < lh * 2.2 and 
                    (is_lowercase_start or len(last_block_text) > 60)
                )

                # v31.7: PROXIMITY MERGING: If it's the same paragraph and styles match, 
                # unite into the previous block to ensure fluid reflow.
                if is_same_para and captured_blocks:
                    prev = captured_blocks[-1]
                    if (abs(prev["fontsize"] - fs) < 0.1 and 
                        prev["fontname"] == fontname and 
                        prev["color"] == color):
                        # Merge text
                        prev["text"] += " " + block_text
                        prev["x1"] = max(prev["x1"], float(bbox[2]))
                        # Update prev_block_baseline to the LAST line of THIS block
                        last_line = block["lines"][-1] if block.get("lines") else None
                        prev_block_baseline = last_line["spans"][0]["origin"][1] if last_line and last_line.get("spans") else bbox[3]
                        last_block_text = block_text
                        continue

                captured_blocks.append({
                    "text": block_text,
                    "x0": float(bbox[0]),
                    "x1": float(bbox[2]),
                    "fontsize": fs,
                    "fontname": fontname,
                    "color": color,
                    "continuation_x": cont_x,
                    "same_paragraph": is_same_para,
                    "original_gap": float(curr_gap),
                    "original_baseline_height": original_lh
                })
                # Update prev_block_baseline to the LAST line of THIS block
                last_line = block["lines"][-1] if block.get("lines") else None
                prev_block_baseline = last_line["spans"][0]["origin"][1] if last_line and last_line.get("spans") else bbox[3]
                last_block_text = block_text

            # ACTUALLY APPLY REDACTIONS TO CLEAR THE PAGE
            page.apply_redactions(images=0, graphics=0)
            
        # Process starting page
        process_page(pdf_doc[start_page_idx], y_threshold, x_threshold, is_first_page=True)

        # Process subsequent pages
        for p_idx in range(start_page_idx + 1, len(pdf_doc)):
            process_page(pdf_doc[p_idx], 0, is_first_page=False)
            
        return captured_blocks

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
    ) -> int:
        """Replace only the target span while preserving natural inline flow for neighboring text."""
        anchor = self._locate_semantic_anchor(pdf_doc, old_text, preferred_page_number=preferred_page_number)
        if not anchor:
            return 0
        if restrict_page_number is not None and anchor["page"].number + 1 != restrict_page_number:
            return 0

        page = anchor["page"]

        exact_matches = self._find_all_matches_on_page(page, old_text)
        target_rects = exact_matches[0] if exact_matches else anchor["rects"]
        full_match_rect = fitz.Rect(target_rects[0])
        for rect in target_rects:
            full_match_rect |= rect

        start_line_info = self._find_line_for_rect(page, target_rects[0])
        end_line_info = self._find_line_for_rect(page, target_rects[-1])
        if start_line_info:
            start_line_rect, start_baseline_y = start_line_info
        else:
            start_line_rect = fitz.Rect(full_match_rect)
            start_baseline_y = anchor["baseline_y"]
        if end_line_info:
            end_line_rect, end_baseline_y = end_line_info
        else:
            end_line_rect = fitz.Rect(full_match_rect)
            end_baseline_y = anchor["baseline_y"]

        block_rect = anchor.get("block_rect") or fitz.Rect(start_line_rect.x0, start_line_rect.y0, end_line_rect.x1, end_line_rect.y1)

        # Tail text that should remain unchanged starts immediately after the target.
        same_line_tail_tokens: list[tuple[float, str]] = []
        words = page.get_text("words")
        for word in words:
            wx0, wy0, _, wy1, wtext = word[:5]
            if wy1 <= end_line_rect.y0 or wy0 >= end_line_rect.y1:
                continue
            if wx0 >= full_match_rect.x1 - 0.5:
                same_line_tail_tokens.append((float(wx0), str(wtext)))

        same_line_tail = ""
        if same_line_tail_tokens:
            same_line_tail_tokens.sort(key=lambda item: item[0])
            same_line_tail = " ".join(token for _, token in same_line_tail_tokens).strip()

        below_line_tail_parts: list[str] = []
        block_dict = page.get_text("dict", clip=block_rect)
        for blk in block_dict.get("blocks", []):
            if blk.get("type") != 0:
                continue
            for line in blk.get("lines", []):
                lbox = line.get("bbox")
                if not lbox:
                    continue
                if float(lbox[1]) > end_line_rect.y1 + 0.5:
                    line_text = "".join(str(span.get("text", "")) for span in line.get("spans", [])).strip()
                    if line_text:
                        below_line_tail_parts.append(line_text)

        inline_tail = " ".join(part for part in [same_line_tail, " ".join(below_line_tail_parts).strip()] if part).strip()

        # Capture only content below this paragraph block; we will reconstruct target+tail ourselves.
        captured_blocks = self._capture_rest_of_document_data(
            pdf_doc,
            page.number,
            y_threshold=block_rect.y1 + 2.0,
            gap_reference_y=block_rect.y1,
        )

        # Clear from target start to paragraph-block bottom per line.
        # This avoids leaving old text on wrapped lines (duplication/overlay) while preserving text before target on first line.
        block_dict_for_redact = page.get_text("dict", clip=block_rect)
        for blk in block_dict_for_redact.get("blocks", []):
            if blk.get("type") != 0:
                continue
            for line in blk.get("lines", []):
                lbox = line.get("bbox")
                if not lbox:
                    continue
                lrect = fitz.Rect(lbox)
                if lrect.y1 < start_line_rect.y0 - 0.5:
                    continue

                if lrect.intersects(start_line_rect):
                    rx0 = target_rects[0].x0
                else:
                    rx0 = block_rect.x0
                rx1 = max(rx0 + 1.0, lrect.x1)
                page.add_redact_annot(fitz.Rect(rx0, lrect.y0, rx1, lrect.y1), fill=(1, 1, 1))
        page.apply_redactions()

        base_lh_detected, base_pg_detected = self._infer_vertical_rhythm(page, anchor["fontsize"])
        target_lh = self._line_height(fontsize)
        edited_lh = max(line_height_override or base_lh_detected, target_lh)
        base_lh = base_lh_detected
        pg = paragraph_gap_override or base_pg_detected

        start_pt = fitz.Point(target_rects[0].x0, start_baseline_y)
        res = self._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=start_pt,
            text=new_text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
            respect_start_y=True,
            line_height_override=edited_lh,
            continuation_x=anchor["block_x"],
        )

        if inline_tail:
            res = self._insert_wrapped_text(
                pdf_doc=pdf_doc,
                start_page=res.final_page,
                start_point=fitz.Point(res.final_point.x, res.final_point.y),
                text=inline_tail,
                fontsize=anchor["fontsize"],
                fontname=anchor["fontname"],
                color=anchor["color"],
                respect_start_y=True,
                line_height_override=base_lh,
                continuation_x=anchor["block_x"],
            )

        self._reflow_remaining_blocks(pdf_doc, res, captured_blocks, base_lh, pg)
        return 1

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
        """Detects (line_height, paragraph_gap) from page content using clustering.
        v30.0: The Baseline Revolution. Uses font origins for absolute precision.
        """
        text_dict = page.get_text("dict")
        baseline_distances: list[float] = []
        all_distances: list[float] = []
        
        # 1. Collect absolute baseline-to-baseline distances
        prev_baseline_y = None
        blocks = sorted(text_dict.get("blocks", []), key=lambda b: b["bbox"][1])
        
        for block in blocks:
            if block.get("type") != 0: continue
            for line in block.get("lines", []):
                # Use span origin for true baseline (not bbox bottom)
                spans = line.get("spans", [])
                if not spans: continue
                
                curr_baseline_y = spans[0]["origin"][1]
                
                if prev_baseline_y is not None:
                    dist = curr_baseline_y - prev_baseline_y
                    # Valid distances: 0.5x to 8.0x font size
                    if 0.5 * fontsize < dist < 8.0 * fontsize:
                        # v31.4: Use 0.5pt buckets for stability
                        all_distances.append(round(dist * 2) / 2)
                
                prev_baseline_y = curr_baseline_y

        if not all_distances:
            lh = self._line_height(fontsize)
            return lh, lh * 1.4

        # 2. Extract Standard Leading (LH)
        # We find the SMALLEST frequent peak that is > 0.8 * fontsize. 
        # This is the true inter-line rhythm, ignoring paragraph gaps.
        candidate_lhs = [d for d in all_distances if d > fontsize * 0.8]
        if candidate_lhs:
            counts = statistics.multimode(candidate_lhs)
            lh = float(min(counts))
        else:
            lh = float(statistics.median(all_distances))

        # 3. Extract Paragraph Gaps (PG)
        # Look for gaps significantly larger than the detected leading
        larger_gaps = [d for d in all_distances if d >= lh + 1.0] # 1pt precision
        if larger_gaps:
            pg_counts = statistics.multimode(larger_gaps)
            pg = float(min(pg_counts))
        else:
            pg = lh * 1.4 # v31.4: Standard 1.4x fallback for paragraph gap
            
        return lh, pg


    @staticmethod
    def _find_line_for_rect(page: fitz.Page, rect: fitz.Rect) -> tuple[fitz.Rect, float] | None:
        """Finds the precise line rectangle and mathematical baseline for a given rect."""
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0: continue
            for line in block.get("lines", []):
                bbox = line.get("bbox")
                line_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                
                # Check if this line contains or intersects the target rect
                if not line_rect.intersects(rect):
                    continue

                span_origins = []
                span_bottoms = []
                for span in line.get("spans", []):
                    # Use 'origin' for mathematical baseline
                    origin = span.get("origin")
                    if isinstance(origin, (list, tuple)) and len(origin) == 2:
                        span_origins.append(float(origin[1]))
                    
                    span_bbox = span.get("bbox")
                    if isinstance(span_bbox, (list, tuple)) and len(span_bbox) == 4:
                        span_bottoms.append(float(span_bbox[3]))
                
                # Preferred: Actual mathematical baseline from 'origin'
                if span_origins:
                    baseline_y = statistics.median(span_origins)
                else:
                    # Fallback to bottom of spans minus a small offset
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
        """Unified Paragraph Insertion: Standardized on Reflow helpers."""
        style = self._infer_page_text_style(page)
        margin = 36.0
        
        # 1. GEOMETRY: Inherit from the anchor block
        first_line_x, block_x, block_rect = self._get_block_geometry(page, anchor_rect)
        est_fs = fontsize or (float(style["fontsize"]) if style else 11.0)
        lh, pg = self._infer_vertical_rhythm(page, est_fs)
        
        # 2. ANCHORING: Find exact split points
        line_info = self._find_line_for_rect(page, anchor_rect)
        anchor_baseline = line_info[1] if line_info else (anchor_rect.y1 - (lh * 0.2))
        anchor_line_bottom = line_info[0].y1 if line_info else anchor_rect.y1
        
        if block_rect:
            anchor_line_bottom = block_rect.y1
            text_dict = page.get_text("dict", clip=block_rect)
            for b in text_dict.get("blocks", []):
                if b["lines"]:
                    last_l = b["lines"][-1]
                    if last_l["spans"]:
                        anchor_baseline = last_l["spans"][0]["origin"][1]

        # 3. CAPTURE & INSERT
        captured_blocks = self._capture_rest_of_document_data(
            pdf_doc, page.number, y_threshold=anchor_line_bottom + 2.0, gap_reference_y=anchor_baseline
        )
        
        start_pt = self._clamp_start_point(page, fitz.Point(first_line_x, anchor_line_bottom + pg), est_fs)
        res = self._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=start_pt,
            text=text,
            fontsize=est_fs,
            fontname=fontname or (str(style["fontname"]) if style else "helv"),
            color=color,
            respect_start_y=True,
            line_height_override=lh,
            continuation_x=block_x
        )
        
        # 4. REFLOW
        self._reflow_remaining_blocks(pdf_doc, res, captured_blocks, lh, pg)

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
        res = self._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=fitz.Point(margin, margin + self._line_height(fontsize)),
            text=text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
            avoid_overlay=False, # Default to False for new pages
            respect_start_y=True, # Always respect start_y for new pages
        )
        if res.overflow:
            self._append_text_to_new_pages(pdf_doc, res.overflow, fontsize, fontname, color)

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
        res = self._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=start_point,
            text=text,
            fontsize=resolved_fontsize,
            fontname=resolved_fontname,
            color=color,
            avoid_overlay=True,
            respect_start_y=True, # Always respect start_y for append
            line_height_override=resolved_line_height,
            right_limit_x=right_x,
            continuation_x=left_x,
        )
        if res.overflow:
            self._append_text_to_new_pages(pdf_doc, res.overflow, resolved_fontsize, resolved_fontname, color)

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

        if tool_name in {"replace_text", "search_replace"}:
            old_text = str(args.get("old_text", "") or args.get("search", ""))
            new_text = str(args.get("new_text", "") or args.get("replace", ""))
            
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

            if not old_text or old_text == new_text:
                changed = 0
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
                    )
                    if replaced <= 0:
                        break
                    changed += replaced
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
            
            fontname = None
            
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
                anchor = self._locate_semantic_anchor(pdf_doc, anchor_text=anchor_text, 
                                                      preferred_page_number=page_number or None, prefer_last=True)
                if anchor:
                    user_intent = str(args.get("intent", "paragraph")).lower()
                    is_inline = (user_intent == "text") or any(kw in position for kw in ["text", "next to", "beside", "after"])
                    
                    if is_inline:
                        # Inline Append: Redact anchor and re-write (Anchor + Content) for stability.
                        content_to_add = text.strip()
                        if not content_to_add.startswith(" ") and not anchor["text"].strip().endswith(" "):
                             content_to_add = " " + content_to_add
                        full_payload = anchor["text"] + content_to_add
                        
                        # Capture and Redact
                        captured_blocks = self._capture_rest_of_document_data(
                            pdf_doc, anchor["page"].number, 
                            y_threshold=anchor["line_bottom"] + 0.5,
                            gap_reference_y=anchor["baseline_y"]
                        )
                        for r in anchor["rects"]:
                            anchor["page"].add_redact_annot(r, fill=(1, 1, 1))
                        anchor["page"].apply_redactions()
                        
                        # Re-insert with Push-Down logic
                        lh, pg = self._infer_vertical_rhythm(anchor["page"], anchor["fontsize"])
                        start_pt = fitz.Point(anchor["rects"][0].x0, anchor["baseline_y"])
                        res = self._insert_wrapped_text(
                            pdf_doc=pdf_doc,
                            start_page=anchor["page"],
                            start_point=start_pt,
                            text=full_payload,
                            fontsize=fontsize or anchor["fontsize"],
                            fontname=fontname or anchor["fontname"],
                            color=color or anchor["color"],
                            respect_start_y=True,
                            line_height_override=lh,
                            continuation_x=anchor["block_x"]
                        )
                        self._reflow_remaining_blocks(pdf_doc, res, captured_blocks, lh, pg)
                    else:
                        # Full Paragraph Vertical Push
                        self._insert_paragraph_below_anchor(
                            pdf_doc=pdf_doc,
                            page=anchor["page"],
                            anchor_rect=anchor["full_match_rect"],
                            text=text,
                            fontsize=fontsize or anchor["fontsize"],
                            fontname=fontname or anchor["fontname"],
                            color=color or anchor["color"],
                        )
                    inserted = True

            if not inserted and page_number > 0 and page_number <= len(pdf_doc) and has_coordinates:
                page = pdf_doc[page_number - 1]
                raw_point = fitz.Point(float(args.get("x", 72)), float(args.get("y", 72)))
                start_point = self._clamp_start_point(page, raw_point, fontsize or 11.0)
                res = self._insert_wrapped_text(
                    pdf_doc=pdf_doc,
                    start_page=page,
                    start_point=start_point,
                    text=text,
                    fontsize=fontsize or 11.0,
                    fontname=fontname or "helv",
                    color=color,
                    avoid_overlay=True,
                    respect_start_y=True,
                )
                if res.overflow:
                    self._append_text_to_new_pages(
                        pdf_doc=pdf_doc,
                        text=res.overflow,
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
        elif tool_name in {"change_font_size", "change_font_color", "set_text_style", "convert_case"}:
            target_text = str(args.get("target_text", ""))
            transformed = target_text
            
            # v32.0: Unified Reflow Engine for ALL property changes.
            # This ensures that even color changes use the same "Perfect" rhythmic path.
            anchor = self._locate_semantic_anchor(pdf_doc, target_text)
            existing_style = {
                "fontsize": anchor["fontsize"],
                "fontname": anchor["fontname"],
                "color": anchor["color"]
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
            color = self._color_tuple(str(raw_color)) if raw_color else existing_style["color"]

            if tool_name == "set_text_style":
                style = str(args.get("style", ""))
                curr_font = existing_style["fontname"]
                is_currently_bold = curr_font in ["hebo", "hebi", "tibo", "cobo"]
                is_currently_italic = curr_font in ["heit", "hebi", "tiit", "coit"]
                target_bold = is_currently_bold or (style == "bold")
                target_italic = is_currently_italic or (style == "italic")
                if target_bold and target_italic: font_name = "hebi"
                elif target_bold: font_name = "hebo"
                elif target_italic: font_name = "heit"
                else: font_name = "helv"

            try:
                active_lh, active_pg = self._infer_vertical_rhythm(pdf_doc[0], existing_style["fontsize"])
            except Exception:
                active_lh, active_pg = None, None

            # v32.3: Use In-Place Path for dimension-invariant changes (Color Only)
            # This prevents layout shifts and paragraph gap collapse reported by user.
            is_color_only = (tool_name == "change_font_color") or (
                tool_name == "set_text_style" and font_size == existing_style["fontsize"] and font_name == existing_style["fontname"]
            )
            
            if is_color_only:
                changed = self._modify_text_inline(
                    pdf_doc,
                    target_text=target_text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color
                )
            else:
                if tool_name == "change_font_size":
                    override_lh = None
                    override_pg = None
                else:
                    override_lh = active_lh
                    override_pg = active_pg
                changed = self._replace_text(
                    pdf_doc,
                    old_text=target_text,
                    new_text=transformed,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color,
                    line_height_override=override_lh,
                    paragraph_gap_override=override_pg,
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
