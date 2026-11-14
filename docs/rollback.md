# Rollback procedure

## What a release is

`git tag vX.Y.Z && git push origin vX.Y.Z` triggers
`.github/workflows/release.yml`, which builds the pipeline image
(the same `Dockerfile` `docker-compose.yml`'s `worker` service builds
locally) and pushes it to GHCR tagged both `X.Y.Z` (no "v" --
`docker/metadata-action`'s semver pattern strips it; confirmed by
checking what actually got pushed, not assumed from the git tag's own
name) and `latest`. Publishing is a deliberate act -- it never happens
on a plain merge to `main`, only on an explicit tag push.

## A real limitation, documented rather than hidden

`docker-compose.yml`'s `worker`/`metabase-setup` services bind-mount the
live repo (`.:/app`, ADR 0005) so local development always runs today's
code without a rebuild. That same bind mount means a container built
from an older image still runs whatever code is currently checked out
on the host -- **the image rollback below only rolls back the baked
Python *dependencies***, not the application code. Rolling back both
together means two steps, not one:

1. `git checkout vX.Y.Z` (or `git switch` to whichever commit that git
   tag points at) on the host.
2. The image rollback below, for the dependency versions baked at that
   same release.

## Procedure (tested, see below)

1. Find the last known-good *image* tag -- `git tag --sort=-v:refname`
   lists the git tags (`v0.1.0`), but the value `RELEASE_TAG` needs is
   the published image tag without the "v" (`0.1.0`); the GHCR package
   page lists those directly.
2. Set `RELEASE_TAG=<that tag>` in `.env` (e.g. `0.1.0`).
3. Pull and redeploy:
   ```
   docker compose -f docker-compose.yml -f docker-compose.prod.yml pull worker metabase-setup
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```
4. Confirm which version is actually running (inspect the image's own
   label, not a file under `/app` -- that path is bind-mounted, so it
   always reflects the host's current checkout, never the image):
   ```
   docker inspect ghcr.io/ahmednouhaz/dataops-energy-platform:$RELEASE_TAG \
     --format '{{index .Config.Labels "org.opencontainers.image.version"}}'
   ```
5. If the code also needs to roll back: `git checkout v<that tag>` on
   the host (the "v" prefix comes back for the git tag).

## Tested for real

See `docs/learning_log.md`'s step 15 entry for the actual tag-push,
publish, and rollback verification performed after this workflow first
merged to `main` (a tag can only trigger `release.yml` once that file
exists on the commit being tagged).
