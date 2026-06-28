# ---- Stage 1: build the React/Vite frontend ----
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime serving API + built frontend ----
FROM python:3.11-slim
WORKDIR /app

# Install Python deps via the project metadata (editable keeps app/ importable in
# place, so main.py resolves frontend/dist relative to the source tree).
COPY pyproject.toml ./
COPY app/ ./app/
RUN pip install --no-cache-dir -e .

# Bring in the compiled frontend from stage 1.
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Render injects $PORT; default to 10000 for local runs.
ENV PORT=10000
EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
