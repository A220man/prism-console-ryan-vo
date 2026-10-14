# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

catalog-from-surfaces

## Roadmap

### catalog-from-surfaces — Source-grounded CLI catalog and thin-baseline score

Status: done

Acceptance:
- A caller can submit declared surfaces or a supported Python/ipcMain source subset and receive one grounded command per surface.
- Each command is marked executable only when the handler, route, and required flags bind.
- The same inventory is scored against a fixed start/stop/status/chat/meeting baseline.
- Analyses persist in SQLite and can be listed, filtered, opened, and exported.
- The labeled evaluation command reports precision and recall for both generators.

Implementation: `backend/app/core/catalog.py`, `backend/app/core/extract.py`, `backend/app/core/evaluate.py`, `backend/app/services/store.py`, `backend/app/api/routes.py`, `backend/app/main.py`, `frontend/src/App.tsx`, `frontend/src/api.ts`, `frontend/src/components/CatalogReport.tsx`, `frontend/src/components/EvaluationPanel.tsx`

Tests: `backend/tests/test_catalog.py`, `backend/tests/test_extract.py`, `backend/tests/test_evaluate.py`, `backend/tests/test_api.py`, `frontend/src/App.test.tsx`

### argv-replay — Replay a user-supplied argv against a saved command

Status: planned

Acceptance:
- A saved analysis accepts an argv and returns the bound parameters or the bind failure.

### agent-proposal-score — Score an agent-authored command list

Status: planned

Acceptance:
- A pasted command list is compared with the grounded executable set and returns precision and recall.

### llm-advisory — Optional advisory explanation of bind failures

Status: planned

Acceptance:
- When LLM_API_KEY is set, a failure explanation is requested from the configured provider and labeled advisory.
- Missing or failing provider calls return an error and do not invent a successful explanation.

### oidc-session — Keycloak OIDC login and role checks

Status: planned

Acceptance:
- Authorization-code login with state, nonce, and PKCE protects every data endpoint.
- Viewer, operator, and admin roles are enforced, and logout clears the session.

