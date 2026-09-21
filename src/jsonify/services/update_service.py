"""Optional update checking against GitHub Releases.

Nothing is downloaded or installed automatically: a check only asks GitHub
for the latest release and reports whether it is newer than the running
version, along with the release page to visit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

DEFAULT_REPOSITORY = "santhoshkumard15092000/Jsonify"


class UpdateCheckError(RuntimeError):
    """Raised when the latest release can't be determined."""


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    """Result of an update check."""

    current_version: str
    latest_version: str
    is_newer: bool
    release_url: str
    notes: str


def parse_version(text: str) -> tuple[int, ...]:
    """Turn ``v1.2.3`` / ``1.2.3-beta`` into ``(1, 2, 3)`` for comparison."""

    numbers = re.findall(r"\d+", text.split("-")[0].split("+")[0])
    return tuple(int(n) for n in numbers) or (0,)


def is_newer(latest: str, current: str) -> bool:
    """Return whether ``latest`` is a higher version than ``current``."""

    a, b = parse_version(latest), parse_version(current)
    length = max(len(a), len(b))
    return a + (0,) * (length - len(a)) > b + (0,) * (length - len(b))


class UpdateService:
    """Checks GitHub Releases for a newer version."""

    def __init__(
        self,
        repository: str = DEFAULT_REPOSITORY,
        *,
        timeout_seconds: float = 8.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._repository = repository
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def check(self, current_version: str) -> UpdateInfo:
        """Ask GitHub for the latest release.

        Raises:
            UpdateCheckError: If the request fails or the response is unusable.
        """

        url = f"https://api.github.com/repos/{self._repository}/releases/latest"

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                transport=self._transport,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "Jsonify"},
            ) as client:
                response = client.get(url)
        except httpx.HTTPError as error:
            raise UpdateCheckError(f"Could not reach GitHub: {error}") from error

        if response.status_code == 404:
            raise UpdateCheckError("No releases have been published yet.")

        if response.status_code != 200:
            raise UpdateCheckError(f"GitHub returned HTTP {response.status_code}.")

        try:
            data = response.json()
            latest = str(data["tag_name"])
        except (ValueError, KeyError, TypeError) as error:
            raise UpdateCheckError("Unexpected response from GitHub.") from error

        return UpdateInfo(
            current_version=current_version,
            latest_version=latest.lstrip("vV"),
            is_newer=is_newer(latest, current_version),
            release_url=str(
                data.get("html_url", f"https://github.com/{self._repository}/releases")
            ),
            notes=str(data.get("body") or "")[:2000],
        )
