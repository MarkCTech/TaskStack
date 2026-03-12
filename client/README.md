# Frontend

Source: **`client/frontend/`** (React app, committed with TaskStack).

Flask serves the production build from **`client/webapp_build`** (generated; gitignored).

From the repo root:

```bash
python scripts/build_frontend.py
```

If `npm` is missing, the script may suggest `winget` / `brew`.

To clean and rebuild: delete `client/webapp_build` (and optionally `client/frontend/node_modules`), then run the script again.
