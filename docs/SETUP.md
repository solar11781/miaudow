# Setting up Miaudow

This guide explains how to run Miaudow on your own computer, how to turn on its optional features, how to run the
tests and how to rebuild the data from the original downloads. Commands are run from the repository root unless a
step says otherwise.

You do not need to rebuild the data to run the app. The computed results (`artifacts/`), the rules files (`rules/`)
and the farmland weights (`data/processed/cell_weights.csv`) are committed, so the app works straight after a clone.

## 1. What you need

| Tool | Version | Needed for |
| --- | --- | --- |
| Git | any recent version | getting the code |
| Python | 3.12 or newer (CI and the Docker image use 3.13) | the backend, the tests and the data pipeline |
| Node.js | 22 (with npm) | the frontend |
| Docker | any recent version | optional: the one-command run (section 3), the sign-in tests and a local database |
| Microsoft Edge | any recent version | optional: the browser tests on your own computer (section 6.3) |
| Bash | Git Bash on Windows, the normal shell on macOS and Linux | optional: the data pipeline (section 7) |

## 2. Get the code

```bash
git clone https://github.com/solar11781/miaudow.git
cd miaudow
```

## 3. Quickest way: run everything with Docker

The `Dockerfile` builds the frontend and the backend into one image. This is the same image that runs on Railway.

```bash
docker build -t miaudow .
docker run --rm -p 8000:8000 miaudow
```

Open http://localhost:8000. The app starts in Vietnamese if your browser lists Vietnamese, otherwise in English; the
button at the top right switches the language. The optional features of section 5 are off in this run. To turn one
on, pass only its settings with `-e`, for example:

```bash
docker run --rm -p 8000:8000 -e ANTHROPIC_API_KEY=<your key> -e FIELDSHIFT_EXPLAIN=1 miaudow
```

Do not pass a copy of `.env.example` with `--env-file`: its empty `PORT=` and `FIELDSHIFT_ROOT=` lines would override
the image's own values and the server would not start.

## 4. Run it for development

Development uses two processes: the Python backend on port 8000 and the frontend development server, which reloads
the page when you change a file.

### 4.1 Backend

Create a virtual environment and install the pinned packages.

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.lock
python -m pip install -e .
```

macOS or Linux:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install -e .
```

`requirements.lock` holds the packages the app needs at run time; `requirements-dev.lock` adds the pipeline, model and
test packages and includes the first file. `pip install -e .` installs the `fieldshift` package from `src/` in
editable mode, so code changes apply without reinstalling.

Start the server:

```bash
uvicorn fieldshift.api.app:app --port 8000
```

Check that it answers: http://127.0.0.1:8000/api/health should return a short JSON reply. The API routes are
`GET /api/past-years`, `POST /api/compare`, `GET /api/method` and `GET /api/health`, plus the optional
`POST /api/explain` and `POST /api/copilot` (section 5).

### 4.2 Frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

`npm ci` installs the exact versions in `package-lock.json`. `npm run dev` first copies the Cesium globe files into
`public/` (the `predev` step) and then starts Vite. Open the address Vite prints, normally http://localhost:5173.
Vite forwards every `/api` request to the backend at http://127.0.0.1:8000. If your backend runs elsewhere, set
`MIAUDOW_API` before `npm run dev`, for example `MIAUDOW_API=http://127.0.0.1:9000 npm run dev`.

### 4.3 One server, as in production

To check the built app the way it is deployed, build the frontend and let the backend serve it:

```bash
cd frontend
npm run build
cd ..
uvicorn fieldshift.api.app:app --port 8000
```

The build goes to `frontend/dist/`, which the backend serves at http://127.0.0.1:8000 together with the API. The
build also writes `THIRD-PARTY-LICENSES.txt` with the licences of every bundled package.

## 5. Optional features and settings

Settings are environment variables. Copy `.env.example` to `.env`, fill in what you need and start the backend with
the file:

```bash
uvicorn fieldshift.api.app:app --port 8000 --env-file .env
```

`.env` is ignored by git; never commit it. Every variable is optional. `.env.example` explains each one.

### 5.1 "Explain simply" and the assistant (Claude API)

| Variable | Value |
| --- | --- |
| `ANTHROPIC_API_KEY` | an Anthropic API key |
| `FIELDSHIFT_EXPLAIN` | `1` turns on the "explain simply" button on the plan cards |
| `FIELDSHIFT_COPILOT` | `1` turns on the assistant page (`#/tro-ly`) |

Without the key, "explain simply" stays off and the assistant answers from fixed sentences with no model. The key is
read only by the server; it never reaches the browser.

### 5.2 Google sign-in and saved answers

Sign-in is on only when both variables are set and the database answers when the server starts.

| Variable | Value |
| --- | --- |
| `GOOGLE_CLIENT_ID` | the client id of an OAuth "Web application" client in Google Cloud |
| `DATABASE_URL` | a PostgreSQL connection string |

In the Google Cloud client, add the addresses you open the app from as authorised JavaScript origins, for example
http://localhost:8000 and http://localhost:5173.

A throwaway local database with Docker:

```bash
docker run --rm -d --name miaudow-db -e POSTGRES_PASSWORD=local -p 5432:5432 postgres:18
```

Then set `DATABASE_URL=postgresql://postgres:local@127.0.0.1:5432/postgres`. The server creates its tables at start.
Stop the database with `docker stop miaudow-db`; the `--rm` flag deletes it and its data.

### 5.3 Other settings

| Variable | Use |
| --- | --- |
| `FIELDSHIFT_ROOT` | the project folder that holds `rules/`; needed only when the package runs outside the checkout (the Docker image sets it) |
| `PORT` | the port of the Docker image (default 8000) |
| `MIAUDOW_API` | where the frontend development server sends `/api` requests (default http://127.0.0.1:8000) |

## 6. Run the tests

CI runs the same checks on every pull request (`.github/workflows/ci.yml`).

### 6.1 Python

```bash
pytest -q
ruff check .
ruff format --check .
```

The sign-in tests need PostgreSQL. They start a throwaway container with Docker, or use `TEST_DATABASE_URL` when it
is set. Without either, they are skipped with a message. `FIELDSHIFT_LIVE=1` also runs the one test that calls the
real NASA POWER API. `ruff` is not in the lock files; install the version CI uses with
`python -m pip install ruff==0.17.4`.

### 6.2 Frontend

```bash
cd frontend
npx eslint .
npx prettier --check .
npm run typecheck
npx vitest run
npm run build
```

### 6.3 Browser tests

The browser tests (Playwright, at phone size 360 x 740 and at desktop size) build the frontend and start the backend
on port 8000 by themselves, so port 8000 must be free.

```bash
cd frontend
npx playwright test
```

- On your own computer the tests use Microsoft Edge. Without Edge, install Playwright's Chromium with
  `npx playwright install chromium` and run the tests with `CI=1 npx playwright test`.
- The tests start the backend with `python`. If that is not the Python with the project's packages, set `PYTHON`,
  for example `PYTHON=.venv/Scripts/python.exe` on Windows or `PYTHON=../.venv/bin/python` on macOS and Linux.
- The offline demo build has its own tests: `npx playwright test -c playwright.snapshot.config.ts`.

## 7. Rebuild the data (optional)

`scripts/reproduce.sh` rebuilds every derived table and artifact from the original public downloads, then runs the
Python tests. Run it from the repository root in Bash, with the virtual environment active.

Before you start:

1. Create a free NASA Earthdata account at https://urs.earthdata.nasa.gov and generate a user token there. MODIS land
   cover and GPM IMERG need it.
2. Set the token in your shell, not in a committed file: `export EARTHDATA_TOKEN=<your token>`.

```bash
bash scripts/reproduce.sh
```

What the script does, in order:

1. Exports the crop statistics of the National Statistics Office (PX-Web tables) and builds the crop table.
2. Downloads the province boundaries and MODIS land cover 2001-2015, then builds the fixed farmland mask and the
   farmland weight of each NASA POWER cell.
3. Downloads NASA POWER daily data for every weighted cell, builds the training table, chooses the normal-yield
   method, runs the model tests, and exports the risk table, the hazard shares, the soil wetness, the secondary
   models, the sensitivity runs, the method page reports and the figures.
4. Downloads GPM IMERG monthly rain for the rain check. NASA's servers for IMERG were mostly down during the event;
   set `FIELDSHIFT_SKIP_IMERG=1` to skip this step.
5. Rebuilds the saved answers for the offline demo build (`frontend/snapshot/`).
6. Runs `pytest -q`.

Downloads go to `data/raw/`, which git ignores. Every download is recorded in `data/MANIFEST.csv` with its address and
sha256 checksum, so you can check that you got the same files. Files that are already there are reused, so a second
run is much faster. Raw statistics files, journal PDFs and the texts of standards are never committed.

## 8. Offline demo build

For a demo without internet, build a static copy that answers a fixed set of saved choices:

```bash
cd frontend
npm ci
npm run build:snapshot
npm run preview -- --outDir dist-snapshot
```

Open http://localhost:4173. Instead of `npm run preview` you can serve the folder with
`python -m http.server 4173 -d dist-snapshot`. The copy answers only the choices saved in `frontend/snapshot/index.json`.
Opening `index.html` directly from the file system does not work, because browsers block module scripts there.

## 9. Common problems

| Problem | Fix |
| --- | --- |
| `RuntimeError: no rules/ folder` when the server starts | Start it from the repository root, or set `FIELDSHIFT_ROOT` to the repository folder. |
| `address already in use` on port 8000 | Another server is running. Stop it, or start this one with `--port 8001` and set `MIAUDOW_API=http://127.0.0.1:8001` for the frontend. |
| The page loads but shows no data | The backend is not running, or `MIAUDOW_API` points to the wrong address. Check http://127.0.0.1:8000/api/health. |
| The 3D globe stays empty in development | Run `npm run cesium` in `frontend/` to copy the Cesium files again. |
| Vietnamese names print as broken characters in a Windows console | Set `PYTHONUTF8=1` (the reproduce script does this for its own run). |
| The browser tests cannot find a browser | Install Edge, or run `npx playwright install chromium` and use `CI=1`. |
| Sign-in does not appear | Both `GOOGLE_CLIENT_ID` and `DATABASE_URL` must be set and the database must answer when the server starts. |
