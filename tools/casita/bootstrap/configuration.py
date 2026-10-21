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
    request_timeout_seconds: float = 10.0
    home_assistant_url: str = ""
    home_assistant_token: str = ""
    home_assistant_entity_ids: tuple[str, ...] = ()

    @property
    def exists(self) -> bool:
        """Return whether configuration came from a file or environment."""

        return bool(self.grocy_url and self.grocy_api_key)

    @property
    def home_assistant_configured(self) -> bool:
        """Return whether the optional Home Assistant integration is enabled."""

        return bool(self.home_assistant_url and self.home_assistant_token)


def _home_assistant_entity_ids(value: str) -> tuple[str, ...]:
    """Parse a stable, deduplicated Home Assistant entity allowlist."""

    entity_ids = tuple(item.strip() for item in value.split(",") if item.strip())
    unique = tuple(dict.fromkeys(entity_ids))

    for entity_id in unique:
        parts = entity_id.split(".")
        if (
            len(parts) != 2
            or any(
                not part
                or not all(
                    character.islower()
                    or character.isdigit()
                    or character == "_"
                    for character in part
                )
                for part in parts
            )
        ):
            raise RuntimeError(
                "HOME_ASSISTANT_ENTITY_IDS must contain comma-separated entity IDs."
            )

    return unique


def _request_timeout_seconds(value: str) -> float:
    """Validate a finite, bounded integration request timeout."""

    try:
        timeout = float(value)
    except ValueError as error:
        raise RuntimeError(
            "CASITA_REQUEST_TIMEOUT_SECONDS must be a number."
        ) from error
    if not 0.1 <= timeout <= 60:
        raise RuntimeError(
            "CASITA_REQUEST_TIMEOUT_SECONDS must be between 0.1 and 60."
        )
    return timeout


def load_configuration(
    source: Path | None = None,
    *,
    strict: bool = True,
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
    home_assistant_url = os.getenv("HOME_ASSISTANT_URL", "").strip()
    home_assistant_token = os.getenv("HOME_ASSISTANT_TOKEN", "").strip()
    if bool(home_assistant_url) != bool(home_assistant_token):
        raise RuntimeError(
            "HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN must be configured together."
        )
    if home_assistant_url and not home_assistant_url.startswith(
        ("http://", "https://")
    ):
        raise RuntimeError("HOME_ASSISTANT_URL must use http:// or https://.")
    missing = [
        name
        for name, value in (
            ("GROCY_URL", grocy_url),
            ("GROCY_API_KEY", grocy_api_key),
        )
        if not value
    ]

    if missing and strict:
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
        request_timeout_seconds=_request_timeout_seconds(
            os.getenv("CASITA_REQUEST_TIMEOUT_SECONDS", "10")
        ),
        home_assistant_url=home_assistant_url,
        home_assistant_token=home_assistant_token,
        home_assistant_entity_ids=_home_assistant_entity_ids(
            os.getenv("HOME_ASSISTANT_ENTITY_IDS", "")
        ),
    )
