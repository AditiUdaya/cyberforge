<!-- How the app is hosted: on a laptop (DECISIONS D59). Owner: A. Filled in by: A0. -->
# infra: hosting locally

The app runs on a laptop (DECISIONS D59): the API and the Streamlit website as two separate services (D55).
Pick one of the two ways below. Both keep the database between runs.

## Option 1: one command (recommended)

From the repo root, in Git Bash on Windows:

```bash
scripts/run_local.sh
```

- API on http://127.0.0.1:8000, website on http://127.0.0.1:8501.
- Loads a 30-day licence signed with your key (`~/.scam-map/license.key`). Demo data is loaded only the first time;
  after that your own reports are kept. `--fresh` clears everything and reloads demo data.
- Data, the local HMAC key and the licence file live in `.local/` (gitignored). Ctrl+C stops everything.

## Option 2: the two containers

The same images a server would run. Build them from the repo root:

```bash
docker build -f infra/Dockerfile -t scam-map-api .
```

```bash
docker build -f infra/Dockerfile.web -t scam-map-web .
```

Make an HMAC key once and keep it: changing it makes every stored report unreachable.

```bash
mkdir -p .local && uv run --project api python -c "import secrets; print(secrets.token_hex(32))" > .local/hmac.key
```

Run both on one Docker network; the database lives on the `scam-map-data` volume:

```bash
docker network create scam-map
```

```bash
docker run -d --name scam-map-api --network scam-map -p 8000:8000 -v scam-map-data:/data -e SCAM_MAP_HMAC_KEY="$(cat .local/hmac.key)" scam-map-api
```

```bash
docker run -d --name scam-map-web --network scam-map -p 8501:8501 -e SCAM_MAP_API_URL=http://scam-map-api:8000 scam-map-web
```

Then load a licence (every route except `/health` and `/license` answers `403 LICENSE_EXPIRED` until you do):

```bash
uv run --project api python scripts/license_sign.py --licensee "Demo Bank" --expires-in 30d --out .local/licence.json
```

```bash
curl -X POST -H "content-type: application/json" --data-binary @.local/licence.json http://127.0.0.1:8000/license
```

Stop with `docker stop scam-map-api scam-map-web`; start again with `docker start scam-map-api scam-map-web`. The
API image starts as root only to take ownership of the `/data` volume, then runs as an unprivileged user.

## Checking it

These all work against the local address (they reset the server first):

```bash
scripts/verify_deployed.sh http://127.0.0.1:8000 --yes
```

```bash
scripts/license_demo.sh http://127.0.0.1:8000 licence-5min.json licence-long.json
```

Logs go to the terminal (Option 1) or `docker logs scam-map-api` (Option 2). By design there is no per-request log:
no URLs, query strings, identifiers or reporter fields are ever logged.

## Judging

The PRD scores the server row on a public HTTPS address; a laptop-only server scores zero on that row. If that
is needed later, a tunnel in front of the local API (for example Cloudflare Tunnel or ngrok) gives one without a
cloud host. That is not set up here.
