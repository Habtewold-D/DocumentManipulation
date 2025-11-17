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
- change_font_type
- change_font_size
- change_font_color
- set_text_style (bold/italic)
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
