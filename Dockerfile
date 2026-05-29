# syntax=docker/dockerfile:1
# One image: the FastAPI gateway serves /api and the built web SPA at /.

# --- stage 1: build the web SPA ---
FROM node:22-slim AS web
WORKDIR /web
RUN corepack enable
ENV CI=1
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build   # tsc --noEmit && vite build -> /web/dist

# --- stage 2: the gateway image ---
FROM python:3.13-slim AS app
WORKDIR /app
# git: the Git-backed doc/risk stores shell out to it (INV-ST-1)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY api/scree ./scree
COPY --from=web /web/dist ./web
ENV SCREE_WEB_DIR=/app/web
EXPOSE 8000
CMD ["uvicorn", "scree.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
