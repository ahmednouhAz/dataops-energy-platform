# Running this project in GitHub Codespaces

For a machine where Docker isn't installed (e.g. a university laptop) --
everything runs in the browser instead, on GitHub's own servers.

## 1. Open a Codespace

1. Go to the repo on GitHub: `https://github.com/ahmednouhAz/dataops-energy-platform`
2. Click the green **Code** button -> **Codespaces** tab -> **Create codespace on main**.
3. If asked to pick a machine type, choose the largest one available
   (4-core / 8GB RAM if offered) -- this stack runs 7 services at once
   (MinIO, Prefect, Prometheus, Grafana, Metabase, the worker), which is
   more than the default 2-core machine comfortably handles.
4. Wait for the container to build. This runs `.devcontainer/devcontainer.json`'s
   `postCreateCommand` automatically: installs Python packages and the
   pre-commit hooks. A few minutes on first create.

## 2. Set up environment variables

In the Codespaces terminal:
```
cp .env.example .env
```
Open `.env` in the file explorer (left sidebar) and fill in any
non-empty values for `MINIO_ROOT_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`,
`METABASE_ADMIN_PASSWORD` (8+ characters for MinIO's password).
Leave `DISCORD_WEBHOOK_URL` empty unless you want alerts delivered
somewhere real.

## 3. Start the platform

```
docker compose up -d
docker compose ps
```
Same as running locally -- all 7 services should show `Up`
(`minio`/`metabase` `(healthy)`; `minio-setup`/`metabase-setup`
`Exited (0)`, which is expected for a one-shot job).

## 4. Open the UIs

Codespaces doesn't use `localhost` links directly in a browser outside
its own tab -- instead:

1. Click the **Ports** tab at the bottom of the VS Code window (next to
   Terminal).
2. You'll see rows for each port the containers expose: `3000`
   (Grafana), `3001` (Metabase), `4200` (Prefect), `9090` (Prometheus),
   `9091` (Pushgateway), `9000`/`9001` (MinIO).
3. Click the globe icon on a row to open that service in a new browser
   tab, forwarded through Codespaces.
4. If a port doesn't appear automatically, right-click in the Ports
   tab -> **Add Port** -> type the port number.

## Si ça ne marche pas

| Symptom | Likely cause / fix |
|---|---|
| `postCreateCommand` fails during setup | Check the terminal output for the exact missing package; `pip install -r requirements.txt` manually as a fallback |
| `docker compose up` is very slow or a service keeps restarting | The machine type is too small -- delete the Codespace and recreate with a bigger machine (step 1.3) |
| Port doesn't show in the Ports tab | Add it manually (step 4.4) -- Codespaces only auto-detects ports a process has already bound to |
| A forwarded URL shows "This site can't be reached" | The container behind that port isn't `Up` yet -- re-check `docker compose ps` |

## Stopping / resuming

Codespaces auto-stops after a period of inactivity (billing reasons) --
your files and uncommitted work are preserved, but running containers
are not: `docker compose up -d` again after resuming. Delete the
Codespace entirely from `github.com/codespaces` once you're done with
it for the day, to avoid using up free quota hours doing nothing.
