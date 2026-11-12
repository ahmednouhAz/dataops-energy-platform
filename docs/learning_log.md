# Learning log

One entry per roadmap step. Each entry: what was done, what I learned, my answers to
the step's questions. Written as I go, in "just do it, explain after" mode when I ask
Claude to move fast (see CLAUDE.md rule 8).

---

## Step 0 — Local setup on the desktop PC (2026-11-12)

### What was done
- Checked the machine: Python (only 3.14 was installed), Git, Docker CLI/daemon,
  GitHub CLI (`gh`, already logged in as `ahmednouhAz`), git identity.
- Installed **Python 3.12** with `winget install Python.Python.3.12`, alongside the
  existing 3.14 (not replacing it), because `dbt-duckdb` does not support 3.14 yet.
  Windows's `py` launcher (`py -0p`) can now list and pick between both.
- Started the Docker Desktop application so the daemon is running (the CLI
  `docker --version` answers even when the daemon isn't started — that only proves the
  client is installed, not that containers can run; `docker ps` is the real test).
- Turned this folder into the real clone of the GitHub repo
  (`ahmednouhAz/dataops-energy-platform`): `git init`, added `origin`, fetched, and
  reset `main` to `origin/main`. Safe because there were zero local commits yet, and
  none of the files already on this machine (`CLAUDE.md`, `course/`) exist on the
  remote, so nothing was overwritten.
- Found that `.gitignore` did **not** actually exclude `course/` or the local
  `.claude/` settings folder, even though `CLAUDE.md` assumed `course/` was already
  ignored. Fixed `.gitignore` to add both.
- Added `CLAUDE.md` to the repo (it is meant to be committed — it's the project's
  instructions file, not a secret or generated file).
- Created this file and `docs/PROGRESS.md` (the requirements checklist copied from
  `CLAUDE.md` section 5, to tick off as the project advances).
- Created a Python 3.12 virtual environment (`.venv`) at the repo root with
  `py -3.12 -m venv .venv`, activated it, and installed `requirements.txt`.

### Why this matters for the four promises
- **Reproductible**: if the Python version, the git remote, or the ignored files are
  wrong from day one, nobody (including future me) can redo this setup the same way.
  Fixing `.gitignore` now avoids accidentally publishing the teacher's `course/`
  material later.

### Answers to the Step 0 questions
- **Q1 (why install Python 3.12 alongside 3.14 instead of replacing it?):**
  [TODO: write your answer here]
- **Q2 (why didn't `docker --version` prove Docker was ready?):**
  [TODO: write your answer here]
