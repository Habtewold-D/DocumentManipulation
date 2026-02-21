from typing import Any
import hashlib

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
                baseline_y = rect.y1 - 1 if preserve_line_baseline else max(36, rect.y0 + fontsize)
                start_point = fitz.Point(rect.x0, baseline_y)
                overflow = self._insert_wrapped_text(
                    pdf_doc=pdf_doc,
                    start_page=page,
                    start_point=start_point,
                    text=new_text,
                    fontsize=fontsize,
                    fontname=fontname,
                    color=color,
                    respect_start_y=preserve_line_baseline,
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
    ) -> str:
        margin = 36.0
        page = start_page
        page_index = page.number
        line_height = self._line_height(fontsize)

        y = start_point.y if respect_start_y else max(start_point.y, margin + line_height)
        max_width = max(80.0, page.rect.width - margin - start_point.x)
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
                    max_width = max(80.0, page.rect.width - margin - margin)

                if y > page.rect.height - margin:
                    remaining_lines.append(line)
                    break

                x = start_point.x if page.number == start_page.number else margin
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
                        max_width = max(80.0, page.rect.width - margin - margin)
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

            candidate_y = max(rect.y1 for rect in overlaps) + line_height * 0.4
            if candidate_y > bottom_limit:
                return candidate_y

        return candidate_y

    def _append_text_to_page_end(
        self,
        pdf_doc: fitz.Document,
        page_number: int,
        text: str,
        fontsize: float,
        fontname: str,
        color: tuple[float, float, float],
    ) -> None:
        margin = 36.0
        line_height = self._line_height(fontsize)
        page_index = max(0, min(page_number - 1, len(pdf_doc) - 1))
        page = pdf_doc[page_index]
        words = page.get_text("words")

        if words:
            last_bottom = max(w[3] for w in words)
            start_y = last_bottom + line_height
        else:
            start_y = margin + line_height

        start_point = self._clamp_start_point(page, fitz.Point(margin, start_y), fontsize)
        overflow = self._insert_wrapped_text(
            pdf_doc=pdf_doc,
            start_page=page,
            start_point=start_point,
            text=text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
            avoid_overlay=True,
        )
        if overflow:
            self._append_text_to_new_pages(pdf_doc, overflow, fontsize, fontname, color)

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

            fontsize = float(args.get("font_size", 11))
            color = self._color_tuple(args.get("color"))
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
            has_coordinates = args.get("x") is not None and args.get("y") is not None
            inserted = False
            place_at_end = (
                ("end" in position)
                or ("at end" in command)
                or ("last" in position)
                or ("append" in position)
                or ("end of" in command)
            )

            if not anchor_text and page_number > 0 and place_at_end:
                self._append_text_to_page_end(
                    pdf_doc=pdf_doc,
                    page_number=page_number,
                    text=text,
                    fontsize=fontsize,
                    fontname="helv",
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
                            fontsize=fontsize,
                            fontname="helv",
                            color=color,
                            avoid_overlay=False,
                            respect_start_y=True,
                        )
                        if overflow:
                            self._append_text_to_new_pages(
                                pdf_doc=pdf_doc,
                                text=overflow,
                                fontsize=fontsize,
                                fontname="helv",
                                color=color,
                            )
                        inserted = True
                    elif "next" in position or "right" in position or "beside" in position:
                        raw_point = fitz.Point(rect.x1 + 8, rect.y1)
                        start_point = self._clamp_start_point(page, raw_point, fontsize)
                        overflow = self._insert_wrapped_text(
                            pdf_doc=pdf_doc,
                            start_page=page,
                            start_point=start_point,
                            text=text,
                            fontsize=fontsize,
                            fontname="helv",
                            color=color,
                            avoid_overlay=True,
                        )
                        if overflow:
                            self._append_text_to_new_pages(
                                pdf_doc=pdf_doc,
                                text=overflow,
                                fontsize=fontsize,
                                fontname="helv",
                                color=color,
                            )
                        inserted = True
                    elif "above" in position:
                        raw_point = fitz.Point(rect.x0, rect.y0 - 4)
                        start_point = self._clamp_start_point(page, raw_point, fontsize)
                        overflow = self._insert_wrapped_text(
                            pdf_doc=pdf_doc,
                            start_page=page,
                            start_point=start_point,
                            text=text,
                            fontsize=fontsize,
                            fontname="helv",
                            color=color,
                            avoid_overlay=True,
                        )
                        if overflow:
                            self._append_text_to_new_pages(
                                pdf_doc=pdf_doc,
                                text=overflow,
                                fontsize=fontsize,
                                fontname="helv",
                                color=color,
                            )
                        inserted = True
                    else:
                        raw_point = fitz.Point(rect.x0, rect.y1 + self._line_height(fontsize))
                        start_point = self._clamp_start_point(page, raw_point, fontsize)
                        overflow = self._insert_wrapped_text(
                            pdf_doc=pdf_doc,
                            start_page=page,
                            start_point=start_point,
                            text=text,
                            fontsize=fontsize,
                            fontname="helv",
                            color=color,
                            avoid_overlay=True,
                        )
                        if overflow:
                            self._append_text_to_new_pages(
                                pdf_doc=pdf_doc,
                                text=overflow,
                                fontsize=fontsize,
                                fontname="helv",
                                color=color,
                            )
                        inserted = True

            if not inserted and page_number > 0 and page_number <= len(pdf_doc) and has_coordinates:
                page = pdf_doc[page_number - 1]
                raw_point = fitz.Point(float(args.get("x", 72)), float(args.get("y", 72)))
                start_point = self._clamp_start_point(page, raw_point, fontsize)
                overflow = self._insert_wrapped_text(
                    pdf_doc=pdf_doc,
                    start_page=page,
                    start_point=start_point,
                    text=text,
                    fontsize=fontsize,
                    fontname="helv",
                    color=color,
                    avoid_overlay=True,
                )
                if overflow:
                    self._append_text_to_new_pages(
                        pdf_doc=pdf_doc,
                        text=overflow,
                        fontsize=fontsize,
                        fontname="helv",
                        color=color,
                    )
                inserted = True

            if not inserted:
                self._append_text_to_new_pages(
                    pdf_doc=pdf_doc,
                    text=text,
                    fontsize=fontsize,
                    fontname="helv",
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
