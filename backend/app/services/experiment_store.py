"""One validated JSON file per experiment; no database is needed for the MVP."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from pydantic import ValidationError

from ..schemas import ExperimentRecord

ID_PATTERN = re.compile(r"qb_[0-9a-f]{32}\Z")


class StoreError(Exception):
    """Errors have safe messages suitable for the API; never include disk paths."""
    status_code = 503


class InvalidExperimentId(StoreError):
    status_code = 422


class ExperimentNotFound(StoreError):
    status_code = 404


class InvalidStoredRecord(StoreError):
    status_code = 500


class RecordConflict(StoreError):
    status_code = 409


def validate_record(data: dict) -> ExperimentRecord:
    try:
        record = ExperimentRecord.model_validate(data)
        # Same identity calculation as production: detect mismatched config/ID.
        identity = json.dumps({"configuration": record.configuration, **record.metadata},
                              sort_keys=True, separators=(",", ":"), allow_nan=False)
        expected_id = "qb_" + hashlib.sha256(identity.encode()).hexdigest()[:32]
        if record.experiment_id != expected_id:
            raise ValueError("identifier mismatch")
        return record
    except (ValidationError, TypeError, ValueError) as exc:
        raise InvalidStoredRecord("The experiment record is malformed or inconsistent.") from exc


class ExperimentStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def _path(self, experiment_id: str) -> Path:
        # An ID is a fixed-format identifier, never a user-provided filename.
        if not ID_PATTERN.fullmatch(experiment_id):
            raise InvalidExperimentId("Invalid experiment ID format.")
        return self.directory / f"{experiment_id}.json"

    def get(self, experiment_id: str) -> ExperimentRecord:
        path = self._path(experiment_id)
        try:
            if path.is_symlink():
                raise InvalidStoredRecord("Experiment records cannot be symbolic links.")
            data = json.loads(path.read_text(encoding="utf-8"))
            record = validate_record(data)
            if record.experiment_id != experiment_id:
                raise InvalidStoredRecord("The saved experiment does not match its filename.")
            return record
        except FileNotFoundError as exc:
            raise ExperimentNotFound("Experiment not found.") from exc
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise InvalidStoredRecord("The saved experiment is not valid JSON.") from exc
        except OSError as exc:
            raise StoreError("Experiment storage is unavailable.") from exc

    def save(self, data: dict) -> tuple[ExperimentRecord, bool]:
        """Return (record, created). Repeated identical runs reuse the same file."""
        record = validate_record(data)
        path = self._path(record.experiment_id)
        temporary_path = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            # Write to a temporary file first. Readers never see half-written JSON.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".tmp",
                                             dir=self.directory, delete=False) as handle:
                temporary_path = Path(handle.name)
                handle.write(record.model_dump_json(indent=2))
                handle.flush()
                os.fsync(handle.fileno())
            try:
                # Linking publishes the complete file atomically and refuses to
                # overwrite an existing ID, including across server processes.
                os.link(temporary_path, path)
                return record, True
            except FileExistsError:
                existing = self.get(record.experiment_id)
                if existing != record:
                    raise RecordConflict("A different record already exists for this experiment ID.")
                return existing, False
        except OSError as exc:
            raise StoreError("The experiment could not be saved.") from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def list_records(self, limit: int, offset: int) -> tuple[list[ExperimentRecord], int]:
        """Stable ID ordering and bounded pages; no timestamps invented as science."""
        try:
            paths = sorted(p for p in self.directory.glob("qb_*.json")
                           if ID_PATTERN.fullmatch(p.stem))
            return [self.get(path.stem) for path in paths[offset:offset + limit]], len(paths)
        except OSError as exc:
            raise StoreError("Experiment storage is unavailable.") from exc
