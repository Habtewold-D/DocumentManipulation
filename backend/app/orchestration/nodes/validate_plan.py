import re

from app.mcp.validators import MCPValidationError, validate_tool_plan


def _parse_number(value: object) -> float | int | None:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            number = float(stripped)
            return int(number) if number.is_integer() else number
        except ValueError:
            return None
    return None


_ORDINAL_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}


def _parse_ordinal_token(token: str) -> int | None:
    normalized = token.strip().lower()
    if normalized in _ORDINAL_WORDS:
        return _ORDINAL_WORDS[normalized]

    match = re.match(r"(\d+)(?:st|nd|rd|th)?$", normalized)
    if match:
        return int(match.group(1))
    return None


def _parse_page_number_from_command(command: str) -> int | None:
    patterns = [
        r"\bpage\s+(\d+)\b",
        r"\bpage\s+(one|two|three|four|five|six|seven|eight|nine|ten|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b(?!\s+paragraph\b)",
        r"\b(\d+)(?:st|nd|rd|th)\s+page\b",
        r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+page\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, command, flags=re.IGNORECASE)
        if not match:
            continue
        parsed = _parse_ordinal_token(match.group(1))
        if parsed and parsed > 0:
            return parsed
    return None


def _parse_occurrence_from_command(command: str) -> int | None:
    patterns = [
        r"\b(\d+)(?:st|nd|rd|th)?\s+occurrence\b",
        r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+occurrence\b",
        r"\boccurrence\s+(\d+)(?:st|nd|rd|th)?\b",
        r"\boccurrence\s+(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, command, flags=re.IGNORECASE)
        if not match:
            continue
        parsed = _parse_ordinal_token(match.group(1))
        if parsed and parsed > 0:
            return parsed
    return None


def _parse_paragraph_index_from_command(command: str) -> int | None:
    patterns = [
        r"\b(\d+)(?:st|nd|rd|th)?\s+paragraph\b",
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+paragraph\b",
        r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+paragraph\b",
        r"\bparagraph\s+(\d+)(?:st|nd|rd|th)?\b",
        r"\bparagraph\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b",
        r"\bparagraph\s+(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, command, flags=re.IGNORECASE)
        if not match:
            continue
        parsed = _parse_ordinal_token(match.group(1))
        if parsed and parsed > 0:
            return parsed
    return None


def _extract_target_text_from_command(command: str) -> str | None:
    patterns = [
        r"\boccurrence\s+of\s+[\"']?(.+?)[\"']?(?=\s+to\s+\w+\b|\s+on\s+\w+\b|\s+in\s+\w+\b|\s+at\s+\w+\b|\s+from\s+\w+\b|\s+with\s+\w+\b|\s*$|[.,])",
        r"\bcolor\s+of\s+(?:the\s+)?(?:first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)?\s*(?:occurrence\s+of\s+)?[\"']?(.+?)[\"']?(?=\s+to\s+\w+\b|\s+on\s+\w+\b|\s+in\s+\w+\b|\s*$|[.,])",
        r"\bhighlight\s+(?:the\s+)?(?:first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)?\s*(?:occurrence\s+of\s+)?[\"']?(.+?)[\"']?(?=\s+on\s+\w+\b|\s+in\s+\w+\b|\s+at\s+\w+\b|\s+from\s+\w+\b|\s*$|[.,])",
        r"\bunderline\s+(?:the\s+)?(?:first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)?\s*(?:occurrence\s+of\s+)?[\"']?(.+?)[\"']?(?=\s+on\s+\w+\b|\s+in\s+\w+\b|\s+at\s+\w+\b|\s+from\s+\w+\b|\s*$|[.,])",
        r"\bstrikethrough\s+(?:the\s+)?(?:first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)?\s*(?:occurrence\s+of\s+)?[\"']?(.+?)[\"']?(?=\s+on\s+\w+\b|\s+in\s+\w+\b|\s+at\s+\w+\b|\s+from\s+\w+\b|\s*$|[.,])",
        r"\bremove\s+(?:the\s+)?(?:first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)?\s*(?:occurrence\s+of\s+)?[\"']?(.+?)[\"']?(?=\s+on\s+\w+\b|\s+in\s+\w+\b|\s+at\s+\w+\b|\s+from\s+\w+\b|\s*$|[.,])",
    ]
    for pattern in patterns:
        match = re.search(pattern, command, flags=re.IGNORECASE)
        if not match:
            continue
        extracted = match.group(1).strip()
        extracted = re.sub(r"^(?:the\s+)?(?:word|text|phrase|letter)\s+", "", extracted, flags=re.IGNORECASE).strip()
        extracted = extracted.strip(" \"'`")
        if extracted:
            return extracted
    return None


def _normalize_step_args(step: dict, document_id: str | None, command: str | None) -> None:
    args = step.setdefault("args", {})
    if not isinstance(args, dict):
        return

    if document_id and "document_id" not in args:
        args["document_id"] = document_id

    tool_name = step.get("tool")
    if not isinstance(tool_name, str):
        return

    target_text_tools = {
        "change_font_size",
        "change_font_color",
        "set_text_style",
        "convert_case",
        "highlight_text",
        "underline_text",
        "strikethrough_text",
    }

    if tool_name in target_text_tools and "target_text" not in args:
        for alias in ("text", "search", "word", "query", "old_text", "target"):
            value = args.get(alias)
            if isinstance(value, str) and value.strip():
                args["target_text"] = value
                break
        if "target_text" not in args and isinstance(command, str):
            extracted_target = _extract_target_text_from_command(command)
            if extracted_target:
                args["target_text"] = extracted_target

    if tool_name == "search_replace":
        if "search" not in args and isinstance(args.get("old_text"), str):
            args["search"] = args["old_text"]
        if "replace" not in args and isinstance(args.get("new_text"), str):
            args["replace"] = args["new_text"]

    if tool_name == "replace_text":
        if "old_text" not in args and isinstance(args.get("search"), str):
            args["old_text"] = args["search"]
        if "new_text" not in args and isinstance(args.get("replace"), str):
            args["new_text"] = args["replace"]

    if tool_name == "remove_text":
        if "old_text" not in args:
            for alias in ("target_text", "text", "search", "target", "value"):
                value = args.get(alias)
                if isinstance(value, str) and value.strip():
                    args["old_text"] = value.strip()
                    break
        if "old_text" not in args and isinstance(command, str):
            extracted_target = _extract_target_text_from_command(command)
            if extracted_target:
                args["old_text"] = extracted_target
        if "scope" not in args:
            args["scope"] = "all"

    if tool_name in {"extract_text", "replace_text", "remove_text", "search_replace"}:
        scope = args.get("scope")
        if isinstance(scope, str):
            normalized_scope = scope.strip().lower()
            if normalized_scope in {"page", "all"}:
                args["scope"] = normalized_scope
            else:
                args["scope"] = "page" if args.get("page_number") is not None else "all"
        elif "scope" not in args:
            args["scope"] = "all"

    targeting_tools = {
        "replace_text",
        "remove_text",
        "search_replace",
        "extract_text",
        "change_font_size",
        "change_font_color",
        "set_text_style",
        "convert_case",
        "highlight_text",
        "underline_text",
        "strikethrough_text",
    }
    if tool_name in targeting_tools:
        normalized_scope = args.get("scope")
        if isinstance(normalized_scope, str):
            scope_token = normalized_scope.strip().lower()
            if scope_token in {"page", "all"}:
                args["scope"] = scope_token
            else:
                args["scope"] = "page" if args.get("page_number") is not None else "all"

        page_num = _parse_number(args.get("page_number") if "page_number" in args else args.get("page"))
        if isinstance(page_num, (int, float)):
            int_page = int(page_num)
            if int_page > 0:
                args["page_number"] = int_page

        paragraph_num = _parse_number(args.get("paragraph_index") if "paragraph_index" in args else args.get("paragraph"))
        if isinstance(paragraph_num, (int, float)):
            int_paragraph = int(paragraph_num)
            if int_paragraph > 0:
                args["paragraph_index"] = int_paragraph

        if "occurrence" in args:
            occurrence_num = _parse_number(args.get("occurrence"))
            if isinstance(occurrence_num, (int, float)) and int(occurrence_num) > 0:
                args["occurrence"] = int(occurrence_num)
            else:
                args.pop("occurrence", None)

        if isinstance(command, str):
            if "page_number" not in args:
                command_page = _parse_page_number_from_command(command)
                if command_page is not None:
                    args["page_number"] = command_page

            if "paragraph_index" not in args:
                command_paragraph = _parse_paragraph_index_from_command(command)
                if command_paragraph is not None:
                    args["paragraph_index"] = command_paragraph

            if tool_name in {
                "replace_text",
                "remove_text",
                "search_replace",
                "change_font_size",
                "change_font_color",
                "set_text_style",
                "convert_case",
                "highlight_text",
                "underline_text",
                "strikethrough_text",
            } and "occurrence" not in args:
                command_occurrence = _parse_occurrence_from_command(command)
                if command_occurrence is not None:
                    args["occurrence"] = command_occurrence

        if "page_number" in args:
            args["scope"] = "page"
        elif "scope" not in args:
            args["scope"] = "all"

    if tool_name == "change_font_color" and "color" not in args:
        for alias in ("font_color", "text_color"):
            value = args.get(alias)
            if isinstance(value, str) and value.strip():
                args["color"] = value
                break

    if tool_name == "change_font_size":
        if "font_size" in args:
            normalized_size = _parse_number(args.get("font_size"))
            if normalized_size is not None:
                args["font_size"] = normalized_size
        if "font_size" not in args:
            for alias in ("size", "new_size", "value", "fontsize", "fontSize"):
                normalized_size = _parse_number(args.get(alias))
                if normalized_size is not None:
                    args["font_size"] = normalized_size
                    break
        if "font_size" not in args and isinstance(command, str):
            match = re.search(r"\b(?:to|size)\s+(\d+(?:\.\d+)?)\b", command.lower())
            if match:
                parsed = _parse_number(match.group(1))
                if parsed is not None:
                    args["font_size"] = parsed

        if "reference_text" not in args:
            for alias in ("reference", "reference_word", "same_as", "match_text", "relative_to"):
                value = args.get(alias)
                if isinstance(value, str) and value.strip():
                    args["reference_text"] = value
                    break

        if "reference_text" not in args and isinstance(command, str):
            reference_match = re.search(
                r"same\s+as\s+(?:word\s+)?[\"']?([^\"'.,\n]+)[\"']?",
                command,
                flags=re.IGNORECASE,
            )
            if reference_match:
                extracted = reference_match.group(1).strip()
                if extracted:
                    args["reference_text"] = extracted

        if "target_text" not in args and isinstance(command, str):
            if re.search(
                r"\b((first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)\s+paragraph|paragraph\s+(first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?|one|two|three|four|five|six|seven|eight|nine|ten))\b",
                command,
                flags=re.IGNORECASE,
            ):
                args["target_text"] = "__paragraph_target__"

    if tool_name == "add_text":
        auto_coordinates = False

        if "text" not in args:
            for alias in ("new_text", "content", "value", "insert_text"):
                value = args.get(alias)
                if isinstance(value, str) and value.strip():
                    args["text"] = value
                    break

        if "reference_text" not in args:
            for alias in ("anchor_text", "relative_to", "target_text", "below_text", "next_to_text"):
                value = args.get(alias)
                if isinstance(value, str) and value.strip():
                    args["reference_text"] = value
                    break

        if "position" not in args:
            placement = args.get("placement")
            if isinstance(placement, str) and placement.strip():
                args["position"] = placement

        if "position" not in args and isinstance(command, str):
            lowered = command.lower()
            if any(token in lowered for token in ("next to", "beside", "same line", "on same line", "inline")):
                args["position"] = "next"
            elif any(token in lowered for token in ("last part", "end of", "at the end", "append", "at the last", "to the last")):
                args["position"] = "end"
            elif any(token in lowered for token in ("below", "under")):
                args["position"] = "below"
            elif "above" in lowered:
                args["position"] = "above"

        if "reference_text" not in args and isinstance(command, str):
            patterns = [
                r"(?:next\s+to|beside|same\s+line\s+(?:with|as)|on\s+same\s+line\s+with|below|under|above)\s+[\"']?([^\"'\n,.]+)[\"']?",
                r"(?:with\s+text|with\s+word|to\s+text|to\s+word)\s+[\"']?([^\"'\n,.]+)[\"']?",
            ]
            for pattern in patterns:
                match = re.search(pattern, command, flags=re.IGNORECASE)
                if match:
                    extracted = match.group(1).strip()
                    if extracted:
                        args["reference_text"] = extracted
                        break

        if isinstance(command, str) and command.strip() and "command" not in args:
            args["command"] = command

        if "page_number" not in args:
            args["page_number"] = 1
            auto_coordinates = True
        if "x" not in args:
            args["x"] = 72
            auto_coordinates = True
        if "y" not in args:
            args["y"] = 72
            auto_coordinates = True

        if auto_coordinates:
            args["_auto_coordinates"] = True


def validate_plan(state: dict) -> dict:
    plan = state.get("plan")
    if not isinstance(plan, list):
        state["status"] = "failed"
        state["error"] = "Invalid plan format"
        return state

    document_id = state.get("document_id")
    command = state.get("command")
    if document_id:
        for step in plan:
            if isinstance(step, dict):
                _normalize_step_args(step, document_id, command)
    else:
        for step in plan:
            if isinstance(step, dict):
                _normalize_step_args(step, None, command)

    try:
        validate_tool_plan(plan)
    except MCPValidationError as error:
        state["status"] = "failed"
        state["error"] = str(error)
        return state

    state["status"] = "validated"
    return state
