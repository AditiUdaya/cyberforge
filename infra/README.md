<!-- Host config and deploy steps for the cloud server. Owner: A. Filled in by: A0. -->
# infra: deploying to Fly.io

Two apps on Fly.io (DECISIONS D55, D56), both always on, both HTTPS on `*.fly.dev`:

| App | What | Config | Image |
| --- | --- | --- | --- |
| API | The address the judges test. SQLite on a 1 GB volume at `/data`. | `fly.api.toml` | `Dockerfile` |
| Web | The Streamlit mobile website. Talks to the API over HTTPS. | `fly.web.toml` | `Dockerfile.web` |

Every command below runs from the **repo root**. You need a Fly.io account with a card on file.

## 1. Once per laptop

Install `flyctl` (PowerShell):

```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

Then log in, which opens a browser:

```powershell
fly auth login
```

Make the licence key pair. The private key goes to `~/.scam-map/license.key` (keep it off git and off the
server); the public key goes into `api/app/license/public_key.pem`, which you **commit** so the image has it:

```powershell
uv run --project api python scripts/license_keygen.py
```

## 2. Pick names

App names are global on Fly. Pick two, for example `scam-map-api-<team>` and `scam-map-web-<team>`, and put them
in `app = "..."` in `fly.api.toml` and `fly.web.toml`. In `fly.web.toml`, also set
`SCAM_MAP_API_URL = "https://<api name>.fly.dev"`.

## 3. API

```powershell
fly apps create <api name>
```

```powershell
fly volumes create scam_map_data --region bom --size 1 --app <api name> --yes
```

The HMAC key turns reporter ids, IP prefixes and identifiers into keyed hashes. Never change it after reports
exist, or every stored report becomes unreachable. Make one and set it as a secret:

```powershell
$key = uv run --project api python -c "import secrets; print(secrets.token_hex(32))"
```

```powershell
fly secrets set SCAM_MAP_HMAC_KEY=$key --app <api name> --stage
```

Deploy one machine (SQLite on one volume needs exactly one):

```powershell
fly deploy . --config infra/fly.api.toml --dockerfile infra/Dockerfile --ha=false
```

Check it, then load a licence (everything except `/health` and `/license` answers `403 LICENSE_EXPIRED` until you do):

```powershell
curl https://<api name>.fly.dev/health
```

```powershell
uv run --project api python scripts/license_sign.py --licensee "Demo Bank" --expires-in 30d --out licence-30d.json
```

```powershell
curl -X POST -H "content-type: application/json" --data-binary "@licence-30d.json" https://<api name>.fly.dev/license
```

## 4. Web

```powershell
fly apps create <web name>
```

```powershell
fly deploy . --config infra/fly.web.toml --dockerfile infra/Dockerfile.web --ha=false
```

Open `https://<web name>.fly.dev` on a phone.

## 5. Verify the deployment

This runs every test layer against the live API and **resets it**, so never run it after the judges load data
(Git Bash):

```bash
scripts/verify_deployed.sh https://<api name>.fly.dev --yes
```

## 6. Before the demo

- Sign the two demo licences just before: `--expires-in 5m` and `--expires-in 365d`.
- Rehearse the four PRD steps: `scripts/license_demo.sh https://<api name>.fly.dev licence-5min.json licence-long.json`.
- After rehearsing, upload the long licence again and leave it.

## Updating

Redeploy the same way (`fly deploy ...`). The database and the uploaded licence live on the volume, so they survive
deploys and restarts. Logs: `fly logs --app <api name>` (no request bodies, query strings or identifiers are logged).
