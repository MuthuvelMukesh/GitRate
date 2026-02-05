"""Minimal FastAPI app to test ML Dashboard UI"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pages.ml_dashboard import router as ml_dashboard_router
from pages.components import router as components_router

app = FastAPI(title="GitRate ML Dashboard Test")

# Register routers
app.include_router(components_router)
app.include_router(ml_dashboard_router, prefix="/ml-dashboard")

@app.get("/")
def root():
    return {"message": "GitRate ML Dashboard - Phase 8 Complete", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "3.0.0", "phase": 8}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
