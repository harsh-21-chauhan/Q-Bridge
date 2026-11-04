"""Connect HTTP requests to the existing science without duplicating its math."""
from threading import Lock

from qbridge.production import run_experiment

from ..schemas import ExperimentEvidence, ExperimentRequest
from .experiment_store import ExperimentStore, StoreError


class ExperimentService:
    def __init__(self, store: ExperimentStore):
        self.store = store
        # One calculation at a time is enough for a local demo. Other requests
        # get an explicit busy response instead of an unbounded work queue.
        self.calculation_lock = Lock()

    def create(self, request: ExperimentRequest):
        if not self.calculation_lock.acquire(blocking=False):
            raise StoreError("A calibration is already running. Try again when it finishes.")
        try:
            record = run_experiment(request.to_scientific_config())
            return self.store.save(record)
        finally:
            self.calculation_lock.release()

    def evidence(self, experiment_id: str) -> ExperimentEvidence:
        record = self.store.get(experiment_id)
        # Explicit allowlist: never pass evaluation or simulator configuration
        # to a later explanation tool as if it were calibration evidence.
        return ExperimentEvidence(
            experiment_id=record.experiment_id, mode=record.mode, result=record.result
        )
