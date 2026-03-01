# AI Document Agent Platform (V1)

This repo will host an AI-powered PDF document agent platform. V1 includes both deterministic PDF tools and AI-powered tools, all exposed through MCP schemas and orchestrated via LangGraph. Groq will be used as the LLM provider for command understanding and tool planning.

## Product Scope

### V1 (Core Text Editing Tools)
V1 delivers a functional end-to-end experience: upload PDF, edit via text tools, version and review changes, and view history.

#### 1) Deterministic PDF Tools (MCP)
These are structured as MCP tools with strict input/output schemas.

**Text Editing Tools**
- replace_text
- add_text
- search_replace
- `change_font_size`: Adjust text size.
- `change_font_color`: Modify text color.
_style (bold/italic)
- convert_case
- highlight_text
- underline_text
- strikethrough_text
- extract_text (full or per-page)

**Document Structure Controls**
- Planned for V2

**Visual Branding Controls**
- Planned for V2

#### 2) V1 User Experience
- Upload a PDF
- Open editor workspace
- Execute a tool via AI command routing
- Preview the change
- Accept or reject the change
- View history, compare versions, and switch

#### 3) V1 System Responsibilities
**Frontend (Next.js)**
- Landing page
- Dashboard (document list + upload)
- Editor workspace (viewer, thumbnails, preview images, version list, diff/compare, tool log)
- Chat/command input (structured commands or natural language with confirmation)

**Backend (FastAPI)**
- File storage for originals and versions
- Tool execution pipeline
- MCP tool registry
- Version control and audit logs
- Change review workflow (accept/reject)
- Version compare service (render preview images for two versions)

**LangGraph (V1 Orchestrator)**
- Reads user command
- Plans tool sequence (text tools only)
- Executes tools via MCP registry
- Returns draft preview or accepted version

**LLM Provider (V1)**
- Groq is used for command understanding and tool planning

---

### V2 (Structure + Branding + AI)
These are added after V1 text tools are stable.

**Text Editing Additions**
- remove_text

**Document Structure Controls**
- add_page
- delete_page
- reorder_pages
- insert_image
- resize_image
- rotate_image

**Visual Branding Controls**
- add_watermark (text or image)
- add_header
- add_footer
- add_page_numbers
- change_page_background

**AI-Powered Features**
- Summarize PDF content
- Rephrase / improve text
- Translate PDF text
- Detect inconsistencies or duplicates
- Extract tables into CSV / Excel

### Later (Harder Features)
These are technically harder and come after V2.

- Remove watermarks (requires detection)
- Replace existing images (requires object detection)
- Remove images (layout-aware deletion)
- Automatically create table of contents (structure detection)

---

## Pre-V2 Hardening Plan (Make V1 Production-Ready First)

Before implementing V2 features, harden V1 for reliability, scale, and safe rollouts.

### 1) Move Heavy Work to Background Jobs
Move the following to background workers/queues:
- Command execution pipeline (LangGraph + tool execution + PDF rewrite + upload + preview manifest)
- Version retention cleanup (stale drafts, rejected versions, old accepted versions asset deletion)

Keep synchronous for now:
- Compare endpoint based on preview-manifest hashes (already lightweight)
- PDF preview fetch endpoint (user waits for immediate render)

### 2) Add Command Run Lifecycle API
- `POST /documents/{id}/commands` returns `202` + `run_id` (queued)
- `GET /commands/{run_id}` returns status/progress/result/error
- `POST /commands/{run_id}/cancel`
- `POST /commands/{run_id}/retry`
- `GET /documents/{id}/commands` history

### 3) Add Feature Flags + Shadow Execution (Recommended)
Yes, this should be done before V2 rollout.

Suggested flags/modes:
- `V2_EXECUTION_MODE=off|shadow|canary|on`
- `V2_CANARY_PERCENT=0..100`

Behavior:
- `off`: V1 only
- `shadow`: V1 result is returned; V2 runs in background for comparison only
- `canary`: selected % of traffic executes V2 as primary, fallback to V1 on failure
- `on`: V2 primary for all traffic

### 4) Observability and Safety Nets
- Per-tool and per-command timing metrics
- Structured error taxonomy (validation/tool/pdf/storage)
- Correlation IDs in logs and run records
- Golden regression tests for critical text flows
- Idempotency key coverage on async submission path

---

## V2 Delivery Order (Recommended)

Deliver V2 in this order to reduce risk and dependency churn.

### Phase A: V2 Foundation
1. `remove_text` (low surface area; builds confidence in text-flow safety)
2. Feature-flag + shadow execution path live for all new V2 tools

### Phase B: Document Structure Controls
3. `add_page`
4. `delete_page`
5. `reorder_pages`
6. `rotate_image`
7. `insert_image`
8. `resize_image`

### Phase C: Visual Branding Controls
9. `add_header`
10. `add_footer`
11. `add_page_numbers`
12. `add_watermark` (text, then image)
13. `change_page_background`

### Phase D: AI-Powered Features
14. Summarize PDF content
15. Rephrase / improve text
16. Translate PDF text
17. Detect inconsistencies or duplicates
18. Extract tables into CSV / Excel

### Phase E: Later (Harder Features)
19. Remove watermarks (requires detection)
20. Replace existing images (requires object detection)
21. Remove images (layout-aware deletion)
22. Automatically create table of contents (structure detection)

---

## MCP (Model Context Protocol) Standards
All tools follow MCP style schemas for predictable tool invocation.

Example (replace_text):

```json
{
  "tool": "replace_text",
  "input_schema": {
    "document_id": "string",
    "old_text": "string",
    "new_text": "string",
    "scope": "page|all",
    "page_number": "number?"
  },
  "output_schema": {
    "success": "boolean",
    "pages_modified": "number[]",
    "version_id": "string",
    "message": "string?"
  }
}
```

---

## Architecture Overview

### Frontend (Next.js)
- App Router
- PDF viewer component
- Thumbnails with drag/drop reorder
- Version list + history
- Tool log panel
- Chat/command input

### Backend (FastAPI)
- Document CRUD
- Versioning
- Tool execution
- MCP registry endpoints

### LangGraph
- Orchestrator routes commands to MCP tools
- Supports deterministic and AI tools
- Multi-agent expansion later

---

## Command Understanding and Tool Planning (Groq + LangGraph)
User commands are free-form English. The system:

1. Sends the command to Groq for intent + tool plan
2. Validates the plan against MCP schemas
3. Executes tools in order via LangGraph
4. Produces a draft version for review
5. Commits the change only on user acceptance

This keeps tool execution deterministic while allowing flexible user instructions.

---

## Versioning Strategy (Accept/Reject + Storage Efficiency)
Storing a full PDF per change can be memory-intensive. Use a two-layer model:

**Draft Layer (During Editing)**
- Each tool run generates a draft version
- Drafts are temporary and can be rejected
- Only accepted drafts become permanent versions

**Permanent Layer (Accepted Versions)**
- Store accepted versions only
- Maintain a tool-operation log for each accepted version
- Create periodic full snapshots (e.g., every N operations) to avoid long replay chains

**Diff/Compare (V1)**
- Generate preview images per page for each accepted version
- Compare two versions by showing side-by-side preview images
- Optionally highlight changed pages by diffing page-level image hashes

This supports your "accept/reject" workflow while keeping storage efficient.

---

## Storage Plan (Cloudinary)
Cloudinary can store:

- Original PDFs
- Accepted version snapshots
- Thumbnails and preview images

Drafts can be stored in a temporary bucket with short TTL or kept in object storage until acceptance.

---

## Vector Storage (Do You Need It?)
Not required for V1 tool execution. Add vector storage only if you want:

- Semantic search across documents
- Retrieval-augmented QA on PDFs
- Similarity-based duplicate detection

If those are not in V1 scope, skip vector storage for now.

---

## V1 Roadmap (Detailed)

### Phase 0: Product Definition (1-2 days)
- Freeze V1 tool list
- Define MCP schemas
- Finalize UX flows

### Phase 1: Backend Foundations (1-2 weeks)
- Storage and versioning layer
- MCP registry and validation
- Tool execution service

### Phase 2: Frontend Foundations (1-2 weeks)
- Landing + dashboard
- Editor workspace layout
- PDF viewer + thumbnails
- Preview image rendering
- Version list + compare UI
- Tool log panel

### Phase 3: Tool Execution UX (1 week)
- Structured tool command input
- Tool validation UX
- Draft preview + accept/reject flow
- Compare draft vs last accepted version

### Phase 4: LangGraph + Groq Integration (1 week)
- Orchestrator agent
- Groq-based command planning
- Text-tool routing only (V1)

### Phase 5: Quality and Release (1 week)
- Tests for tools and versioning
- Error handling
- Logging and audit

---

## What To Do Next (Action Plan)

1. Confirm V1 tool list and MCP schemas
2. Decide storage approach (local vs object storage)
3. Decide auth approach (single-tenant vs multi-user)
4. Decide command UX (structured-only vs natural language + confirmation)
5. Start backend foundations

---

## README Maintenance During Development
This README should evolve alongside the build. Use this process:

1. **Keep a short "Status" section**
   - Track current phase, last completed milestone, and next task

2. **Update "Roadmap" checkboxes**
   - Mark phases and tools as implemented

3. **Add a "Decisions" log**
   - Record key choices (storage, auth, PDF engine, MCP schema changes)

4. **Keep "API" and "Schemas" current**
   - Update endpoints and tool definitions when they change

5. **Add a "How to Run" section once bootstrapped**
   - Include frontend and backend setup commands

If you want, I can keep the README updated as we build by adding a short progress section every time we implement a feature.
