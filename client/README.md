# Frontend

Flask serves **`client/webapp_build`**.

1. Set **`FRONTEND_REPO`** and **`FRONTEND_BRANCH`** at the top of the root **Makefile** (the build script reads them).
2. From the repo root:
   ```bash
   python scripts/build_frontend.py
   ```
   First run clones into `client/frontend-src/`; later runs pull + build. If `npm` is missing, the script may suggest `winget` / `brew`.

To clean and rebuild: delete `client/frontend-src` and `client/webapp_build`, then run the script again.
