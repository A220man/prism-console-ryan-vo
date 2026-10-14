# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 - 2026-10-14

First checkpoint of Prism Console.

- Score declared IPC, HTTP, and function surfaces into one grounded command per surface.
- Extract module-level Python functions, a small FastAPI-style decorator form, and `ipcMain.handle` callbacks with an identifier parameter list.
- Compare coverage and correctness with a thin `start` / `stop` / `status` / `chat` / `meeting` baseline.
- Store analyses and an audit log in SQLite. List, filter, open, and export them from the web UI.
- Report precision and recall for both generators on the hand-labeled cases in `backend/app/core/evaluate.py`.

This checkpoint does not authenticate callers, call a language model, or launch the target application.
