"""Experiment endpoints used by the dashboard and interactive API docs."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from ..schemas import (
    ExperimentEvidence, ExperimentId, ExperimentList, ExperimentRecord,
    ExperimentRequest, ExperimentSummary,
)
from ..services.experiment_service import ExperimentService

router = APIRouter(prefix="/api/experiments", tags=["Experiments"])


def get_service(request: Request) -> ExperimentService:
    return request.app.state.experiment_service


Service = Annotated[ExperimentService, Depends(get_service)]


@router.post("", response_model=ExperimentRecord, status_code=201,
             responses={200: {"description": "Identical saved experiment reused"},
                        503: {"description": "Calculation busy or storage unavailable"}})
def create_experiment(body: ExperimentRequest, response: Response, service: Service):
    """Run the validated adaptive algorithm and save the complete simulated record."""
    # A normal def runs in FastAPI's worker threadpool. CPU work is not put in
    # an async handler where it would block the server's event loop.
    record, created = service.create(body)
    response.status_code = 201 if created else 200
    response.headers["Location"] = f"/api/experiments/{record.experiment_id}"
    return record


@router.get("", response_model=ExperimentList)
def list_experiments(service: Service, limit: int = Query(20, ge=1, le=100),
                     offset: int = Query(0, ge=0)):
    """List saved runs in stable ID order; responses contain no hidden truth."""
    records, total = service.store.list_records(limit, offset)
    return ExperimentList(
        experiments=[ExperimentSummary(
            experiment_id=r.experiment_id, configuration=r.configuration,
            status=r.result.decision.status, switched=r.result.decision.switched,
        ) for r in records],
        total=total, next_offset=offset + limit if offset + limit < total else None,
    )


@router.get("/{experiment_id}", response_model=ExperimentRecord)
def get_experiment(experiment_id: ExperimentId, service: Service):
    """Retrieve a saved record; evaluation stays in its labeled separate section."""
    return service.store.get(experiment_id)


@router.get("/{experiment_id}/evidence", response_model=ExperimentEvidence)
def get_evidence(experiment_id: ExperimentId, service: Service):
    """Return observed calibration and decision evidence, excluding simulator truth."""
    return service.evidence(experiment_id)
