"""FastAPI app exposing the query-to-visualization service."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.clinicaltrials.client import CTGovError
from app.pipeline import run_pipeline
from app.schemas import VisualizeRequest, VisualizeResponse

app = FastAPI(
    title="Cherion",
    description="Natural-language clinical-trial questions -> structured visualization specs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The frontend is a Vite + React build; `npm run build` emits frontend/dist.
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_INDEX = _DIST / "index.html"

if (_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/visualize", response_model=VisualizeResponse)
async def visualize(request: VisualizeRequest) -> VisualizeResponse:
    try:
        return await run_pipeline(request)
    except CTGovError as exc:
        raise HTTPException(status_code=502, detail=f"ClinicalTrials.gov error: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/", response_model=None)
async def demo() -> FileResponse | HTMLResponse:
    if not _INDEX.exists():
        return HTMLResponse(
            "<h1>Cherion</h1><p>Frontend not built. Run "
            "<code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>, "
            "or use the Vite dev server with <code>npm run dev</code>.</p>",
            status_code=200,
        )
    return FileResponse(_INDEX)
