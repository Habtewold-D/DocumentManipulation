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
    ) -> int:
        replacements = 0
        for page in pdf_doc:
            rects = page.search_for(old_text)
            for rect in rects:
                page.add_redact_annot(rect, fill=(1, 1, 1))
            if rects:
                page.apply_redactions()
            for rect in rects:
                page.insert_text(
                    point=(rect.x0, rect.y1 - 2),
                    text=new_text,
                    fontsize=fontsize,
                    fontname=fontname,
                    color=color,
                )
                replacements += 1
        return replacements

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
            page_number = max(1, int(args.get("page_number", 1)))
            if page_number <= len(pdf_doc):
                page = pdf_doc[page_number - 1]
                page.insert_text(
                    point=(float(args.get("x", 72)), float(args.get("y", 72))),
                    text=str(args.get("text", "")),
                    fontsize=float(args.get("font_size", 11)),
                    color=self._color_tuple(args.get("color")),
                    fontname="helv",
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

            font_size = float(args.get("font_size", 11))
            font_name = str(args.get("font_family", "helv"))
            color = self._color_tuple(str(args.get("color", "black")))

            if tool_name == "set_text_style":
                style = str(args.get("style", ""))
                if style == "bold":
                    font_name = "helv"
                elif style == "italic":
                    font_name = "tiro"

            changed = self._replace_text(
                pdf_doc,
                old_text=target_text,
                new_text=transformed,
                fontsize=font_size,
                fontname=font_name,
                color=color,
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
