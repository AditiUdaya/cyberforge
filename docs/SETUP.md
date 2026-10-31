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
| `SCAM_MAP_HMAC_KEY` | API (required) | any random string of 16+ characters locally; a real secret on the host. Changing it makes every stored report unreachable. |
| `SCAM_MAP_LICENSE_PUBLIC_KEY` | API (optional) | path to a public key PEM; defaults to `api/app/license/public_key.pem` |

Make an HMAC key:

```bash
uv run --project api python -c "import secrets; print(secrets.token_hex(32))"
```

## 5. Run it locally

API on port 8000:

```bash
cd api && uv run uvicorn app.main:app --reload
```

Check it: open http://127.0.0.1:8000/health and expect `{"ok": true}`. Every other route answers
`403 LICENSE_EXPIRED` until a licence is uploaded (section 7).

Streamlit on port 8501, pointed at the local API:

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

### Contract tests (PRD Appendix A)

`judge/contract.py` sends the PRD's own example requests and checks every reply against
`shared/contract/*.schema.json`. The same checks also run inside the API's pytest suite.

Against a throwaway local server that it starts and stops itself:

```bash
cd judge && uv sync --frozen && uv run python contract.py --target local
```

Against a running server, local or deployed. This calls `POST /admin/reset`, so it wipes the data:

```bash
cd judge && uv run python contract.py --target https://your-host
```

## 7. Licence

The server only works with a signed licence. The private key stays on your laptop, never in git or on the server.

Once per laptop: make the key pair. This writes the private key to `~/.scam-map/license.key` and the
public key to `api/app/license/public_key.pem`, which you then commit:

```bash
uv run --project api python scripts/license_keygen.py
```

Sign the two demo licences:

```bash
uv run --project api python scripts/license_sign.py --licensee "Demo Bank" --expires-in 5m --out licence-5min.json
```

```bash
uv run --project api python scripts/license_sign.py --licensee "Demo Bank" --expires-in 365d --out licence-long.json
```

Upload one:

```bash
curl -X POST -H "content-type: application/json" --data-binary @licence-long.json http://127.0.0.1:8000/license
```

Run the PRD's four-step demo against any server with a long licence loaded (it waits for the short one to expire):

```bash
scripts/license_demo.sh http://127.0.0.1:8000 licence-5min.json licence-long.json
```

`licence-*.json` files are safe to share; only `license.key` is secret.

## 8. Run the API container

```bash
docker build -f infra/Dockerfile -t scam-map-api .
```

```bash
docker run --rm -p 8000:8000 -v scam-map-data:/data -e SCAM_MAP_HMAC_KEY=<your key> scam-map-api
```

The database and the uploaded licence live on the `/data` volume, so they survive container restarts.

## 9. Deploy

Two apps on Fly.io (DECISIONS D55, D56). Step-by-step commands are in [infra/README.md](../infra/README.md).

## Windows notes

- Run `scripts/*.sh` from Git Bash.
- `python3` may be the Microsoft Store stub; always go through `uv run`.
- Git does not track the executable bit here (`core.filemode=false`). Stage new scripts with `git add --chmod=+x`.
