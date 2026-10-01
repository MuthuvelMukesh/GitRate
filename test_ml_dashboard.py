"""Manual smoke-test app for the dashboard/ML routers.

Not a pytest module (kept for manual ``python test_ml_dashboard.py`` runs).
Prefer ``uvicorn gitrate.main:app`` for the full application surface.
"""

from fastapi import FastAPI

from gitrate.api.components import router as components_router
from gitrate.api.ml_dashboard import router as ml_dashboard_router

app = FastAPI(title="GitRate ML Dashboard Test")

# Register routers
app.include_router(components_router)
app.include_router(ml_dashboard_router, prefix="/ml-dashboard")


@app.get("/")
def root():
    return {"message": "GitRate dashboard smoke test", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

