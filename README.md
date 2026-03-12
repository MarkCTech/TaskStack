# TaskStack

Flask + MySQL API with a React SPA. When setup is done, open **http://localhost:5000**.

---

## Run the project (after first-time setup)
From the **project root** (folder that contains `main.py`), in a **new terminal**:

Activate the venv:
>PowerShell:
>```bash
>.\.venv\Scripts\Activate.ps1
>```
>Linux/macOS:
>```bash
>source .venv/bin/activate
>```

 Run the server:

>```bash
>python main.py
>```
Rebuild the frontend only when the repo changed:

>```bash
>python scripts/build_frontend.py
>```
---

## What you need installed

Python 3, Git, Node.js (LTS), MySQL, Redis. MySQL must have the app database (`taskstack`). Clone the repo and work from the project root (`taskstack` after clone, or whatever folder you use).

---

## First-time setup

Do these in order. Stop if a step fails.

### Step 1 — Virtual environment (once) & activate

**Once:** create `.venv` in the project (holds this project’s Python and packages).

>PowerShell:
>```bash
>python -m venv .venv
>```
>Linux/macOS:
>```bash
>python3 -m venv .venv
>```

#### Activate the venv

**Do this in every new terminal** before `python` or `pip`. 
Skip only if already activated in that same terminal.

>PowerShell:
>```bash
>.\.venv\Scripts\Activate.ps1
>```
>Linux/macOS:
>```bash
>source .venv/bin/activate
>```

If PowerShell blocks scripts, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

When the venv is on, your prompt usually shows `(.venv)`.

---

### Step 2 — Install Python packages

With the venv **activated**:

>```bash
>pip install -r requirements.txt
>pip install -r requirements-dev.txt
>```

`requirements.txt` runs the app. `requirements-dev.txt` adds test and lint tools.

---

### Step 3 — Config file `.env`

Copy the example file to **`.env`** in the project root (next to **`main.py`**).

>PowerShell:
>```bash
>Copy-Item .env.example .env
>```
>Linux/macOS:
>```bash
>cp .env.example .env
>```

You must set **`FLASK_SECRET_KEY`**. Generate one:

>```bash
>python -c "import secrets; print(secrets.token_urlsafe(48))"
>```

Put that value in **`.env`** as **`FLASK_SECRET_KEY=...`**. 
The rest of `.env.example` is usually fine for local use.

---

### Step 4 — Build the frontend

The React app lives in **`client/frontend/`** (committed with this repo) and is built into **`client/webapp_build`**.

Run:

>```bash
>python scripts/build_frontend.py
>```

Run again after frontend changes. To clean and rebuild, delete **`client/webapp_build`** (and optionally **`client/frontend/node_modules`**) then run the script again.

---

### Step 5 — Run the server

With the venv **activated**:

>```bash
>python main.py
>```

Enter MySQL username and password when asked. Then open **http://localhost:5000**.

---

## Later runs

Open a terminal in the project root → **activate the venv** → `python main.py`. 
Re-run the frontend build only when the frontend changed.

---

## CI and tests

GitHub Actions creates `.venv`, installs both requirement files, then runs **`make ci`** (lint + test).

To run checks on your machine: activate the venv, then:

>```bash
>make ci
>```

Workflow file: `.github/workflows/ci.yml`.

---

## `.env` reference

| Variable | Required | Notes |
|----------|----------|--------|
| `FLASK_SECRET_KEY` | Yes | Session signing |
| `REDIS_URL` | Yes | e.g. `redis://localhost:6379/0` |
| `CORS_ORIGINS` | Yes | e.g. `http://localhost:5000` |
| `SESSION_COOKIE_SECURE` | No | `false` for local http if cookies fail |
| `FRONTEND_STATIC_FOLDER` | No | Default `./client/webapp_build` |

Environment variables override `.env` when both are set.
See `.env.example` for the full list.

---

## Troubleshooting

**Windows: `pip install` errors about `dotenv` or `.deleteme`**  
Use a venv (Step 1). Install into the venv, not globally.

**Windows: frontend build cannot find `npm`**  
Install Node LTS. Close the terminal and open a new one so `PATH` includes npm. Run Step 4 again.

**Browser shows errors, no UI**  
Run Step 4. You need `client/webapp_build/index.html`.

---

## When you’re done

**Stopping work:** Press **Ctrl+C** in the terminal where the server is running, then close PowerShell if you like. You don’t have to “deactivate” the venv—closing the window is fine.

**Next time:** Open a new terminal, **activate the venv** again (same commands as Step 1), then `python main.py`. The `.venv` folder stays so you usually skip reinstalling packages.

**Removing the venv completely:** Delete the `.venv` folder (or run `make clean`). Next session you’ll repeat Step 1–2.
