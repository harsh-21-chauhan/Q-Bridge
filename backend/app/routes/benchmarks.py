"""Serve precomputed research evidence without expensive benchmark reruns."""
from fastapi import APIRouter, Request

from ..schemas import BenchmarkSummary

router = APIRouter(prefix="/api/benchmarks", tags=["Benchmarks"])


@router.get("/summary", response_model=BenchmarkSummary)
def benchmark_summary(request: Request):
    """Return eight aggregate policies and 40 scenario breakdowns from frozen M2C data."""
    return request.app.state.report_service.summary()
