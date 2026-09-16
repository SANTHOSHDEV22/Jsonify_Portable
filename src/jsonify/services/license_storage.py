"""Local Jsonify license storage."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


class LicenseStorage:
    """Stores the activated license locally."""

    def get_directory(self) -> Path:
        """Return Jsonify's application-data directory."""

        app_data = os.environ.get(
            "LOCALAPPDATA"
        )

        if app_data:
            return (
                Path(app_data)
                / "Jsonify"
            )

        return (
            Path.home()
            / ".jsonify"
        )

    def get_license_path(self) -> Path:
        """Return activated license path."""

        return (
            self.get_directory()
            / "license.jsonify-license"
        )

    def save_license(
        self,
        source: str | Path,
    ) -> Path:
        """Copy an activated license to local storage."""

        destination = (
            self.get_license_path()
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

        return destination

    def remove_license(self) -> None:
        """Remove locally activated license."""

        path = self.get_license_path()

        if path.exists():
            path.unlink()