"""Small, explicit server settings. No model credentials are used at this stage."""
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    experiment_dir: Path
    research_dir: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        # In an editable checkout, this file lives at backend/app/config.py.
        # A wheel installation can point to evidence using QBRIDGE_RESEARCH_DIR.
        root = Path(__file__).resolve().parents[2]
        return cls(
            experiment_dir=Path(os.environ.get(
                "QBRIDGE_EXPERIMENT_DIR", str(root / "results/experiments")
            )).expanduser().resolve(),
            research_dir=Path(os.environ.get(
                "QBRIDGE_RESEARCH_DIR", str(root / "research")
            )).expanduser().resolve(),
        )
