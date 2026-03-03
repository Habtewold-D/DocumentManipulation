import re

from app.orchestration.providers.groq_client import GroqClient

class ToolPlanner:
    def __init__(self) -> None:
        self.client = GroqClient()

    def create_plan(self, command: str, image_url: str | None = None) -> dict:
        command_lower = command.lower()

        # Page operation fallbacks
        add_page_match = re.search(r'\b(add|insert)\s+(?:a\s+)?(?:blank\s+|new\s+|black\s+)?page\s+(before|after)\s+(?:page\s+)?(\d+)', command, re.IGNORECASE)
        if add_page_match:
            position = add_page_match.group(2).lower()
            page_number = str(add_page_match.group(3))
            return {
                "status": "fallback",
                "plan": [{"tool": "add_page", "args": {"position": position, "page_number": page_number}}],
            }

        delete_page_match = re.search(r'\b(?:delete|remove)\s+page\s+(\d+)', command, re.IGNORECASE)
        if delete_page_match:
            page_number = str(delete_page_match.group(1))
            return {
                "status": "fallback",
                "plan": [
                    {
                        "tool": "delete_page",
                        "args": {
                            "page_number": page_number,
                        },
                    }
                ],
            }

        reorder_match = re.search(r'reorder pages to ([\d,\s]+)', command, re.IGNORECASE)
        if reorder_match:
            order_str = reorder_match.group(1)
            page_order = [str(p.strip()) for p in order_str.split(',') if p.strip().isdigit()]
            if page_order:
                return {
                    "status": "fallback",
                    "plan": [
                        {
                            "tool": "reorder_pages",
                            "args": {
                                "page_order": page_order,
                            },
                        }
                    ],
                }

        insert_match = re.search(r'\b(insert|add)\s+(?:an?\s+)?image\s+(?:from\s+)?([^\s]+)\s+on\s+page\s+(\d+)\s+at\s+(\d+),\s*(\d+)\s+size\s+(\d+)x(\d+)', command, re.IGNORECASE)
        if insert_match:
            image_url = insert_match.group(2)
            page_number = str(insert_match.group(3))
            x = int(insert_match.group(4))
            y = int(insert_match.group(5))
            width = int(insert_match.group(6))
            height = int(insert_match.group(7))
            return {
                "status": "fallback",
                "plan": [
                    {
                        "tool": "insert_image",
                        "args": {
                            "image_url": image_url,
                            "page_number": page_number,
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                        },
                    }
                ],
            }

        resize_match = re.search(r'\bresize\s+image\s+on\s+page\s+(\d+)\s+index\s+(\d+)\s+to\s+(\d+)x(\d+)', command, re.IGNORECASE)
        if resize_match:
            page_number = str(resize_match.group(1))
            image_index = str(resize_match.group(2))
            new_width = int(resize_match.group(3))
            new_height = int(resize_match.group(4))
            return {
                "status": "fallback",
                "plan": [
                    {
                        "tool": "resize_image",
                        "args": {
                            "page_number": page_number,
                            "image_index": image_index,
                            "new_width": new_width,
                            "new_height": new_height,
                        },
                    }
                ],
            }

        rotate_match = re.search(r'\brotate\s+image\s+on\s+page\s+(\d+)\s+index\s+(\d+)\s+by\s+(\d+)\s+degrees?', command, re.IGNORECASE)
        if rotate_match:
            page_number = str(rotate_match.group(1))
            image_index = str(rotate_match.group(2))
            angle = int(rotate_match.group(3))
            return {
                "status": "fallback",
                "plan": [
                    {
                        "tool": "rotate_image",
                        "args": {
                            "page_number": page_number,
                            "image_index": image_index,
                            "angle": angle,
                        },
                    }
                ],
            }

        # Natural insert image commands
        insert_image_intent = re.search(r'\b(insert|add|put|place)\s+(?:this\s+|an?\s+)?image\b', command, re.IGNORECASE)
        if insert_image_intent and image_url:
            ordinal_map = {
                "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
                "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10",
            }

            page_token_match = re.search(
                r'\b(?:before|after|top|bottom)\b.*?\b(?:page\s+)?(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s*(?:page)?\b',
                command,
                re.IGNORECASE,
            )
            page_token = page_token_match.group(1).lower() if page_token_match else "1"
            page_number = ordinal_map.get(page_token, page_token)

            before_match = re.search(r'\bbefore\s+(?:the\s+)?(?:page\s+)?(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b', command, re.IGNORECASE)
            after_match = re.search(r'\bafter\s+(?:the\s+)?(?:page\s+)?(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b', command, re.IGNORECASE)
            end_match = re.search(r'\b(?:at\s+)?(?:the\s+)?end\s+of\s+(?:the\s+)?(?:page\s+)?(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s*(?:page)?\b', command, re.IGNORECASE)
            on_page_match = re.search(r'\bon\s+(?:the\s+)?(?:page\s+)?(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+page\b|\bon\s+(?:the\s+)?(?:page\s+)?(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b', command, re.IGNORECASE)
            top_match = re.search(r'\b(?:at|in|on)\s+the\s+top\s+of\s+(?:the\s+)?(?:(?:page\s+)?(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)|(?:\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+page)\b', command, re.IGNORECASE)
            bottom_match = re.search(r'\b(?:at|in|on)\s+the\s+bottom\s+of\s+(?:the\s+)?(?:(?:page\s+)?(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)|(?:\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+page)\b', command, re.IGNORECASE)
            above_match = re.search(r'\babove\s+(.+)$', command, re.IGNORECASE)
            below_match = re.search(r'\bbelow\s+(.+)$', command, re.IGNORECASE)

            position = "top"
            anchor_text = None

            if before_match:
                page_number = ordinal_map.get(before_match.group(1).lower(), before_match.group(1))
                page_number = str(max(1, int(page_number) - 1))
                position = "top"
            elif after_match:
                page_number = ordinal_map.get(after_match.group(1).lower(), after_match.group(1))
                page_number = str(int(page_number) + 1)
            elif end_match:
                page_number = ordinal_map.get(end_match.group(1).lower(), end_match.group(1))
                position = "bottom"
            elif top_match:
                token = top_match.group(1)
                if token:
                    page_number = ordinal_map.get(token.lower(), token)
                position = "top"
            elif bottom_match:
                token = bottom_match.group(1)
                if token:
                    page_number = ordinal_map.get(token.lower(), token)
                position = "bottom"
            elif on_page_match:
                token = on_page_match.group(1) or on_page_match.group(2)
                if token:
                    page_number = ordinal_map.get(token.lower(), token)
                position = "top"

            if above_match:
                anchor_candidate = above_match.group(1).strip().strip('"\'`')
                anchor_candidate = re.sub(r'^(?:this\s+|the\s+)?(?:paragraph|text)\s+', '', anchor_candidate, flags=re.IGNORECASE).strip()
                if anchor_candidate and anchor_candidate.lower() not in {"this", "paragraph", "text"}:
                    anchor_text = anchor_candidate
                position = "above"

            if below_match:
                anchor_candidate = below_match.group(1).strip().strip('"\'`')
                anchor_candidate = re.sub(r'^(?:this\s+|the\s+)?(?:paragraph|text)\s+', '', anchor_candidate, flags=re.IGNORECASE).strip()
                if anchor_candidate and anchor_candidate.lower() not in {"this", "paragraph", "text"}:
                    anchor_text = anchor_candidate
                position = "below"

            return {
                "status": "fallback",
                "plan": [
                    {
                        "tool": "insert_image",
                        "args": {
                            "image_url": image_url,
                            "page_number": str(page_number),
                            "position": position,
                            "anchor_text": anchor_text,
                        },
                    }
                ],
            }

        plan = self.client.plan(command)

        remove_prefix_match = re.match(r"^\s*(?:remove|delete)\s+(?:the\s+)?(?:text\s+)?(.+)$", command, flags=re.IGNORECASE | re.DOTALL)
        if remove_prefix_match:
            candidate = remove_prefix_match.group(1).strip().strip('"\'')
            if candidate:
                return {
                    "status": "fallback",
                    "plan": [
                        {
                            "tool": "remove_text",
                            "args": {
                                "old_text": candidate,
                                "scope": "all",
                            },
                        }
                    ],
                }

        if plan.get("plan"):
            plan_steps = plan.get("plan", []) if isinstance(plan, dict) else []
            if (
                isinstance(plan_steps, list)
                and len(plan_steps) == 1
                and isinstance(plan_steps[0], dict)
                and plan_steps[0].get("tool") == "extract_text"
                and any(token in command_lower for token in ("remove ", "delete "))
            ):
                extract_args = plan_steps[0].get("args", {}) if isinstance(plan_steps[0].get("args", {}), dict) else {}
                target = str(
                    extract_args.get("target_text", "")
                    or extract_args.get("text", "")
                    or extract_args.get("query", "")
                ).strip()
                if target:
                    return {
                        "status": "fallback",
                        "plan": [
                            {
                                "tool": "remove_text",
                                "args": {
                                    "old_text": target,
                                    "scope": "all",
                                },
                            }
                        ],
                    }
            return plan

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

        remove_match = re.search(
            r"\b(?:remove|delete)\s+(?:the\s+)?(?:text\s+)?[\"']?([^\"'\n,.]+)[\"']?",
            command,
            flags=re.IGNORECASE,
        )
        if remove_match:
            target = remove_match.group(1).strip()
            if target:
                return {
                    "status": "fallback",
                    "plan": [
                        {
                            "tool": "remove_text",
                            "args": {
                                "old_text": target,
                                "scope": "all",
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
