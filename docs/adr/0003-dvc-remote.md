# ADR 0003 — DVC for the reference dataset; remote is a local folder for now

## Decision
- Track `data/reference/` (a fixed one-week extract of both real sources,
  built by `scripts/build_reference_dataset.py`) with DVC, not Git.
- DVC remote `storage` is a **local folder** (`../dataops-dvc-storage`,
  sibling to the repo, outside Git entirely), the same choice TP2 makes
  before introducing a shared remote. **To migrate later:** once
  docker-compose brings up MinIO (step 11), `dvc remote add -d storage
  s3://<bucket>/dvc --endpointurl http://localhost:9000` replaces this one
  line in `.dvc/config` -- nothing about how the data is tracked changes.

## Why a separate reference dataset, not the CI sample
`tests/fixtures/*.csv` (step 7) stay in plain Git on purpose -- TP4 is
explicit that a small, stable test fixture belongs in Git, not DVC. DVC
exists for something **too big or too likely to change** to live
comfortably in Git history. `data/reference/` is that: 8064 + 2016 rows
(1.6 MB), useful for testing the pipeline against something closer to real
volume without re-hitting the live APIs every time, and for rehearsing the
backfill mechanics (step 10) before doing it for real against 1M+ rows.

## Why a fixed date range (2026-09-01 to 2026-09-07), not "the last 7 days"
A reference dataset has to produce the exact same file every time it's
rebuilt, or `dvc status` would show it as changed on every run for no
reason. A sliding window breaks that guarantee by definition. The chosen
week is also safely past the real-time dataset's freshest-hours null gap
(ADR 0002 addendum), confirmed empirically: 0 of 8064 rows have an empty
`consommation`.

## Known limitation (documented, not hidden)
Because the remote is a local folder outside Git, **`dvc pull` only works
on this machine** right now -- cloning the repo elsewhere (another machine,
Codespaces) gives `data/reference.dvc` but no actual data until the remote
moves to MinIO in step 11. This mirrors TP2's own progression (local folder
first, "a real remote" later) and is called out explicitly so it isn't
mistaken for a bug during the individual exam or the defense.

## Alternatives rejected
- Putting `data/reference/` straight into Git: 1.6 MB isn't huge, but it
  would only grow if the reference window is ever widened, and Git handles
  binary/large-ish files far worse than DVC's content-addressed storage.
- Skipping a reference dataset and only relying on the tiny CI fixture:
  the CI fixture is deliberately too small (10/6 rows) to catch issues that
  only show up at realistic volume (pagination, performance, a rule that
  behaves differently on a handful of edge-case rows the tiny fixture
  doesn't contain).
