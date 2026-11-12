# The pipeline image: Python + every dependency the project's code needs
# (dlt, dbt, Pandera, pytest...). Published to GHCR on a tag in step 15;
# used locally today as docker-compose.yml's "worker" service.
FROM python:3.12.7-slim-bookworm

WORKDIR /app

# dbt shells out to git (e.g. to fetch packages) even though this project
# has none yet -- `dbt debug` reports it as a failed check without this,
# found by running `dbt debug` inside the built image.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first, in their own layer: changing application code
# shouldn't force a multi-minute pip re-install on every rebuild.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No long-running process exists yet (Prefect flows are step 12) -- stay
# alive so `docker compose exec worker <command>` can run pipeline code,
# dbt, or pytest inside the exact same environment CI and prod will use.
CMD ["sleep", "infinity"]
