import json
from typing import Any

from groq import Groq

from app.config.settings import settings


class GroqClient:
    def __init__(self) -> None:
        self._enabled = bool(settings.groq_api_key)
        self._client = Groq(api_key=settings.groq_api_key) if self._enabled else None

    def plan(self, command: str) -> dict[str, Any]:
        if not self._enabled or self._client is None:
            return {"status": "disabled", "plan": []}

        system_prompt = (
            "You are an MCP planner for a PDF editor. "
            "Return strict JSON only with shape: {\"plan\":[{\"tool\":string,\"args\":object}]}. "
            "Use only these tools: replace_text, add_text, search_replace, change_font_type, "
            "change_font_size, change_font_color, set_text_style, convert_case, highlight_text, "
            "underline_text, strikethrough_text, extract_text. "
            "Required args: replace_text(old_text,new_text,scope), search_replace(search,replace), "
            "add_text(text,page_number,x,y), extract_text(scope). "
            "If command is ambiguous and missing critical values, return {\"plan\":[]}"
        )

        response = self._client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        plan = parsed.get("plan", []) if isinstance(parsed, dict) else []
        if not isinstance(plan, list):
            plan = []

        return {"status": "ok", "plan": plan}
