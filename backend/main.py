"""
TrustRail FastAPI Server Entrypoint
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api.routes import router as api_router

app = FastAPI(
    title="TrustRail — Adaptive Permission Layer for AI Shopping Agents",
    description=(
        "Razorpay AI Buildathon 2026 (Track 01: AI Growth & Agentic Commerce). "
        "Deterministic, rule-based adaptive trust score engine and mandate gating "
        "sitting between AI buyer agents and payment execution."
    ),
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")
app.include_router(api_router)  # Direct access without /api prefix as well for simplicity


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "TrustRail Mandate Gate & Scoring Engine",
        "version": "1.0.0",
        "evaluation_track": "Track 01: AI Growth & Agentic Commerce",
    }


# Mount Dashboard static files
dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
if os.path.exists(dashboard_dir):
    app.mount("/static", StaticFiles(directory=dashboard_dir), name="static")

    @app.get("/", include_in_schema=False)
    def serve_dashboard():
        index_file = os.path.join(dashboard_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Dashboard UI under development. Access API docs at /docs"}


def main():
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
