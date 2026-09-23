# Mini Benchling Agents: macOS implementation plan

Status: proposed build checklist, not an implemented or tested application.
Prepared: September 22, 2026.
Platform: macOS, with Terminal/zsh commands and Docker Desktop for the service runtime.
Revision: replaces the platform setup and command examples in the earlier plan; preserves all 30 core tickets and four extension tickets.

This is a build plan, not an already implemented application. Tool-installation and repository-initialization commands are usable immediately on a compatible Mac. Application commands become usable only after the ticket that implements the referenced file, service, or module. The commands have not been executed on your Mac.

## Release goal

Ship one local application that demonstrates three connected workflows:

1. Upload a CSV, inspect a proposed import, approve it, and persist validated measurements with source provenance.
2. Create an experiment and receive a historical comparison supported by specific experiment records.
3. Request research, retrieve evidence through generated MCP connectors, and save a cited notebook draft.

Build in the numbered order below. Each step is a ticket or small pull request. Pass its acceptance check before starting dependent work. Reuse only code you own or are authorized to reuse from previous MCP/model-provider work. Do not copy employer code, data, or credentials.

## Fixed decisions

| Concern | Decision for release 1 |
|---|---|
| Host environment | macOS; Terminal/zsh; repository under `~/Developer/mini-benchling-agents` |
| Node tooling | Node.js 24; npm; frontend lockfile committed |
| Backend | Python 3.12, FastAPI, Pydantic contracts, SQLAlchemy, Alembic |
| Storage | PostgreSQL, relational identity and relationships, JSONB for flexible data |
| Jobs | PostgreSQL events plus run tables; polling; no Redis |
| Deployment | Docker Desktop + Compose on the Mac; local, single workspace |
| Upload storage | Local named volume shared by API and worker |
| Frontend | React + TypeScript + Vite on the Mac for development; compiled assets served by the API for the demo |
| Models | Deterministic fake provider for tests; one live provider adapter |
| MCP | Standalone FastMCP, with a curated OpenAPI-to-server-package generator |
| Required connectors | Molecule registry and PubMed adapter |
| Deferred | PDF, UniProt, inventory/reordering, embeddings, dynamic subagents, public hosting |

All timeouts, limits, scoring rules, and fixture outcomes below are proposed project defaults, not measured results or scientific recommendations. Lock the dependency versions you actually resolve and test; do not mix current documentation with older SDK examples.

---

# Phase A: environment and scope

## 01. Set up the Mac development environment

Use Terminal, iTerm, or your editor's integrated **zsh** terminal. Run each block in order, not the whole document as a script. Skip installations for tools that are already correctly installed.

### 01a. Identify your Mac and shell

```bash
sw_vers
uname -m
echo "$SHELL"
```

`arm64` means the current shell is running as ARM; `x86_64` means it is running as Intel. An Apple silicon Mac running a translated terminal can also report `x86_64`, so confirm the physical chip in **Apple menu > About This Mac**. Prefer an untranslated terminal on Apple silicon. Check the current tool requirements before installing on an older macOS version. Homebrew's published support varies by architecture and OS; the installer alternative below avoids requiring Homebrew on an unsupported combination. [M1, M4]

### 01b. Install Apple's Command Line Tools

Check first:

```bash
xcode-select -p
```

When no developer-tools path is configured, run:

```bash
xcode-select --install
```

Complete the macOS installation dialog before continuing. The Command Line Tools are sufficient for this setup; the plan does not require the full Xcode application. [M1]

### 01c. Install Homebrew and initialize its path

Check for an existing installation:

```bash
command -v brew
```

When absent, use Homebrew's official installer. Read its prompts before accepting changes:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the installer's printed shell-configuration instructions. The standard Homebrew prefixes are `/opt/homebrew` on Apple silicon and `/usr/local` on Intel. For an existing standard installation, this block selects the appropriate prefix, persists its initialization once in `~/.zprofile`, and initializes this terminal: [M1, M2]

```bash
if [ "$(uname -m)" = "arm64" ] && [ -x /opt/homebrew/bin/brew ]; then
  BREW_BIN=/opt/homebrew/bin/brew
elif [ "$(uname -m)" = "x86_64" ] && [ -x /usr/local/bin/brew ]; then
  BREW_BIN=/usr/local/bin/brew
else
  echo "Follow the Homebrew installer's PATH instructions before continuing."
  BREW_BIN=
fi

if [ -n "$BREW_BIN" ]; then
  BREW_INIT="eval \"\$($BREW_BIN shellenv)\""
  touch "$HOME/.zprofile"
  grep -Fqx "$BREW_INIT" "$HOME/.zprofile" || printf '%s\n' "$BREW_INIT" >> "$HOME/.zprofile"
  eval "$("$BREW_BIN" shellenv)"
fi

brew --version
```

Do not overwrite an existing shell profile. An Apple silicon Mac with an Intel-only Homebrew installation needs its architecture setup resolved rather than silently mixing packages from two architectures.

### 01d. Install project tools

For the Homebrew path:

```bash
brew install git uv node@24
brew install --cask docker-desktop
```

Use Node 24 as the project baseline. The `node@24` formula is keg-only, so add its executable directory explicitly. Existing Node version-manager users should select Node 24 in that manager instead of adding a competing Homebrew Node installation. [M3, M5, M6, M7]

Run this only when using the Homebrew Node installation:

```bash
NODE_BIN="$(brew --prefix node@24)/bin"
NODE_INIT="export PATH=\"$NODE_BIN:\$PATH\""
touch "$HOME/.zshrc"
grep -Fqx "$NODE_INIT" "$HOME/.zshrc" || printf '%s\n' "$NODE_INIT" >> "$HOME/.zshrc"
export PATH="$NODE_BIN:$PATH"
```

Now install a project-managed Python rather than changing the system Python:

```bash
uv python install 3.12
```

uv can install the chosen Python version independently of a system interpreter. Use `uv run ...` for project commands. [M8]

**Installer alternative for Intel/unsupported Homebrew setups:** retain Git from Apple's developer tools, install uv with its official standalone installer below, install Node 24 using the official macOS installer/download for the appropriate architecture, and install the matching Docker Desktop Mac build. Do not also install a second copy through Homebrew. [M3, M4, M7]

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Follow uv's printed PATH instructions and open a new terminal before running `uv python install 3.12`. Docker and Node must still support your macOS version; this alternative is not a promise that every older Mac is supported.

### 01e. Start Docker Desktop

```bash
open -a Docker
```

Complete Docker's first-run configuration and review its terms in the application. Once its engine is running, verify:

```bash
git --version
uv --version
uv python find 3.12
node --version
npm --version
docker version
docker compose version
docker run --rm hello-world
```

`docker version` must show a working server, not just a client. Keep Docker Desktop running whenever using Compose. Docker provides distinct Apple silicon and Intel installers; use the one matching your hardware. [M4]

### 01f. Configure your editor

Use the Mac editor you already have. For VS Code, open the Command Palette with **Cmd+Shift+P**, run **Shell Command: Install 'code' command in PATH**, then open a new terminal. This enables `code .`. The menu-based **File > Open Folder** route works without a terminal command. [M9]

Choose the repository's `.venv/bin/python` as the editor interpreter after Step 02. Do not install a local PostgreSQL service, Redis, Kubernetes, or a local model server for this plan.

**Acceptance:** Git, uv-managed Python 3.12, Node 24, npm, Docker, and Compose are available. Docker runs the smoke-test container. The correct editor opens a folder on the Mac.

## 02. Initialize the repository and Python package

```bash
mkdir -p "$HOME/Developer"
cd "$HOME/Developer"
mkdir mini-benchling-agents
cd mini-benchling-agents

uv init --package --name minibench --python 3.12
uv python pin 3.12
uv add fastapi "uvicorn[standard]" pydantic-settings sqlalchemy "psycopg[binary]" alembic python-multipart httpx
uv add --dev pytest pytest-asyncio ruff
uv run alembic init migrations
printf '24\n' > .node-version

uv run python -c "import minibench; print('minibench import OK')"
uv run ruff check .
```

This block is for a **new repository**. For an existing project, open its existing root instead; do not create a second nested repository or rerun scaffolders over edited files. Keep the checkout out of iCloud-synced Desktop/Documents folders. The quoted dependency extras work in zsh without wildcard expansion. uv initialization creates the Python package; a model, worker, and API still need to be implemented in the later tickets. [M10]

Check `git status` after initialization. If no Git repository was created, run `git init`. Commit both `.python-version` and `.node-version` with the dependency lockfiles.

Use this structure; create feature modules when their steps arrive rather than filling the repository with empty abstractions:

```text
mini-benchling-agents/
  src/minibench/
    main.py
    settings.py
    db.py
    api/
    domain/
      schemas/
      models/
      services/
    runtime/
    agents/
    llm/
    connectors/
    scripts/
  migrations/
  tests/
    unit/
    integration/
    e2e/
    live/
  fixtures/
  web/
  docs/
  compose.yaml
  compose.test.yaml
  Dockerfile
  .dockerignore
  .env.example
  .python-version
  .node-version
  pyproject.toml
  uv.lock
```

Ignore `.env`, `.env.*` except `.env.example`, `.venv`, `.DS_Store`, caches, uploads, `node_modules`, and generated build directories. Add secrets, `.venv`, `web/node_modules`, `.git`, uploads, and caches to `.dockerignore` too. Commit `uv.lock`; later commit the frontend lockfile too.

**Acceptance:** The package imports, Ruff runs, and the initial repository contains no secrets.

## 03. Build the local service skeleton

Create `settings.py`, `db.py`, `main.py`, `Dockerfile`, `compose.yaml`, `.dockerignore`, and `.env.example`.

Implement `GET /health` as a liveness check and `GET /ready` as a database readiness check. Configure the database URL through settings. Use a PostgreSQL service with a health check and persistent volume. Use a separate named upload volume. Pin a supported PostgreSQL major for development, such as 17, and record the exact image digest tested for the release; do not use a floating `latest` image.

Start with `db` and `api`. Add `worker` in Step 10, using the same image but a different command. API command:

```text
uv run uvicorn minibench.main:app --host 0.0.0.0 --port 8000
```

Publish application ports to host loopback only. Give containers the service hostname `db`, not `localhost`, for database access. Do not automatically run migrations separately in every worker; provide a documented one-shot migration command.

### Mac versus container boundaries

The canonical development setup is:

| Runs directly on the Mac | Runs in Linux containers through Docker Desktop |
|---|---|
| Editor, Git, uv dependency updates, local lint/unit tests | API, worker, PostgreSQL |
| Node/npm and Vite during frontend development | PubMed adapter and generated MCP servers when added |
| Browser and Docker CLI | PostgreSQL integration tests in an isolated test stack |

Use multi-architecture images with a manifest matching the host, starting with `python:3.12-slim` and `postgres:17` as candidate image tags. Do **not** force `platform: linux/amd64` on an Apple silicon Mac. Verify the manifests selected at build time rather than promising support for an architecture you did not test. Record tested image digests for the release. [M11]

Keep host and container dependencies separate. Never copy or bind-mount the Mac's `.venv` or `web/node_modules` into Linux. For development, mount selected source directories, not the entire repository over the container's dependency environment. Rebuild the image when `pyproject.toml` or `uv.lock` changes. Follow uv's Docker workflow with a locked sync and an independently created container environment. [M12]

### Networking contract

Publish only `127.0.0.1:8000:8000` for the API. The API binds to `0.0.0.0:8000` **inside** its container; it is exposed only on host loopback. PostgreSQL needs no published port in the canonical workflow. [M13]

| Caller | Destination |
|---|---|
| Browser / Vite running on the Mac | `http://127.0.0.1:8000` |
| API or worker container | PostgreSQL at `db:5432` |
| Worker / connector inside Compose | API at `http://api:8000` |
| Future container that must reach an explicitly approved host service | `host.docker.internal` plus that service's port |

Compose service names work inside the Compose network, not in a Mac terminal. `localhost` inside a container means that container, not your Mac or the database container. Docker Desktop documents `host.docker.internal` for reaching host services. [M13, M14]

### Environment and tests

After creating `.env.example`, copy it once without overwriting existing secrets:

```bash
cp -n .env.example .env
```

Generate distinct local reviewer/worker keys and a local database password; leave live-provider values blank while `MODEL_MODE=fake`. Do not put real keys in `.env.example`, the image, shell scripts, or frontend `VITE_*` configuration.

Implement `compose.test.yaml` with a `db_test` service and a `tests` runner built from the same development/test image. It must have separate volumes/credentials and a test-only database URL. Reject test startup against a database not explicitly labeled for testing. The test runner can run migrations against that database and then pytest; it must never reset the demo database.

Add a CI workflow that installs locked dependencies, runs Ruff, and executes tests with a dedicated PostgreSQL service. Do not depend on live model or science APIs in CI. Keep Linux CI even though development is on a Mac, and use consistent filename/import casing. Use `--locked` for dependency verification in CI and rebuilt containers rather than silently changing the lockfile.

Commands usable **after the skeleton files exist**:

```bash
docker compose build api
docker compose up -d --wait db
docker compose up -d api
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/ready
```

Give `db` a health check so `--wait` tests readiness. Later API startup must depend on a successful one-shot migration; do not run migrations independently in every worker. [M15, M16]

Environment contract: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `UPLOAD_DIR`, `MODEL_MODE=fake`, `MODEL_NAME`, `MODEL_API_KEY`, `REVIEWER_API_KEY`, and `WORKER_API_KEY`. Pass each service only the environment entries it needs. Compose may read `.env` for interpolation, but do not apply the complete file as `env_file` to every service. Never pass the reviewer key to the worker or model. Inside Compose, build `DATABASE_URL` with hostname `db`; use a distinct `db_test` URL only in the test stack.

**Acceptance:** Compose starts the database/API and the health/readiness smoke tests pass.

## 04. Create the complete demo fixtures before model integration

Use explicitly synthetic protein-assay records, not real laboratory data. Create 20 historical experiments, 30 samples, and a handful of synthetic registry molecules. Record explicit outcomes and failure-step labels on historical experiments; these are fixture labels, not scientific inferences.

Limit release-1 CSVs to UTF-8, comma-separated, one measurement per logical record. Canonical headers:

```text
sample_id,measurement_name,value,unit
```

Associate the entire file with an experiment at upload time.

Create:

| File | Expected result |
|---|---|
| `clean.csv` | 20 valid measurements |
| `renamed_headers.csv` | Same 20 values; headers require mapping |
| `unknown_sample.csv` | 20 valid records and one unknown-sample issue |
| `ambiguous_alias.csv` | 20 valid records and one ambiguous-match issue |
| `bad_unit.csv` | 20 valid records and one unsupported-unit issue |
| `malformed.csv` | Explicit file-level parsing failure |

Place expected outputs beside inputs. For ambiguous matching, deliberately assign one alias to two samples. Never invent sample matches to satisfy a test.

Create historical-check cases with known matching experiment IDs, including one with three comparable experiments and two recorded failures, plus one with no comparable history.

**Acceptance:** Expected outputs exist before extraction or retrieval code is written.

---

# Phase B: scientific data and durable events

## 05. Implement the initial database models and migrations

Create models/contracts for `Experiment`, `Sample`, `SampleAlias`, `ResultUpload`, and `Event`. Use separate Pydantic create/read contracts and explicit SQLAlchemy models; do not expose arbitrary database columns through generic patch operations.

Required fields are specified in Appendix A. Include foreign keys, uniqueness constraints, UTC timestamps, and integer object versions where relevant. Flexible conditions belong in JSONB; IDs and relationships do not.

For measurements added in Step 15, preserve raw reported strings and use Decimal/PostgreSQL NUMERIC for normalized numeric values rather than converting source values through floating point.

**Acceptance:** Alembic builds a fresh database; invalid references and duplicate canonical sample codes are rejected.

## 06. Implement the domain API and seed command

Write domain services first, thin API routes second. Add list/create/detail operations for samples and experiments. Provide an explicit experiment-update command with an expected version rather than an unrestricted patch endpoint.

Implement the seed module, invoked from the Mac as `docker compose run --rm api uv run python -m minibench.scripts.seed_demo` so it uses the container database network and environment. Use stable fixture identifiers and make repeated seeding safe. Seed historical records without triggering live agents; document that this is a development-only seed path.

Create new live experiments and their `experiment.created` event in the same transaction. Historical checks are not subscribed until Step 23; do not silently discard unmatched historical events.

Add basic local API-key authentication: derive reviewer/worker principals from validated server-side keys, never from a caller-supplied role field. Limit the worker's capabilities and prevent it from using approval routes. This is a local-demo boundary, not enterprise authentication or a sandbox for untrusted Python code.

**Acceptance:** API tests cover create/read, invalid inputs, version conflicts, and denied worker approvals. Seed runs twice without duplication.

## 07. Implement upload finalization and atomic event creation

Create `POST /api/experiments/{id}/uploads` and `GET /api/uploads/{id}`.

Stream the file into a temporary location under the upload volume. Enforce a 5 MiB limit while reading, not only from declared Content-Length. Compute SHA-256 and atomically move completed bytes into a generated storage path; never use a supplied filename as a filesystem path.

Only after storage succeeds, commit `ResultUpload` and `results.uploaded` together in one database transaction. A failed transaction can leave an orphan file, so provide an orphan-cleanup command with an age threshold; never create a ready upload pointing to missing bytes.

Use `(experiment_id, sha256)` as the duplicate-upload key for this release. Reuploading identical bytes to the same experiment returns the existing upload. This prevents byte-identical reuploads, not all semantically equivalent datasets.

**Acceptance:** Failed storage produces no ready upload/event. Failed database commit produces no event. Identical reupload returns the existing upload.

## 08. Add durable runtime records

Create `AgentRun` and `RunStep` tables, plus an immutable event envelope with event/schema versions, aggregate reference/version, actor, timestamp, and correlation/causation IDs.

Run states:

```text
queued -> running -> succeeded
                  -> waiting_approval
                  -> retry_wait -> running
                  -> failed
waiting_approval -> succeeded | cancelled
```

The approval transaction in Step 16 will complete the small staged import synchronously. Do not add a separate continuation job for that operation in release 1.

Add attempts, next-attempt time, worker identity, lease token, lease expiry, cumulative budget usage, and sanitized error fields. Create a unique constraint on `(event_id, subscription_id)`.

**Acceptance:** State-transition and constraint tests reject illegal transitions and duplicate logical dispatches.

---

# Phase C: reliable runtime before real AI

## 09. Implement deterministic event dispatch

Create a versioned subscription registry. Initially register only `results.uploaded -> data_entry_v1`.

For each registered subscription, find matching events with no corresponding `(event_id, subscription_id)` run. In a short transaction, lock an event and insert its missing run records with conflict-safe uniqueness. The presence of the run is the durable dispatch record: do not use one global dispatched boolean that would hide events from a newly added subscription. Retain unmatched events and show them as unmatched rather than losing them.

Define subscription activation/backfill explicitly when adding agents: for this demo, a new subscription processes existing matching events not previously dispatched to that subscription. Do not reset already completed runs.

**Acceptance:** Dispatching the same event repeatedly produces one run for each subscription, including under concurrent dispatchers.

## 10. Implement leased worker execution

Create `runtime/worker.py`, `runtime/executor.py`, and `runtime/repository.py`. Set its container command to:

```text
uv run python -m minibench.runtime.worker
```

From the Mac, launch that service after adding it to Compose:

```bash
docker compose up --build -d worker
docker compose logs -f worker
```

Do not also launch a duplicate host worker. Rebuild/restart this service after code changes until you deliberately add a development reloader.

Use a short `SELECT ... FOR UPDATE SKIP LOCKED` transaction to claim a due run. PostgreSQL documents this pattern for queue-like tables. Commit the claim before making network/model calls.

Defaults: 1-second polling, one active run per worker, 60-second leases, heartbeat every 10 seconds, and at most three total execution attempts. Retry transient failures with scheduled delays of 5 and 30 seconds plus small jitter; do not keep a DB transaction open or sleep while holding a job lock. Do not retry schema/authorization failures as transient failures.

Recover expired leases. Before persisting any authoritative effect, lock the run and verify both lease token and expiry in the same transaction as the effect. A stale worker must not write merely because it checked its lease earlier.

**Acceptance:** A stopped worker's lease is recoverable, and the old lease cannot commit after another worker takes ownership.

## 11. Prove the runtime with a fake handler

Implement a placeholder data-entry handler that reads the file, counts logical CSV records, writes a trace step, and completes. No live model needed.

Write integration tests named:

```text
test_upload_while_worker_stopped_is_processed_after_restart
test_duplicate_dispatch_creates_one_run
test_two_workers_do_not_claim_same_live_lease
test_expired_lease_is_recovered
test_stale_worker_cannot_commit
test_transient_failure_stops_after_three_attempts
```

Run them against PostgreSQL, not an SQLite substitute. From the Mac, use the isolated test stack implemented in Step 03:

```bash
docker compose -p minibench-tests -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
```

The test runner must wait for `db_test` readiness, migrate its dedicated database, and exit with pytest's exit status. Cleanup commands appear in Appendix E.

**Acceptance:** Every test passes and an upload made while the worker is offline completes after restart.

## 12. Add the first run-inspection UI

Implement `GET /api/runs` and `GET /api/runs/{id}`, including sanitized trace steps, attempts, and error information.

Scaffold the frontend:

```bash
npm create vite@latest web -- --template react-ts
cd web
npm install
cd ..
```

Set Vite's development proxy for `/api` to `http://127.0.0.1:8000`, since Vite runs on the Mac. Keep browser requests relative to `/api`. Do not use `http://api:8000` as a Mac-side proxy target. Start the frontend in a second terminal:

```bash
cd "$HOME/Developer/mini-benchling-agents/web"
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open the UI using `http://127.0.0.1:5173`. Keep the API in Docker rather than starting a second copy of it on port 8000. Commit `web/package-lock.json`; use `npm ci` for later clean installs. [M6]

 Build `RunsPage.tsx` and `RunDetailPage.tsx`. Poll active runs every second; stop polling completed runs and clear timers on navigation. Show event ID, agent, status, attempt, timestamps, trace steps, and errors.

For the local reviewer view, accept the reviewer key at runtime and retain it only in memory; never embed it into the compiled frontend or logs.

**Acceptance:** Upload through the API and watch the run progress in the browser. This is the first demonstrable platform checkpoint.

---

# Phase D: reviewed CSV imports

## 13. Implement deterministic parsing and validation

Create `agents/data_entry/parser.py`, `mapping.py`, `resolution.py`, and `validation.py`.

Parse with Python's CSV library and cap files at 1,000 logical data records for release 1. Keep stable record indexes and the original field strings. A logical record may span physical lines; record physical start/end lines too when feasible, and do not call a record index a source line number.

Apply exact header aliases first. Resolve sample canonical IDs first, then known aliases. Multiple alias matches produce an ambiguity issue. Unknown units, missing fields, malformed numbers, and non-finite numeric values produce explicit issues.

Do not let a model rewrite values or infer a sample from an unrelated free-text similarity. Do not silently drop invalid records.

**Acceptance:** `clean.csv` produces exactly 20 expected rows with no model calls; every problematic fixture yields the expected issue locations.

## 14. Add a fake and one live model adapter

Create `llm/base.py`, `llm/fake.py`, and one live provider module using your authorized reusable adapter or a documented SDK. Pin the SDK actually tested.

Define typed `ColumnMapping` and `ModelTurn` outputs. Use the model only for unresolved header mapping at this stage. Send headers and a small bounded set of example values, not the whole file by default.

Validate the returned mapping against allowed canonical fields and real source columns. Allow at most one repair attempt for invalid structured output; then stop with a reviewable error. Record model identifier, prompt version, latency, available token counts, and sanitized errors.

Keep `MODEL_MODE=fake` for CI. Never silently switch a failed live run into fake mode. Display the selected mode in the UI.

**Acceptance:** Renamed headers work through the adapter, invented column names are rejected, and model failure does not corrupt data.

## 15. Stage immutable import proposals

Add `ImportProposal` and `Measurement` models and migrations. A proposal stores parsed candidate rows, issues, explicit exclusions, source/version information, a content hash, and review state. A new edit creates a new proposal revision; it does not mutate an approved payload.

Release-1 policy: an unresolved row blocks approval unless the reviewer explicitly excludes it with a reason. Thus the full file remains accounted for even when only valid rows will be committed.

When processing completes, atomically persist the proposal and change the run to `waiting_approval`; release the lease. No worker remains occupied while a human reviews.

**Acceptance:** Valid rows are visible in a pending proposal, while the committed measurement table remains unchanged.

## 16. Implement protected approval and finalization

Create explicit revision, approval, and rejection endpoints. Do not expose them as agent tools. Require a validated reviewer principal, expected proposal version/hash, and any explicit row exclusions.

In one short transaction: lock run/proposal, check pending state and expected revision, revalidate referenced object versions and row constraints, insert measurements, record reviewer/decision, mark the proposal applied, and finish the run. This bounded, local database operation does not call a model or external API.

Enforce `UNIQUE(upload_id, source_record_index)` for release-1 measurements. Only one applied proposal is permitted per upload. Repeating approval returns the existing result; a changed/stale proposal returns a conflict without partial writes.

Rejecting a proposal records the reason and sets the waiting run to `cancelled`, not a successful import.

**Acceptance:** Stale revisions, worker principals, repeated clicks, and concurrent approval attempts cannot create unauthorized or duplicate measurements.

## 17. Complete the import UI and release checkpoint

Build `UploadPage.tsx` and `ImportReviewPage.tsx`. Show original values alongside proposed mappings, canonical sample resolution, units, issue messages, exclusions, and source coordinates. Allow mapping correction or explicit exclusions through revision creation. Keep original file values immutable.

Test the entire path in the browser: upload the unknown-sample fixture, review its issue, explicitly exclude the unresolved record, approve the 20 valid records, and inspect each measurement's source.

Add `test_approval_retry_does_not_duplicate_measurements`, `test_stale_proposal_is_rejected`, and `test_unresolved_row_blocks_approval`.

**Acceptance:** Restarting the app while awaiting approval preserves the proposal; approval inserts exactly the expected rows once. Tag this checkpoint `v0.1-reviewed-imports`.

---

# Phase E: spec-first interfaces and generated connectors

## 18. Extract the small object registry

After implementing samples and experiments explicitly, create `domain/object_registry.py`. Register each public create/read schema, service implementation, route prefix, and stable operation IDs. Generate only repetitive create/list/detail route exposure and their contracts.

Keep approval, upload finalization, and business-specific writes as explicit commands. Let FastAPI produce OpenAPI from Pydantic request/response contracts rather than maintaining independent agent schemas.

Add a contract test proving a public schema change appears in OpenAPI while service validation and permissions remain active.

**Acceptance:** Two object types use the registry without a universal ORM/code-generation framework or unrestricted CRUD bypasses.

## 19. Add the tiny molecule registry

Create `Molecule` with a stable ID, name, aliases, target identifier, synthetic-data marker, and optional structured properties. No chemistry validation or molecular calculations in this release.

Expose only two research operations initially: `search_molecules` and `get_molecule`. Seed synthetic molecules. Add a controlled create endpoint for testing JSON request-body generation, but keep it outside Research's allowed tool set.

Export the API's OpenAPI document using a script, not by hand. Store the selected registry contract under `connectors/specs/`.

**Acceptance:** Registry search/detail return fixtures and the exported specification is generated from the real application.

## 20. Implement the connector-package generator

Add FastMCP plus the generation/validation dependencies you need and commit the tested lockfile. From the Mac, add the base dependency:

```bash
uv add fastmcp
```

Then rebuild relevant Python service images before running integration tests. Follow the installed version's client API rather than pasting older HTTP-client examples.

Implement a CLI with this project-defined interface:

```bash
uv run python -m minibench.connectors.generate --spec connectors/specs/molecule-registry.json --config connectors/configs/molecule-registry.yaml --out generated/molecule-registry
```

The generator CLI above runs on the Mac and writes files into this repository. Its emitted server runs in a container. Generation must work offline from the input spec/config; it should not need to resolve container hostnames from the Mac.

Input configuration declares selected operation IDs, tool names/descriptions, fixed upstream base URL, allowed destinations, auth environment-variable names, and timeout/response limits. For a registry connector inside Compose, the upstream URL is `http://api:8000`, not `localhost:8000`.

Support only the OpenAPI subset exercised by your fixtures: selected 3.0/3.1 constructs, local non-cyclic references, common path/query parameters, and JSON request/response bodies. Reject unsupported operations and remote references with actionable errors. Validate the final sanitized tool names are unique.

Generate `server.py`, the source spec, a normalized tool manifest, a locked dependency specification, Dockerfile, README, `.env.example`, and a support report. Runtime conversion may use `FastMCP.from_openapi`; label this accurately as a generated package around FastMCP's conversion capability, not a new protocol compiler.

**Acceptance:** Running the generator twice with unchanged input produces equivalent normalized manifests and a standalone package that imports successfully.

## 21. Prove real MCP behavior and permissions

Use explicit allowlist rules followed by a catch-all exclusion. FastMCP's default conversion exposes endpoints as tools, so a partial allowlist without final exclusion is not sufficient.

Launch the generated server and test it using a real MCP client: initialization, tool listing, schema inspection, and tool calls. Include an actual HTTP transport integration test; import-only checks are insufficient. Run the server and client together on the isolated test network or deliberately publish a test-only loopback port; do not expose MCP services on all Mac network interfaces.

Verify path/query and JSON-body mapping, missing required fields, upstream 404/timeouts, operation exclusion, and credential redaction. Use configured upstream credentials, not blind forwarding of client tokens. For the local registry, explicitly allow only the expected Compose service destination; external connectors must not accept arbitrary destinations from tool arguments or redirects.

Keep generated MCP servers unexposed to the public network. The runtime validates tool arguments and agent-specific permissions even if the server also enforces its own policy.

**Acceptance:** Research can discover/call registry read tools through MCP and cannot discover or invoke approval/admin operations.

## 22. Add PubMed through a small adapter, then generate its MCP server

Implement two FastAPI adapter operations: `search_articles(query, limit)` and `get_article(pmid)`. Use NCBI ESearch to obtain IDs and EFetch for available article records/abstracts. Do not represent PubMed records as guaranteed full-text articles.

Normalize output to PMID, title, authors, publication metadata, available abstract, connector-supplied source URL, retrieval timestamp, and source excerpt identifiers. Use a safe XML parser with external entities/network resolution disabled. No arbitrary external URL fetch tool.

Run the adapter as a single shared service with caching and a centralized request limiter. Start at no more than two NCBI requests per second for headroom below the documented no-key limit. Include configured tool/contact parameters and optional API key; honor 429/backoff responses. A model-generated query must use normal encoded API parameters, never string-built URLs.

Export its OpenAPI and use the same generator from Step 20. Document that PubMed normalization is handwritten and MCP exposure is generated.

Keep network mocks/recordings in normal CI; put one real search/fetch/MCP smoke test behind an explicit `live` marker. Log partial data and source failures honestly.

**Acceptance:** A real PubMed query succeeds through the generated MCP server, with a source record usable as notebook evidence. No direct HTTP bypass from the Research agent.

---

# Phase F: historical checks and research

## 23. Implement Study Check using structured retrieval

Add an immutable experiment-version snapshot or equivalent captured event payload, plus `StudyAssessment`. Register `experiment.created -> study_check_v1` and define subscription backfill behavior.

Filter completed prior experiments by canonical target and assay type, excluding the current experiment. Restrict evidence to records available at the captured assessment cutoff. Rank by explicit condition matches, recording matched and missing fields. Version the scoring rule; do not treat missing conditions as positive matches. Return up to five candidates and abstain when no candidate meets the configured comparison rule.

Compute counts and recorded failure steps in code from source records. The model may explain the evidence but may not invent counts or imply experimental similarity proves causality. Label the result as a comparison, not scientific validation.

Save evidence experiment IDs/versions and the version of the new design assessed. A later design edit makes the old assessment visibly stale; it cannot silently apply to the new design.

**Acceptance:** The fixture with three comparable experiments and two recorded failures is reported exactly; the no-history fixture produces an explicit abstention.

## 24. Implement the bounded Research agent

Add `ResearchRequest`, `NotebookEntry`, and evidence storage with migrations. `POST /api/research-requests` commits the request and `research.requested` event together.

Expose only approved, read-only registry/PubMed MCP tools. In the core release this agent does not need a human pause; approval waiting is relevant to imports and later reorder work. Define a typed model turn as either allowed tool calls or a final notebook draft. The runtime validates tool names and arguments, executes tools, stores sanitized results and evidence snapshots, and returns bounded results to the model. It does not expose generic HTTP, SQL, shell, or reviewer operations.

Defaults: six model turns, twelve tool calls, and 180 seconds of active execution across retries, excluding approval wait. Persist cumulative usage so retry does not reset budgets. Configure a provider-specific token cap. A terminated/partial run remains visibly partial; do not silently present it as complete.

The final draft contains summary, claim-level evidence IDs, disagreements, missing evidence, limitations, and sources. Source IDs/URLs must come from retrieved connector records, not model invention. Distinguish synthetic local-registry records from real literature.

Save drafts as non-authoritative notebook entries. Verify evidence IDs exist, then assess claim support separately in evaluations; source existence alone is not evidence that the claim is supported. Persist one notebook draft per logical research request/version to avoid retry duplicates.

**Acceptance:** The trace proves both registry and PubMed were accessed through MCP, and every factual claim has linked evidence or is explicitly labeled unsupported/unknown.

## 25. Finish the connected interface

Add `ExperimentDetailPage.tsx` with design/history/assessment and `ResearchPage.tsx` with research request/notebook display. Link uploads, runs, experiments, proposals, measurements, notebook entries, and evidence.

Display fake/live mode, synthetic-data labels, errors, partial results, stale assessments, and pending approvals prominently. Render untrusted model/source text safely; do not inject raw HTML. Show latency, available usage counts, and redacted tool calls in the run inspector.

Keep ordinary tables/forms. Do not introduce streaming, a graph editor, or a general chat interface for this release.

**Acceptance:** A reviewer can navigate all three workflows and inspect the evidence behind every displayed output.

---

# Phase G: evaluations and release

## 26. Add repeatable evaluation commands

Implement the evaluation module and a separate explicit live mode. Execute it in the container so its configured database and connector destinations are resolvable:

```bash
docker compose exec api uv run python -m minibench.scripts.evaluate --mode fake
```

The fake evaluation path must be deterministic; live evaluation is an explicit additional command and never an automatic fallback. Write reports under `reports/` with dataset version, code commit, model ID, prompt versions, mode, and timestamps.

Measure extraction field accuracy, sample resolution correctness, ambiguity detection, and preservation of raw values. Evaluate historical retrieval against held-out labeled cases, including irrelevant-match and abstention cases. Separately evaluate citation-reference validity and actual claim support using manual labels on the small benchmark.

Report denominators, partial/failing runs, and available usage metrics. Never generalize perfect fixture results into broad scientific-document accuracy.

**Acceptance:** Re-running fake mode reproduces outputs; live results remain clearly labeled as measured runs, not predetermined expectations.

## 27. Execute the failure/security release suite

Test duplicate events, lease expiry, stale workers, stale proposals, concurrent approvals, restart during review, malformed CSV, unavailable model/API, 429/timeouts, missing abstracts, invalid tool arguments, exhausted budgets, and prompt injection in retrieved source text.

The injection test should verify a specific forbidden action was blocked, not claim universal prompt-injection immunity. Check that logs/manifests contain no secrets and that worker credentials cannot authorize review.

Document delivery semantics: at-least-once processing and idempotent committed effects. Do not claim exactly-once execution or sandboxing against malicious Python inside the worker process.

**Acceptance:** All required local tests pass against PostgreSQL and live integration smoke results are recorded separately.

## 28. Package a clean-checkout demo

Configure Compose migration ordering, idempotent seeding, named volumes, health checks, and deterministic fixture mode. Build/serve the compiled frontend through the API for the final local demo; keep Vite for development.

The intended normal developer commands, after the relevant files exist, are:

```bash
cd "$HOME/Developer/mini-benchling-agents"
open -a Docker
docker info

docker compose build api worker
docker compose up -d --wait db
docker compose run --rm api uv run alembic upgrade head
docker compose run --rm api uv run python -m minibench.scripts.seed_demo
docker compose up -d api worker
```

Complete Docker's first-run UI before expecting `docker info` to succeed. Start the Vite frontend separately during development (Step 12). For the final demo, use a Linux Node 24 builder stage to compile the frontend from its lockfile and copy only built assets into the API image. Never copy Mac-native `node_modules` into that stage.

Add the adapter/generated connector services to the final Compose file. Configure one-shot startup services or an explicit bootstrap command so a reviewer can reach a seeded demo with documented steps. Verify the final `docker compose up --build` behavior on a clean checkout and blank volumes **on the Mac architecture actually tested**. On Apple silicon, also record a Linux AMD64 CI result if you want to claim both architectures; otherwise clearly limit the compatibility claim.

Tests must use a separate database, never delete the demo database implicitly. A destructive demo reset must require an explicit flag. Record which Docker/dependency versions were tested.

**Acceptance:** A clean checkout works in fixture mode without API credentials; live mode documents exactly what credentials and outbound access are required.

## 29. Write the reviewer-facing artifacts

Create README, architecture notes, supported-OpenAPI-subset documentation, security/limitations notes, evaluation report, and a two-minute demo script.

README order: what it does, demo, quick start, architecture, reliability evidence, generated-connector explanation, measured evaluations, limitations, and credits/inspiration. Explain precisely what is yours versus FastAPI/FastMCP functionality. Describe the project as independent and inspired by public patterns, not an official Benchling implementation.

Demo sequence: upload/review/approve; inspect a historical check; run cited research; briefly show a retry/recovery test. Clearly label fixture mode or edited recording segments. Verify company/product references against original sources before publishing.

**Acceptance:** Another developer can understand the architecture and reproduce the demo without private context.

## 30. Release the core before expanding it

Run the complete test suite, inspect for secrets, run a clean-checkout demo, record the demo, and tag `v1.0` only after the gates pass.

Then add extensions in this order:

1. Reorder with threshold-transition events, one pending request per low-stock episode, and simulated fulfillment after approval.
2. A constrained text-based PDF importer with page/table provenance and validated chunk merging.
3. UniProt through another tested connector.
4. Embeddings only after comparison with the structured historical-retrieval baseline.

Dynamic subagents, conversation compaction, multi-tenant authorization, and public cloud deployment require separate scope and tests.

**Acceptance:** The first release contains a reliable connected story, not unfinished versions of every feature in the original brief.

---

# Appendix A: minimum persistence contract

Add these tables incrementally at their numbered steps, not all at once.

| Table | Essential columns and rules |
|---|---|
| `experiments` | id, name, target_id, assay_type, conditions JSONB, lifecycle status, recorded_outcome, failure_step, version, created_at, updated_at; outcomes are recorded data, not inferred facts |
| `samples` | id, unique canonical_code, label, metadata JSONB, version |
| `sample_aliases` | sample_id FK, alias; unique(sample_id, alias), nonunique alias across samples to represent ambiguity |
| `result_uploads` | id, experiment_id FK, original_filename, storage_key, sha256, media_type, byte_count, status, created_at; unique(experiment_id, sha256) |
| `events` | id, event_type, schema_version, aggregate_type/id/version, actor_id, immutable payload, correlation_id, causation_id, created_at; agent_runs records per-subscription delivery |
| `agent_runs` | id, event_id FK, subscription_id, agent_version, state, attempt_count, next_attempt_at, worker_id, lease_token, lease_expires_at, cumulative_usage JSONB, error, started_at, finished_at; unique(event_id, subscription_id) |
| `run_steps` | id, run_id FK, attempt, ordinal, kind, timestamps, sanitized inputs/outputs, error, model/prompt/tool versions |
| `import_proposals` | id, upload_id FK, run_id FK, revision, payload JSONB, content_hash, referenced_versions, state, decision metadata; unique(upload_id, revision), at most one applied proposal per upload |
| `measurements` | id, experiment_id/sample_id/upload_id/proposal_id FKs, source_record_index, source_columns, physical line range where available, measurement_name, raw_value/raw_unit, numeric_value NUMERIC, normalized_unit, created_at; unique(upload_id, source_record_index) for one-measurement-per-row scope |
| `molecules` | id, name, aliases, target_id, properties JSONB, is_synthetic |
| `study_assessments` | id, run_id, experiment_id, assessed_version, cutoff, scoring_version, evidence records/versions, computed counts, explanation, stale indicator |
| `research_requests` | id, target/query, version, status, created_at |
| `notebook_entries` | id, request_id/version, run_id, draft state, structured content, evidence IDs, created_at; one logical draft per request version |
| `evidence_records` | id, run_id, connector/version, source identifier, connector-supplied URL, fetched_at, content hash, bounded source snapshot, synthetic/live marker |

Retain immutable experiment-version snapshots or equivalent captured records to support reproducible historical checks. Source events and run steps are not a substitute for complete scientific provenance unless they retain the required versions and records.

# Appendix B: minimum API surface

These are project-defined routes to implement, not existing endpoints.

```text
GET  /health
GET  /ready
GET  /api/samples
POST /api/samples
GET  /api/samples/{id}
GET  /api/experiments
POST /api/experiments
GET  /api/experiments/{id}
POST /api/experiments/{id}/revisions
POST /api/experiments/{id}/uploads
GET  /api/uploads/{id}
GET  /api/runs
GET  /api/runs/{id}
GET  /api/import-proposals/{id}
POST /api/import-proposals/{id}/revisions
POST /api/import-proposals/{id}/approve
POST /api/import-proposals/{id}/reject
GET  /api/experiments/{id}/measurements
GET  /api/experiments/{id}/assessments
GET  /api/molecules
GET  /api/molecules/{id}
POST /api/molecules
POST /api/research-requests
GET  /api/research-requests/{id}
GET  /api/notebook-entries/{id}
GET  /api/evidence/{id}
```

The PubMed adapter is a separate integration surface:

```text
GET /articles/search?query=...&limit=...
GET /articles/{pmid}
```

Limit list pagination and returned payload sizes. Map validation, conflict, authorization, and transient upstream errors into distinct documented responses.

# Appendix C: coding-agent task template

Use this for one ticket at a time, not for generating the entire project in one request:

```text
Implement Step [NUMBER] from docs/implementation-plan.md.
The development machine is a Mac. Use Terminal/zsh-compatible commands.
Run API, worker, PostgreSQL, and MCP services through Docker Compose.
Run the Vite development server on the Mac with npm.
Do not assume Apple silicon versus Intel; inspect the environment first.
Do not force AMD64 images or mount host .venv/node_modules into Linux.
Read the relevant existing code and tests before editing.
Preserve the established stack and contracts.
Do not implement later phases, add unrelated infrastructure, or use real secrets.
Create or update the step's acceptance tests.
Use deterministic fakes unless this step explicitly requires a live integration.
Run the relevant tests and lint checks.
Report changed files, commands run, results, and any acceptance criteria not met.
Do not claim a test passed unless you executed it.
Stop after this ticket.
```

# Appendix D: extension tickets after v1.0

These tickets complete additional parts of the original brief without blocking the core release.

## E1. Reorder agent

Add `reagents`, `inventory_items`, `inventory_movements`, and `purchase_proposals`. Store quantities with units and prices with explicit currency and source timestamps. Seed historical vendor/price records, including missing-data cases.

Implement a stock-adjustment command that locks the inventory row, applies the change, checks the threshold transition, and emits `inventory.low` in the same transaction. Assign a low-stock episode ID, persist it while stock stays low, and reset it only after a defined recovery threshold. Enforce one pending purchase proposal per item/episode.

Calculate reorder quantity from a configured target-stock rule; look up vendor and cost from historical records. Unknown vendor/price remains unknown. Register a bounded reorder handler; an LLM may draft the explanation, not override quantities, prices, or approvals.

Generalize the already-tested proposal/decision service only where there is real overlap. Keep a specific purchase finalizer. Add reviewer-only approval, rejection, stale-inventory validation, and explicitly simulated fulfillment. Never place a real order in the portfolio demo.

**Acceptance:** Repeated low-stock updates create one pending request; rejection/approval is audited; fulfilled/superseded requests are not executed twice; missing vendor data is not fabricated.

## E2. Constrained PDF ingestion and chunked extraction

Choose three text-based table PDFs with expected row-level outputs and record the chosen parser/version/license. Add media-type routing while keeping CSV behavior unchanged.

Extract text/tables with page and table coordinates. Chunk on table/row boundaries with stable chunk IDs; retain an overlap policy and deduplicate using source coordinates rather than generated values.

Use typed per-chunk model output and a deterministic validated reducer. Keep raw reported text and unit strings; resolve entities through the same resolver as CSV. Explicitly identify unreadable pages, missing rows, or ambiguous cells instead of inventing values.

Reuse the immutable proposal/review workflow. Include a test where a model omits or duplicates a row so the reducer catches it. Do not claim support for scans, arbitrary layouts, or OCR until those get separate fixtures and tests.

**Acceptance:** Every committed measurement links to a source page/table/cell or exact text span; fixture outputs match expected rows and problematic regions remain reviewable.

## E3. UniProt connector

Verify UniProt's current official API documentation and the exact operations needed before coding. Start with protein search and accession detail, not unrestricted endpoint coverage.

Test one real request for each operation. Use a supplied OpenAPI document only after checking that it covers those operations; otherwise write a small normalized adapter and label that boundary explicitly.

Normalize accession, protein/gene names, organism, relevant annotations, source links, retrieval time, and response snapshots. Bound results and response size; configure authentication/rate behavior from current official guidance.

Run the existing generator, MCP contract tests, and an explicit live smoke test. Add only these new read tools to Research's allowlist, while preserving its cumulative budgets and evidence requirements.

**Acceptance:** Research accesses the third source through MCP, cites real accession records, and remains correct when the source is unavailable or returns no match.

## E4. Embedding retrieval and optional provider routing

Freeze a held-out historical-check benchmark and record the structured baseline first. Define a deterministic textual representation of each experiment without leaking its future outcome into query construction.

Add vector storage and migrations, record embedding model/version and source experiment version, and implement reindexing for changed designs. Combine vector ranking with the same explicit target/assay filters.

Compare relevant-history recall, irrelevant-match rate, abstention behavior, latency, and cost against the baseline. Enable vectors only when the measured tradeoff is useful, keeping evidence IDs/versions unchanged.

A second LLM provider and cheap/strong model routing are separate enhancements. Add adapters behind the same interface, contract-test structured output and errors, and measure quality/cost on the same fixtures before introducing automatic routing or fallback.

**Acceptance:** The evaluation, not a library choice, explains why the enhancement is enabled. Provider failures and fallback remain visible in traces.

# Appendix E: everyday Mac commands and troubleshooting

Run commands from the project root unless a block explicitly changes directory. Application commands here are **targets for implemented steps**, not tools supplied by this document.

## E.1 Save this plan into your repository

After downloading this document and creating the repository, copy it into `docs/implementation-plan.md`. Finder can do this; when the download has the filename used here, the Terminal command is:

```bash
cd "$HOME/Developer/mini-benchling-agents"
mkdir -p docs
cp "$HOME/Downloads/Mini_Benchling_Agents_Implementation_Plan_macOS.md" docs/implementation-plan.md
```

Use the actual download location when your browser saves elsewhere. Do not overwrite local edits to the plan without reviewing the difference.

## E.2 Start and inspect the backend

After Step 10 and migrations/seeding:

```bash
cd "$HOME/Developer/mini-benchling-agents"
open -a Docker
docker info
docker compose up -d --wait db
docker compose up --build -d api worker
docker compose ps
docker compose logs -f api worker
```

`Ctrl+C` stops log following; it does not stop detached services. Add the named adapter/MCP services to this startup routine once their implementation steps are complete. Keep foreground Vite in its own terminal.

## E.3 Run frontend and checks

Frontend development:

```bash
cd "$HOME/Developer/mini-benchling-agents/web"
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Lint and deterministic unit tests on the Mac, once the test directories contain tests:

```bash
cd "$HOME/Developer/mini-benchling-agents"
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/unit -q
```

Database/runtime tests in the isolated test stack:

```bash
docker compose -p minibench-tests -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
```

Cleanup of **only the isolated test stack** after its command exits:

```bash
docker compose -p minibench-tests -f compose.test.yaml down -v
```

This cleanup deliberately deletes test volumes. The test Compose file must not declare demo volumes as external or reuse global demo volume names. In CI, capture the test command's exit status before cleanup so successful cleanup cannot hide failing tests.

## E.4 Apply schema and dependency changes

Migration generation requires a database connection. After adding the relevant ORM models and wiring Alembic metadata, run it **inside a running API container with `migrations/` bind-mounted to the repository**:

```bash
docker compose exec api uv run alembic revision --autogenerate -m "describe_the_schema_change"
```

Use the container form by default. Review the generated migration before applying it; configure the development mount and write permissions so the file appears on the Mac. Do not use a host `DATABASE_URL` containing the Compose-only hostname `db`.

Apply reviewed migrations:

```bash
docker compose run --rm api uv run alembic upgrade head
```

Dependency changes:

```bash
uv add package-name
```

`package-name` is a placeholder, not a dependency to install. After making actual dependency changes and committing `uv.lock`, rebuild:

```bash
docker compose build api worker
docker compose up -d api worker
```

Migrations that remove columns or otherwise break running workers need a planned stop/restart sequence; this demo should normally make schema changes with worker execution stopped.

## E.5 Stop without deleting your data

```bash
docker compose stop
```

Or remove the normal containers/network while preserving named volumes:

```bash
docker compose down
```

Do not add `-v` to the normal demo command unless you explicitly intend to erase its volumes. Use the planned reset command with an explicit destructive flag for demo resets.

## E.6 Common Mac setup problems

| Symptom | Action |
|---|---|
| `brew: command not found` | Follow the installer's PATH instructions; check the architecture-appropriate Homebrew prefix and open a new terminal. |
| `node` reports the wrong major | Run `which -a node`; keep one intentional Node selection. For the Homebrew path, add `$(brew --prefix node@24)/bin` as in Step 01d. |
| `uv: command not found` | Check the chosen installer and its PATH instructions; do not install into system Python as a workaround. |
| Docker client works but server is unavailable | Open Docker Desktop, finish first-run configuration, and run `docker info` again. |
| Port 8000 or 5173 is already used | Identify the listener with `lsof -nP -iTCP:8000 -sTCP:LISTEN` or the equivalent command with port 5173. Stop only a process you recognize, or deliberately change the mapping and proxy together. |
| Host process cannot resolve `db` | `db` is a Compose-network hostname. Prefer the documented container command; a deliberate host-debug setup needs its own published DB port and host-side URL. [M13] |
| Connector calls `localhost` and cannot reach the API | Inside Compose, point it to `http://api:8000`; `localhost` refers to the connector itself. [M13] |
| ARM/AMD64 warning or binary architecture error | Inspect the Mac/terminal architecture, image manifest, and native dependencies. Remove unjustified architecture overrides and rebuild the appropriate variant; do not treat emulation as the automatic default. [M11] |
| Mac virtual environment breaks inside a container | Remove the host dependency mount from Compose; build/install dependencies inside Linux. Preserve the lockfile, not the host binaries. [M12] |
| Docker cannot mount the source directory | Keep the checkout under `~/Developer` and check Docker Desktop's configured file-sharing access for that directory. |
| Import works on Mac but fails in Linux CI | Check exact path/filename capitalization and ensure the file was committed. For a case-only rename, use a temporary distinct name with `git mv`. |
| `zsh: no matches found` for dependency extras | Quote extras, for example `"uvicorn[standard]"` and `"psycopg[binary]"`. |
| `code: command not found` | Use VS Code's Command Palette to install its shell command, or use File > Open Folder. [M9] |
| Model calls stop after the Mac sleeps | Inspect lease/retry recovery when the machine resumes. This local demo does not keep running reliably while the Mac or Docker is unavailable. |

## E.7 First-session finish line

Complete Steps 01-03 first. The deliverable is a correctly configured Mac, a repository with locked dependencies, a running API container, a healthy PostgreSQL container, and passing health/readiness checks. No prompts, external science calls, or dynamic agents are needed yet.

# Technical references

Mac/tooling references below were consulted for this revision on September 22, 2026. Check the selected installer and locked package versions before building, particularly on older Intel Macs. These sources support platform/framework behavior, not the project's unmeasured performance or acceptance results.

- [M1] Homebrew installation, prefixes, prerequisites, and support: `https://docs.brew.sh/Installation`
- [M2] Homebrew official installer: `https://brew.sh/`
- [M3] uv installation, Homebrew, and standalone Mac installer: `https://docs.astral.sh/uv/getting-started/installation/`
- [M4] Docker Desktop Mac installation and architecture selection: `https://docs.docker.com/desktop/setup/install/mac-install/`
- [M5] Homebrew Node 24 formula and keg-only status: `https://formulae.brew.sh/formula/node@24`
- [M6] Vite Node requirements, scaffolding, and commands: `https://vite.dev/guide/`
- [M7] Official Node downloads and release selection: `https://nodejs.org/en/download/`; Docker Desktop cask: `https://formulae.brew.sh/cask/docker-desktop`
- [M8] uv-managed Python installation: `https://docs.astral.sh/uv/guides/install-python/`
- [M9] VS Code macOS shell command: `https://code.visualstudio.com/docs/setup/mac`
- [M10] uv project initialization: `https://docs.astral.sh/uv/concepts/projects/init/`
- [M11] Docker platform manifests and builds: `https://docs.docker.com/build/building/multi-platform/`
- [M12] uv Docker integration and virtual-environment separation: `https://docs.astral.sh/uv/guides/integration/docker/`
- [M13] Compose networking and service names: `https://docs.docker.com/compose/how-tos/networking/`
- [M14] Docker Desktop host-service networking: `https://docs.docker.com/desktop/features/networking/`
- [M15] Compose readiness/startup dependencies: `https://docs.docker.com/compose/how-tos/startup-order/`
- [M16] Compose `up` options, including `--wait`: `https://docs.docker.com/reference/cli/docker/compose/up/`

Architecture reference list retained from the original plan; match each implementation to its installed framework version:

- uv projects and lockfiles: `https://docs.astral.sh/uv/guides/projects/`
- FastAPI/Pydantic contracts and OpenAPI: `https://fastapi.tiangolo.com/tutorial/body/`
- PostgreSQL queue-like locking: `https://www.postgresql.org/docs/current/sql-select.html`
- FastMCP OpenAPI conversion and allowlist/exclusion behavior: `https://gofastmcp.com/integrations/openapi`
- MCP security and token passthrough: `https://modelcontextprotocol.io/specification/draft/basic/security_best_practices`
- NCBI search/fetch: `https://eutilities.github.io/site/Quick_Start/eu_quick/`
- NCBI request limits: `https://eutilities.github.io/site/API_Key/usageandkey/`
