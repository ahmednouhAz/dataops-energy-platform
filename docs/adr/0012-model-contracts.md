# ADR 0012 — Bonus: `contract: enforced` on the marts that can take it

## Decision
`config: {contract: {enforced: true}}` + a `data_type:` on every column,
added to the 5 marts with an explicit column list already:
`dim_region`, `dim_energy_source`, `dim_date`, `fct_energy_production`,
`fct_consumption_weather`. **Not** added to `eco2mix_rejected`, which
deliberately does `select *` (see below).

## Why this, and why not everywhere
A data contract (`contracts/*.yaml`, step 7) checks the *source's*
shape at ingestion. A dbt model contract checks a *mart's* shape at
build time -- if a future change to an upstream model, a dbt version
bump, or a typo accidentally changes a mart's column names, types, or
order, the build fails loudly instead of silently handing the dashboard
(or anyone else downstream) a differently-shaped table.

`eco2mix_rejected` keeps `select *` on purpose (its own comment: every
column `int_eco2mix_checked` carries, whatever that turns out to be).
A contract requires an *exact*, explicit column list -- enforcing one
here would mean hand-listing every raw measurement column, the opposite
of why this model uses `select *` in the first place (so it doesn't
need updating every time a raw column is added or renamed upstream).
Forcing a contract onto it would fight its own design, not improve it.

## A real blocker, found by running it, not by reading dbt's docs first
`dbt build --full-refresh` on the first attempt:
```
Invalid value for on_schema_change: sync_all_columns. Models
materialized as incremental with contracts enabled must set
on_schema_change to 'append_new_columns' or 'fail'
```
`fct_energy_production`'s `on_schema_change='sync_all_columns'` (set
when the model was first built, step 5) is incompatible with a contract.
Changed to `'fail'` -- the more correct choice anyway: a contract's
whole point is that a shape change should stop the build, not get
silently synced into the table underneath it, which is exactly what
`sync_all_columns` would otherwise do.

A second, smaller thing found the same way: putting a `--` SQL comment
inside a Jinja `config(...)` call is a compilation error (`invalid
syntax for function call expression`) -- Jinja parses the arguments as
an expression, not SQL, so `--` isn't a comment there. Used a Jinja
`{# ... #}` comment block above the `config()` call instead.

## Proved it actually catches something, not just that it compiles
Changed `dim_region.latitude`'s declared `data_type` from `double` to
`integer` and ran `dbt build --select dim_region`: failed immediately
with
```
| column_name | definition_type | contract_type | mismatch_reason    |
| latitude    | DOUBLE          | INTEGER       | data type mismatch |
```
-- the exact, actionable error a contract is supposed to produce.
Reverted immediately after confirming it; `git diff --stat` showed only
the intended 46-line addition remaining.

## Alternatives rejected
- Contract on every mart including `eco2mix_rejected`: rejected above --
  would mean giving up the `select *` design this model exists for.
- Leaving `on_schema_change='sync_all_columns'` and dropping the
  contract from `fct_energy_production` instead (the one model where
  this conflict showed up): rejected -- it's the *biggest* mart, and
  the one most worth protecting from an accidental shape change, since
  it's also the one the dashboard and the daily flow depend on most
  directly.

## Verification
- `dbt build --full-refresh`: `PASS=42/43` (1 exposure, no-op by
  design), all 5 contracted marts build and validate against their
  declared schema.
- Deliberately broke `dim_region`'s contract (wrong `data_type`):
  `dbt build --select dim_region` failed with the exact mismatch
  reported, as expected. Reverted, confirmed clean, rebuilt --
  `PASS=42/43` again.
- `ruff check .`, full `pytest`: unaffected, still green.
