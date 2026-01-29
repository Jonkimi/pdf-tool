"""LibreOffice detection and installation helper."""

import logging
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any, List


LIBREOFFICE_DOWNLOAD_URL = "https://www.libreoffice.org/download/download/"


class LibreOfficeInstaller:
    """Platform-aware LibreOffice detection and installation helper."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def detect_libreoffice(self) -> Optional[str]:
        """Enhanced detection: shutil.which() + common install locations.

        Returns:
            Path to soffice executable or None.
        """
        system = platform.system()

        # First try PATH via shutil.which
        for name in ("soffice", "libreoffice"):
            path = shutil.which(name)
            if path:
                return path

        # Fall back to common install locations
        candidates = self._get_common_paths(system)
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

        return None

    def _get_common_paths(self, system: str) -> List[Path]:
        """Get common installation paths for the platform."""
        if system == "Darwin":
            return [
                Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            ]
        elif system == "Windows":
            paths = []
            for program_dir in (
                Path("C:/Program Files/LibreOffice/program"),
                Path("C:/Program Files (x86)/LibreOffice/program"),
            ):
                if program_dir.exists():
                    paths.append(program_dir / "soffice.exe")
            return paths
        else:
            # Linux
            return [
                Path("/usr/bin/soffice"),
                Path("/usr/bin/libreoffice"),
                Path("/usr/local/bin/soffice"),
                Path("/snap/bin/libreoffice"),
                Path("/opt/libreoffice/program/soffice"),
            ]

    def get_platform_info(self) -> Dict[str, Any]:
        """Get platform-specific installation information.

        Returns:
            Dict with platform info and install instructions.
        """
        system = platform.system()

        if system == "Darwin":
            return {
                "platform": "macos",
                "install_commands": {
                    "homebrew": "brew install --cask libreoffice",
                },
                "download_url": LIBREOFFICE_DOWNLOAD_URL,
            }
        elif system == "Windows":
            return {
                "platform": "windows",
                "download_url": LIBREOFFICE_DOWNLOAD_URL,
            }
        else:
            return {
                "platform": "linux",
                "install_commands": {
                    "apt": "sudo apt install libreoffice",
                    "dnf": "sudo dnf install libreoffice",
                    "pacman": "sudo pacman -S libreoffice-fresh",
                },
                "download_url": LIBREOFFICE_DOWNLOAD_URL,
            }

    def open_download_page(self) -> None:
        """Open the LibreOffice download page in the default browser."""
        webbrowser.open(LIBREOFFICE_DOWNLOAD_URL)

    def verify_path(self, path: str) -> Optional[str]:
        """Check if a path points to a valid LibreOffice executable.

        Args:
            path: Path to the executable.

        Returns:
            Version string if valid, None otherwise.
        """
        if not path or not Path(path).is_file():
            return None

        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Output like: "LibreOffice 7.5.3.2 ..."
                version = result.stdout.strip()
                if "LibreOffice" in version:
                    return version
        except Exception as e:
            self.logger.debug(f"Failed to verify LibreOffice path {path}: {e}")

        return None
