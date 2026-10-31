<!-- Developer setup for both people. Owner: A and B. Kept current by whoever changes the toolchain. -->
# Setup

Everything is Python 3.12 managed by uv: the API, the judge simulator and the Streamlit web app.
No Node, no npm.

## 1. Install the tools (once per laptop)

| Tool | Version we use | Check |
| --- | --- | --- |
| Git | any recent | `git --version` |
| uv | 0.12.x | `uv --version` |
| Python | 3.12 (uv can install it) | `uv python list --only-installed` |
| Docker | any recent (for the container) | `docker --version` |

If Python 3.12 is missing:

```bash
uv python install 3.12
```

## 2. Get the code

```bash
git clone <repo-url> scam-map
cd scam-map
```

Each task gets its own branch, named after the task ID:

```bash
git switch -c b/B0 main
```

## 3. Install dependencies

Each project has its own locked environment. `--frozen` installs exactly what is in `uv.lock`.

```bash
cd api && uv sync --frozen && cd ..
```

```bash
cd web && uv sync --frozen && cd ..
```

Pinned versions (all pass `pip-audit` with 0 findings on 31 Oct):

| Project | Runtime | Dev |
| --- | --- | --- |
| `api/` | fastapi 0.162.0, uvicorn 0.54.0 | httpx2 2.16.0 (Starlette test client), pytest 9.2.0, pytest-cov 7.1.0, ruff 0.17.3, mypy 2.4.1, pip-audit 2.10.1 |
| `web/` | streamlit 1.66.1, httpx 0.28.1 | pytest 9.2.0, ruff 0.17.3, mypy 2.4.1, pip-audit 2.10.1 |

Adding a dependency: `uv add <name>==<exact version>`, then `uv run pip-audit` must show 0 findings before you commit (CLAUDE.md).

## 4. Environment variables

Copy these into a `.env` file at the repo root, or set them in your shell. `.env` is gitignored.

| Name | Used by | Local value |
| --- | --- | --- |
| `SCAM_MAP_DB_PATH` | API | `scam_map.sqlite` in the working directory (the default); `/data/scam_map.sqlite` in the container |
| `SCAM_MAP_API_URL` | web | `http://127.0.0.1:8000` |
| `SCAM_MAP_HMAC_KEY` | API, from B2 | any long random string locally; a real secret on the host |

## 5. Run it locally

API on port 8000:

```bash
cd api && uv run uvicorn app.main:app --reload
```

Check it: open http://127.0.0.1:8000/health and expect `{"ok": true}`.

Streamlit on port 8501 (from task A0):

```bash
cd web && uv run streamlit run app.py
```

## 6. Run the checks

Before any commit, from the repo root (in Git Bash on Windows):

```bash
scripts/check.sh
```

Sections for parts that are not built yet will fail until their task lands. Run a single project's checks while you work:

```bash
cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy --strict app && uv run pytest -q -W error
```

## 7. Run the API container

```bash
docker build -f infra/Dockerfile -t scam-map-api .
```

```bash
docker run --rm -p 8000:8000 -v scam-map-data:/data scam-map-api
```

The database lives on the `/data` volume, so it survives container restarts.

## 8. Deployment shape

Two services on the cloud host (DECISIONS D55): the API container is the HTTPS address the judges test, and the
Streamlit container is the phone link, with `SCAM_MAP_API_URL` pointing at the API. The host is chosen in task A0.

## Windows notes

- Run `scripts/*.sh` from Git Bash.
- `python3` may be the Microsoft Store stub; always go through `uv run`.
- Git does not track the executable bit here (`core.filemode=false`). Stage new scripts with `git add --chmod=+x`.
