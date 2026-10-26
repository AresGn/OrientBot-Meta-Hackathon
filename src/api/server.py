"""FastAPI stub for the OrientBot demo (agent loop not wired yet)."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="OrientBot Demo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/run")
async def run_agent() -> JSONResponse:
    """Run the agent loop (not implemented)."""
    return JSONResponse(
        status_code=501,
        content={"status": "not implemented", "steps": []},
    )


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
