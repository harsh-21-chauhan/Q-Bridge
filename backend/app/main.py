"""Start with: python -m uvicorn backend.app.main:app --reload

The backend coordinates validated Python science, local JSON files and existing
benchmark data. The assistant defaults to mock mode; live requests require explicit configuration.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import Settings
from .routes import benchmarks, experiments, assistant
from .services.assistant_service import AssistantService
from .services.experiment_service import ExperimentService
from .services.experiment_store import ExperimentStore, StoreError
from .services.report_service import ReportService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create independent services so tests never write into real experiment history."""
    settings = settings or Settings.from_environment()
    app = FastAPI(
        title="Q-Bridge API", version="0.1.0",
        description="Simulated Bayesian calibration and placement. No real hardware. Research assistant defaults to mock mode.",
    )
    app.state.experiment_service = ExperimentService(ExperimentStore(settings.experiment_dir))
    app.state.report_service = ReportService(settings.research_dir)
    app.state.assistant_service = AssistantService(app.state.experiment_service, settings.experiment_dir.parent / "assistant")

    @app.exception_handler(StoreError)
    async def store_error(request: Request, error: StoreError):
        return JSONResponse(status_code=error.status_code, content={"detail": str(error)})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        # Report which field is wrong without echoing arbitrary request values.
        # This also safely handles invalid NaN/Infinity values in malformed JSON.
        details = [{"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
                   for item in error.errors()]
        return JSONResponse(status_code=422, content={"detail": details})

    @app.get("/api/health", tags=["Health"])
    def health():
        # Liveness only: benchmark/storage failures are reported by their endpoints.
        return {"status": "ok", "mode": "simulation", "meta_integration": "mock_default"}

    app.include_router(experiments.router)
    app.include_router(benchmarks.router)
    app.include_router(assistant.router)
    return app


app = create_app()
