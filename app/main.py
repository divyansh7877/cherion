"""FastAPI app exposing the query-to-visualization service."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

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

_FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


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


@app.get("/")
async def demo() -> FileResponse:
    if not _FRONTEND.exists():  # pragma: no cover
        raise HTTPException(status_code=404, detail="Frontend demo not built.")
    return FileResponse(_FRONTEND)
