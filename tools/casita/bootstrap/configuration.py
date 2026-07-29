"""Deployment configuration loaded by the composition root."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class ApplicationConfiguration:
    """Hold validated process configuration without exposing environment APIs."""

    project_root: Path
    source: Path | None
    grocy_url: str
    grocy_api_key: str
    timezone: str
    household_id: str
    household_name: str

    @property
    def exists(self) -> bool:
        """Return whether configuration came from a file or environment."""

        return self.source is not None or bool(
            os.getenv("GROCY_URL") and os.getenv("GROCY_API_KEY")
        )


def load_configuration(
    source: Path | None = None,
) -> ApplicationConfiguration:
    """Load and validate Nuestra Casita deployment configuration."""

    candidates = (
        source,
        PROJECT_ROOT / ".env",
        Path("/opt/Nuestra-Casita/.env"),
    )
    config_source = next(
        (
            candidate
            for candidate in candidates
            if candidate is not None and candidate.is_file()
        ),
        None,
    )

    if config_source is not None:
        load_dotenv(config_source)

    grocy_url = os.getenv("GROCY_URL", "").strip()
    grocy_api_key = os.getenv("GROCY_API_KEY", "").strip()
    missing = [
        name
        for name, value in (
            ("GROCY_URL", grocy_url),
            ("GROCY_API_KEY", grocy_api_key),
        )
        if not value
    ]

    if missing:
        raise RuntimeError(
            f"Missing {', '.join(missing)} in Nuestra Casita configuration."
        )

    return ApplicationConfiguration(
        project_root=PROJECT_ROOT,
        source=config_source,
        grocy_url=grocy_url,
        grocy_api_key=grocy_api_key,
        timezone=os.getenv("CASITA_TIMEZONE", "UTC").strip() or "UTC",
        household_id=os.getenv(
            "CASITA_HOUSEHOLD_ID",
            "default",
        ).strip() or "default",
        household_name=os.getenv(
            "CASITA_HOUSEHOLD_NAME",
            "Nuestra Casita",
        ).strip() or "Nuestra Casita",
    )
