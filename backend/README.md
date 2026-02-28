# Backend Structure Plan (V1)

This document defines the backend folder structure and implementation plan for V1.

## Goals for V1 Backend

- Support MCP-based deterministic text tools
- Run LangGraph orchestration for command-to-tool planning
- Integrate Groq for natural language command understanding
- Support draft/accept/reject versioning
- Support compare/history/tool log APIs
- Keep architecture scalable for V2 (structure, branding, AI features)

## Recommended Backend Tech Choices

- Framework: FastAPI
- Validation: Pydantic v2
- ORM: SQLAlchemy + Alembic
- Task queue (optional early): Celery/RQ (for heavy PDF ops)
- Storage:
  - Metadata: PostgreSQL
  - File assets: Cloudinary (PDFs, previews, thumbnails)
  - Cache/session/locks: Redis (optional in first cut)
- Observability: structlog + OpenTelemetry (add gradually)

---

## Scalable Folder Structure

```text
backend/
  README.md
  pyproject.toml
  .env.example
  alembic.ini
  Dockerfile

  app/
    main.py
    config/
      settings.py
      logging.py
      security.py

    api/
      deps.py
      router.py
      v1/
        health.py
        auth.py
        documents.py
        versions.py
        tools.py
        compare.py
        logs.py
        orchestration.py

    domain/
      documents/
        models.py
        schemas.py
        service.py
        repository.py
      versions/
        models.py
        schemas.py
        service.py
        repository.py
      tools/
        models.py
        schemas.py
        service.py
      logs/
        models.py
        schemas.py
        service.py
        repository.py

    mcp/
      registry.py
      schemas/
        replace_text.json
        add_text.json
        search_replace.json
        change_font_size.json
        change_font_color.json
        set_text_style.json
        convert_case.json
        highlight_text.json
        underline_text.json
        strikethrough_text.json
        extract_text.json
      validators.py
      errors.py

    orchestration/
      graph.py
      nodes/
        parse_command.py
        validate_plan.py
        execute_tools.py
        finalize_draft.py
      providers/
        groq_client.py
      planners/
        tool_planner.py

    pdf_engine/
      core/
        loader.py
        writer.py
        coordinates.py
      text_tools/
        replace_text.py
        add_text.py
        search_replace.py
        change_font_size.py
        change_font_color.py
        set_text_style.py
        convert_case.py
        highlight_text.py
        underline_text.py
        strikethrough_text.py
        extract_text.py
      render/
        thumbnails.py
        previews.py
        compare.py
      adapters/
        pymupdf_adapter.py

    storage/
      cloudinary_client.py
      asset_service.py
      paths.py

    db/
      session.py
      base.py
      models/
        user.py
        document.py
        document_version.py
        tool_execution_log.py
      migrations/

    jobs/
      queue.py
      workers/
        render_worker.py
        compare_worker.py

    common/
      constants.py
      enums.py
      exceptions.py
      utils.py
      idempotency.py

  tests/
    unit/
      mcp/
      pdf_tools/
      services/
    integration/
      api/
      orchestration/
    fixtures/
```

---

## Why This Structure Scales

- `api` handles transport concerns only (HTTP contracts).
- `domain` holds business logic and repositories.
- `mcp` keeps tool schemas and validation centralized.
- `orchestration` isolates LangGraph + Groq logic.
- `pdf_engine` isolates deterministic transformation logic.
- `storage` abstracts Cloudinary, so changing providers is easy.
- `jobs` supports async rendering/compare when load grows.

---

## V1 API Boundaries

- `POST /api/v1/documents/upload`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{document_id}`
- `POST /api/v1/documents/{document_id}/commands`
- `POST /api/v1/documents/{document_id}/drafts/{draft_id}/accept`
- `POST /api/v1/documents/{document_id}/drafts/{draft_id}/reject`
- `GET /api/v1/documents/{document_id}/versions`
- `GET /api/v1/documents/{document_id}/compare?from=...&to=...`
- `GET /api/v1/documents/{document_id}/tool-logs`
- `GET /api/v1/tools` (MCP registry)
- `GET /api/v1/tools/{tool_name}`

---

## Data Model (V1)

Core tables:

- `users`
- `documents`
- `document_versions`
  - states: `draft`, `accepted`, `rejected`
- `tool_execution_logs`
- `command_runs` (stores one user command + generated plan)

Key design:

- Only accepted versions are permanent.
- Draft versions can have TTL cleanup.
- Each accepted version references the base accepted version + operation log.
- Snapshot policy: full snapshot every N accepted operations.

---

## MCP and LangGraph Best Practices

1. MCP schema-first design
   - Every tool has strict input/output schema and error schema.
2. Validate before execute
   - Command plan must pass schema checks before PDF mutation.
3. Deterministic tool layer
   - LLM decides plan, tool execution remains deterministic.
4. Idempotency keys
   - Prevent duplicate tool runs when clients retry.
5. Traceability
   - Record `command -> tool plan -> tool runs -> version_id`.

---

## Suggested Implementation Order (Backend Only)

1. Project bootstrap (`app/main.py`, config, db session)
2. DB models + Alembic migrations
3. Cloudinary storage adapter
4. MCP registry + validators
5. Minimal PDF engine with 2 tools first (`replace_text`, `extract_text`)
6. Version service (`draft`, `accept`, `reject`)
7. LangGraph command pipeline with Groq planner
8. Remaining V1 text tools
9. Preview/thumbnail/compare endpoints
10. Tool log and audit endpoints
11. Tests (unit then integration)

---

## Commit Strategy (Recommended)

Use small, meaningful commits after each completed backend slice.

Examples:

- `feat(backend): bootstrap fastapi app and config`
- `feat(backend): add db models for documents versions and logs`
- `feat(backend): add mcp registry and schema validation`
- `feat(backend): implement replace_text and extract_text tools`
- `feat(backend): add draft accept reject version workflow`
- `feat(backend): add langgraph command orchestration with groq`
- `feat(backend): add thumbnails previews and compare endpoints`
- `test(backend): add unit tests for mcp validators and tools`

