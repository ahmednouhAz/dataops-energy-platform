# ADR 0011 — Bonus: pre-commit hooks, SQLFluff, conventional commits, and closing the devcontainer issue

## Decision
Four of CLAUDE.md's "easy wins first" bonus items, picked because each
was genuinely cheap and still real (not a token gesture):
- **SQLFluff**: `.sqlfluff` (dialect `duckdb`, jinja templater with
  `apply_dbt_builtins`) lints every model, singular test, and seed.
  `.sqlfluffignore` excludes `models/governance/` (see below).
- **Pre-commit hooks**: `.pre-commit-config.yaml` -- `trailing-whitespace`,
  `end-of-file-fixer`, `check-yaml`, `check-added-large-files`,
  `check-merge-conflict`, `ruff --fix`, `sqlfluff-lint`.
- **Conventional commit messages**: `conventional-pre-commit`, a
  `commit-msg` hook, restricted to the exact types CLAUDE.md section 6
  already names for branch prefixes (`feat`/`fix`/`chore`/`docs`/`test`/
  `ci`/`refactor`) -- every commit this project has made already follows
  this by hand; the hook just catches a slip before it happens instead
  of at review time.
- **Closed the standing devcontainer issue** (CLAUDE.md section 2,
  "Open issues" since step 0): verified, don't just assume.

## Why these four specifically, not others from the list
"Cheapest first," genuinely: each took under an hour, none required new
infrastructure (no new service, no new cloud account), and each is
either already-partially-true (conventional commits -- this project's
own git history already follows the convention) or catches something a
later, more expensive step would otherwise have to catch by hand every
time (SQLFluff/pre-commit, vs. relying on remembering to run `ruff
check .` before every commit). Compare to e.g. OpenLineage+Marquez or
the level-2 lakehouse migration, both explicitly bigger asks on the same
list.

## SQLFluff found real issues, but most were style, not bugs
Linting the actual models surfaced ~30 findings. Investigated each
category rather than blanket-suppressing everything:
- **Fixed for real** (`models/marts/fct_energy_production.sql`): an
  unqualified `date_heure` reference across the main select and the
  `is_incremental()` subquery (`RF02`). Added table aliases
  (`p`/`prev`) -- a genuine clarity improvement, zero behavior change,
  confirmed with `dbt build` (`PASS=42/43`, unchanged).
- **Tried, then reverted** (`models/intermediate/int_eco2mix_checked.sql`):
  the same `RF02` finding on its `unknown_region` check. Aliasing just
  that one reference left every *other* column in the same `case when`
  chain newly flagged as "inconsistently qualified" (`RF03`) -- a worse
  state than before, since partial qualification is worse than
  consistent non-qualification. Fully qualifying the whole file (every
  reference in a long, heavily-commented rule chain) was judged a
  bigger, riskier change than this bonus item warrants. Reverted;
  `AM04`/`RF02`/`RF03`/`RF04` excluded project-wide instead, with the
  reasoning written directly into `.sqlfluff` so it isn't mistaken for
  "nobody looked at these."
- **Excluded as pure style** (`LT01`/`LT02`/`LT09`/`ST06`): indent
  width, one-select-target-per-line, column ordering. These would mean
  reformatting every existing model (all of which already follow the
  TP course's own established style, which the teacher already
  recognizes) for no functional benefit.
- **A parsing limitation, not a style choice**
  (`models/governance/demo_pii_masking.sql`): the lightweight `jinja`
  templater (no live dbt connection) can't resolve the custom
  `mask_pii()` macro, so the file fails to parse at all under SQLFluff.
  The accurate fix (the heavier `dbt` templater) needs a working
  profile/connection at lint time -- not worth it for one demo file.
  Excluded via `.sqlfluffignore` instead of silencing the rule (silencing
  wouldn't have helped -- it's a parse failure, not a rule violation).

## The devcontainer issue: verified, not just re-asserted
CLAUDE.md has carried "devcontainer failed to build in Codespaces
twice... TODO: fix and verify" since step 0, with no verification since.
Rather than re-pin a tag and hope, tested the actual two failure points
directly:
- `docker pull mcr.microsoft.com/devcontainers/python:1-3.12-bookworm`:
  succeeds -- the currently-pinned base image is real and pullable.
- `docker run` that same image, mount this repo, run the exact
  `postCreateCommand` (`pip install -r requirements.txt`): succeeds,
  every dependency installs cleanly.
- Added `pre-commit install --hook-type pre-commit --hook-type
  commit-msg` to `postCreateCommand` (this step's own addition) and
  re-verified the combined command still succeeds end to end.

**What this does and doesn't prove**: this confirms the image and the
setup command both work in a plain Docker container, which is most of
what Codespaces actually does under the hood. It does **not** prove the
`docker-in-docker` *feature* resolves identically inside the real
Codespaces orchestration layer, or rule out a Codespaces-specific
resource/network constraint -- that needs an actual Codespaces session,
which wasn't available to test from here. Documented as "substantially
de-risked, not 100% closed" rather than claiming more certainty than
was actually earned.

## A real bug, found by testing the devcontainer end to end, not just the base image
First pass at verifying the devcontainer tested `pip install -r
requirements.txt` on its own, then separately confirmed `pre-commit
install` works -- but never the *combined* `postCreateCommand` exactly
as written. Running it exactly as written failed: `pre-commit: command
not found`, because `pre-commit` itself was never added to
`requirements.txt` -- the local venv had it from a manual `pip install
pre-commit` earlier in this same session, which masked the gap until
the devcontainer's from-scratch install exposed it. Fixed by adding
`pre-commit>=3.0,<5` to `requirements.txt`; re-ran the exact combined
command and confirmed `pre-commit installed at .git/hooks/pre-commit`
and `...commit-msg` both printed, with a final `POSTCREATE_OK` marker
reaching the end of the chain.

## Verification
- `sqlfluff lint models data_tests seeds`: clean (0 findings) with the
  final `.sqlfluff`/`.sqlfluffignore`.
- `pre-commit run --all-files`: all 7 hooks pass (after accepting the
  whitespace/EOF fixes it made to several pre-existing files on its
  first run).
- `pre-commit install` + a direct `conventional-pre-commit` run:
  rejects `"this is not a conventional commit message"`, accepts
  `"feat: add pre-commit hooks and sqlfluff (step 18)"`.
- Devcontainer: `docker pull` + `docker run` with the exact
  `postCreateCommand` (including the new `pre-commit install` step),
  both succeed, confirmed by exit code and the full dependency list
  installing without error.
- `dbt build`: `PASS=42/43` unchanged after the `fct_energy_production.sql`
  qualification fix. `ruff check .`, full `pytest`: unaffected, still
  green.
