from typing import Any

import fitz


def apply_page_operations(executor, pdf_doc: fitz.Document, tool_name: str, args: dict[str, Any]) -> int:
    if tool_name == "add_page":
        position = args.get("position")
        page_number_str = args.get("page_number")
        source_page_str = args.get("source_page")
        if not isinstance(page_number_str, str) or not page_number_str.isdigit():
            raise ValueError("Invalid page_number for add_page")
        pno = int(page_number_str)
        if position == "before":
            pno -= 1
        elif position == "after":
            pass
        else:
            raise ValueError("Invalid position for add_page")
        if pno < 0:
            pno = 0
        source = None
        if source_page_str:
            if not isinstance(source_page_str, str) or not source_page_str.isdigit():
                raise ValueError("Invalid source_page for add_page")
            source_pno = int(source_page_str) - 1
            if 0 <= source_pno < len(pdf_doc):
                source = source_pno
        pdf_doc.insert_page(pno, source)
        return 1
    elif tool_name == "delete_page":
        page_number_str = args.get("page_number")
        if not isinstance(page_number_str, str) or not page_number_str.isdigit():
            raise ValueError("Invalid page_number for delete_page")
        page_number = int(page_number_str)
        if page_number < 1 or page_number > len(pdf_doc):
            raise ValueError("Invalid page_number for delete_page")
        pdf_doc.delete_page(page_number - 1)
        return 1
    elif tool_name == "reorder_pages":
        page_order_strs = args.get("page_order")
        if not isinstance(page_order_strs, list) or len(page_order_strs) != len(pdf_doc):
            raise ValueError("Invalid page_order for reorder_pages")
        page_order = []
        for p_str in page_order_strs:
            if not isinstance(p_str, str) or not p_str.isdigit():
                raise ValueError("Invalid page_order for reorder_pages")
            p = int(p_str)
            if p < 1 or p > len(pdf_doc) or p in page_order:
                raise ValueError("Invalid page_order for reorder_pages")
            page_order.append(p)
        pdf_doc.select([p - 1 for p in page_order])
        return len(pdf_doc)
    else:
        raise ValueError(f"Unsupported page tool: {tool_name}")
