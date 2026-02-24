from app.orchestration.providers.groq_client import GroqClient


class ToolPlanner:
    def __init__(self) -> None:
        self.client = GroqClient()

    def create_plan(self, command: str) -> dict:
        plan = self.client.plan(command)
        if plan.get("plan"):
            return plan

        command_lower = command.lower()
        import re
        # 1. High-precision extraction for long multi-paragraph requests
        # Use first match to split, and support "below to", "next to both" etc.
        spatial_pattern = r'\b(below to|below|after|next to both|next to|above|beside)\b'
        # FIND LAST MATCH: Avoids issues where the user's CONTENT includes spatial keywords.
        matches = list(re.finditer(spatial_pattern, command, re.IGNORECASE | re.DOTALL))
        spatial_match = matches[-1] if matches else None
        
        if spatial_match:
            used_keyword = spatial_match.group(1).lower()
            parts = [command[:spatial_match.start()], command[spatial_match.end():]]
            
            raw_content = parts[0]
            raw_anchor = parts[1]
            
            # Content cleaning
            text = raw_content.strip()
            # Rigorous verb stripping
            text = re.sub(r'^(add this paragraph|add this text|add a paragraph|add the text|add text|add paragraph|add)\s*', '', text, flags=re.IGNORECASE)
            
            # Extract anchor string
            anchor = raw_anchor.strip()
            # Fuzzier matching for fillers
            anchor = re.sub(r'^(to this|to the|to both|to|of this|of the|of|this|the|is the|is)\s+', '', anchor, flags=re.IGNORECASE)
            
            # Additional cleanup for anchor verbs if content was split early
            anchor = re.sub(r'^(this paragraph|this text|this|the)\s*', '', anchor, flags=re.IGNORECASE)
            anchor = anchor.strip()
            
            # Determine intent STRICTLY from the starting verb phrase
            # This prevents content like "the scholarship paragraph" from overriding the intent.
            intent_verb_match = re.search(r'^(add|insert)\s+(this\s+)?(paragraph|text)\b', command.strip(), re.IGNORECASE)
            if intent_verb_match:
                intent = "paragraph" if "paragraph" in intent_verb_match.group(0).lower() else "text"
            else:
                intent = "paragraph" if "paragraph" in command_lower else "text"
            
            # LOGGING: Helps debug if the planner is splitting correctly
            print(f"[ToolPlanner] Action Intent: {intent}")
            print(f"[ToolPlanner] Split by '{used_keyword}': Content='{text[:30]}...', Anchor='{anchor[:30]}...'")

            # Replace internal newlines with spaces to allow natural reflow
            content_clean = " ".join(text.split())
            
            # RECURSIVE CLEANING: Strip conversational fluff and tool verbs from the start
            prefixes = [
                r"^for\s+this\s+", r"^this\s+", r"^(add|insert)\s+(the\s+|this\s+)?(paragraph|text)\s*", r"^add\s+", r"^insert\s+"
            ]
            changed = True
            while changed:
                changed = False
                for p in prefixes:
                    match = re.search(p, content_clean, re.IGNORECASE)
                    if match:
                        content_clean = content_clean[match.end():].strip()
                        changed = True
                        break

            # TRUNCATE ANCHOR: Use a 15-word window for identifying search during planning
            final_anchor = " ".join(anchor.split()[:15])
            
            return {
                "status": "fallback",
                "plan": [
                    {
                        "tool": "add_text",
                        "args": {
                            "text": content_clean or "New content",
                            "anchor_text": final_anchor or "the paragraph",
                            "position": used_keyword or "below",
                            "intent": intent
                        },
                    }
                ],
            }

        return {
            "status": "fallback",
            "plan": [
                {
                    "tool": "replace_text",
                    "args": {
                        "old_text": "from",
                        "new_text": "to",
                        "scope": "all",
                    },
                }
            ],
        }
