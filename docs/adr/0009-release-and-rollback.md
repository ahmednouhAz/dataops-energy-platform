# ADR 0009 — Continuous delivery: GHCR releases and rollback

## Decision
- `.github/workflows/release.yml`: on a `v*` tag push (not on a plain PR
  or merge -- publishing is a deliberate act), builds the same
  `Dockerfile` the `worker` service already builds locally and pushes it
  to GHCR tagged both the exact version and `latest`.
- `docker-compose.prod.yml`: an override file swapping the `worker`/
  `metabase-setup` services' `build: .` for a pull of a specific
  published tag (`RELEASE_TAG` in `.env`), used with `docker compose -f
  docker-compose.yml -f docker-compose.prod.yml`.
- "Dev vs prod environments" (the checklist's separate bullet from GHCR
  publishing) is already satisfied by existing work, not new to this
  step: dbt's `dev`/`prod`/`ci` targets (step 4), and
  `PROD_DUCKDB_PATH`/`SERVING_DUCKDB_PATH` vs. the interactive
  `DUCKDB_PATH` (step 11/12) already keep the two from ever touching the
  same file.
- `docs/rollback.md`: the documented, tested procedure.

## A real limitation this step's testing surfaced, not fixed by inventing a new deployment topology
`docker-compose.yml`'s bind mount (`.:/app`, ADR 0005) exists so local
dev always runs today's code with no rebuild step. That same bind mount
means a container started from an *older* published image still runs
whatever code the host's git working tree currently has checked out --
confirmed directly by inspecting the merged Compose config
(`docker compose ... config`), not assumed. Two ways to handle this were
considered:
1. **Restructure the prod topology** so `worker`/`metabase-setup` don't
   bind-mount at all in prod mode, with a separate named volume for the
   warehouse files they'd otherwise write under `/app`. Tried this first
   (`volumes: !reset []` -- the Compose Specification's actual mechanism
   for clearing a merged list from an override file; plain `build: null`
   and an empty-list override were both tested and confirmed to do
   nothing, Compose just ignores them). It worked, but needed a second
   shared volume, a second set of path env vars for the prod case only,
   and a rework of `scripts/setup_metabase.py`'s hard-coded data path --
   real new infrastructure for a project whose actual deployment target
   is still "one desktop running Docker Compose," not a remote server
   where this distinction would matter for real.
2. **Document the real constraint honestly instead**: the image rollback
   below rolls back the baked *dependencies*; rolling back the *code*
   too is a second, explicit step (`git checkout <tag>` on the host).
   Chosen over option 1 -- it's the truthful answer for this project's
   actual architecture, not a workaround that hides what bind-mounting
   for dev convenience actually costs.

## Why `release.yml` is a separate workflow, not a job added to `ci.yml`
`ci.yml` runs on every PR and every push to `main` -- if the release job
lived there, every ordinary merge would attempt a GHCR push (and either
need its own gating logic to skip most of the time, or actually publish
constantly). A separate workflow, triggered only by `v*` tags, makes
"this merge is now a release" an explicit, separate action
(`git tag vX.Y.Z && git push --tags`), matching this project's own git
workflow rule (CLAUDE.md section 6): nothing happens to shared state
without a deliberate step.

## How to actually tell which version is running
Not a file under `/app` -- bind-mounted, always reflects the host's
current checkout regardless of which image is deployed. The image's own
OCI label does: `docker/metadata-action`'s `type=semver` tag pattern
also sets `org.opencontainers.image.version`, readable with `docker
inspect <image> --format '{{index .Config.Labels
"org.opencontainers.image.version"}}'` -- this is what `docs/rollback.md`
actually checks to confirm a rollback worked, not just that the
`pull`/`up` commands exited 0.

## Alternatives rejected
- Adding the release job to `ci.yml`: rejected above.
- Restructuring the prod topology to make the bind-mount limitation
  disappear entirely: rejected above, in favor of documenting the real
  tradeoff.
- Checking a baked `VERSION` file inside the image instead of an OCI
  label: would work, but duplicates information `docker/metadata-action`
  already derives correctly from the git tag -- one more thing to keep
  in sync for no benefit over reading the label Docker already sets.
