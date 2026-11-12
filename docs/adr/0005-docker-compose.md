# ADR 0005 — Docker Compose services, and the free MinIO image disappearing

## Decision
- `Dockerfile`: one image for the pipeline (`python:3.12.7-slim-bookworm`
  + `requirements.txt` + `git`, needed by dbt even with no packages
  installed yet -- found via `dbt debug`).
- `docker-compose.yml` starts four things: `minio` (object storage),
  `minio-setup` (a one-shot job that creates the DVC bucket, then exits),
  `prefect-server` (no flows registered against it yet -- that's step 12),
  and `worker` (our image, bind-mounting the real repo over `/app`, kept
  alive with `sleep infinity` so it can be `docker compose exec`'d into).
- `.env.example` committed, `.env` gitignored, no secret in either --
  `.env.example`'s values are placeholder dev defaults, not real
  credentials.
- DVC's `storage` remote (ADR 0003's local-folder remote) now points at
  this MinIO instance instead, as ADR 0003 said it eventually would.

## A real, unanticipated problem: the free MinIO image is gone
CLAUDE.md's plan (written before this step) assumed `minio/minio` on
Docker Hub, the standard choice in every MinIO tutorial. Running
`docker pull minio/minio` today returns `pull access denied for
minio/minio, repository does not exist`. On 2025-10-23, MinIO stopped
publishing the free Community Edition image to Docker Hub *and* its
`quay.io` mirror -- confirmed by testing both registries directly, not
just reading about it: both returned an access-denied/unauthorized error
rather than resolving the image at all.

**Alternative found and verified working:** Chainguard publishes a free,
unofficial-but-actively-maintained MinIO image at
`cgr.dev/chainguard/minio`. Pulled and ran it directly:
- It only ships a `latest` tag (no versioned tags on the free tier), which
  conflicts with CLAUDE.md's "pin image versions" rule on its face. Pinned
  by **digest** instead (`cgr.dev/chainguard/minio@sha256:786c...`) --
  stricter than a version tag, since a digest can never move underneath
  you even if `latest` is later retagged to a new build.
- It's a minimal image: no shell utilities beyond coreutils/bash, no
  `curl`/`wget`. The standard `curl -f .../minio/health/live` healthcheck
  pattern doesn't work here. Used bash's `/dev/tcp` pseudo-device instead
  (`exec 3<>/dev/tcp/localhost/9000`) -- a raw TCP connection attempt with
  no extra binary required, confirmed to work by testing it against the
  image directly before writing it into the compose file.
- It bundles `mc` (the MinIO client) in the same image, so `minio-setup`
  reuses the `minio` image with a different entrypoint instead of pulling
  a separate `minio/mc` image (also hit the same October 2025 Docker Hub
  removal, confirmed the same way).
- Runs as a non-root user (UID 65532). A bind-mounted host directory would
  need a manual `chown` first to be writable by that UID; a **named Docker
  volume** avoids the problem entirely, since Docker initializes a fresh
  named volume's permissions from the image's own filesystem at that path.
  That's why `minio-data` is a named volume, not `./minio-data:/data`.

## Why `prefect-server` runs now, with no flows yet
Step 12 builds the actual daily/backfill flows and needs somewhere to
register and run them; starting the server here means `worker`'s
`PREFECT_API_URL` already points at something real today, and step 12 is
pure flow code with no new infrastructure to stand up. No healthcheck is
defined on it yet -- nothing depends on strict readiness before a flow
exists to register, so `depends_on: condition: service_started` is enough
for now; may need tightening in step 12 if flow deployment races the
server's startup.

## Why the worker bind-mounts the repo instead of only using the image's own COPY
The Dockerfile's `COPY . .` matters for the image GHCR will serve in step
15 (no host filesystem to mount there). For local dev, `docker-compose.yml`
bind-mounts `.:/app` over it, so the container always runs today's code
with no rebuild step -- the same live-edit workflow as running locally,
but now also usable by a newcomer with no Python/dbt/DuckDB installed on
the host at all, only Docker. Verified directly: `docker compose exec
worker python -m pytest` (15 passed) and `docker compose exec worker dbt
build --select dim_region` (PASS=6) both ran against the exact same
`dev.duckdb` the host sees, with nothing installed outside the container.

## A quirk found, not fixed: `ruff check .` fails differently inside the container
Running `ruff check .` inside the worker (bind-mounted repo) reports 20
`EXE002` errors ("executable but no shebang") on files that pass `ruff
check .` cleanly on the host and in CI. Cause: Docker Desktop's Windows
bind-mount translation reports every file as executable (NTFS has no
POSIX executable bit to translate, so it defaults to `755` for everything
shared this way), which a normal Linux checkout -- including the one
GitHub Actions does for `ci.yml` -- never produces, since mode bits come
from git's own index there, not a Windows filesystem. Deliberately **not**
"fixed" by disabling the rule: that would weaken `ruff` for Linux/macOS
contributors and CI, to paper over an artifact of developing on Windows
specifically. Lint stays something you run on the host or let CI run;
`docker compose exec worker pytest`/`dbt build` are what the container is
actually for.

## Alternatives rejected
- `bitnami/minio`: also lost its free, maintained tags (migrated to an
  unsupported `bitnamilegacy` archive starting 2025-08-28) -- same
  problem as upstream MinIO, just discovered slightly later in the
  process.
- A random third-party Docker Hub mirror of the old `minio/minio` image:
  would work, but trusting an unverified rebuild of a storage server for
  a project's object storage is a supply-chain risk not worth taking when
  a vendor-published free alternative (Chainguard) exists.
- Writing a bucket-creation script in Python/boto3 instead of using `mc`:
  `boto3` is already a dependency (via `dvc[s3]`), so this was briefly
  considered, but `mc` ships inside the image we already pulled, needs no
  extra code, and is the standard tool for the job.

## Verification
- `docker compose up -d --build`: `minio` healthy, `minio-setup` exited 0
  with `Bucket created successfully`, `prefect-server` and `worker` up.
- `docker compose exec worker python -m pytest -q`: 15 passed.
- `docker compose exec worker dbt debug`: all checks passed (after adding
  `git` to the image).
- `docker compose exec worker dbt build --select dim_region`: PASS=6,
  against the same `dev.duckdb` the host's own `dbt build` writes to.
- `curl`-equivalent health check from inside `worker` to
  `http://prefect-server:4200/api/health`: HTTP 200.
- DVC remote migration: `dvc push` to the new MinIO remote, then deleted
  `data/reference/` *and* `.dvc/cache`, `dvc pull` restored both files
  with their exact original line counts (8065 and 2017 lines, header
  included) -- the same recovery proof ADR 0003 did for the local-folder
  remote, now repeated against MinIO.
