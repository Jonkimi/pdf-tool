"""Ghostscript detection and installation helper."""

import logging
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any, List


GHOSTSCRIPT_DOWNLOAD_URL = "https://ghostscript.com/releases/gsdnld.html"


class GhostscriptInstaller:
    """Platform-aware Ghostscript detection and installation helper."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def detect_ghostscript(self) -> Optional[str]:
        """Enhanced detection: shutil.which() + common install locations.

        Returns:
            Path to gs executable or None.
        """
        system = platform.system()

        # First try PATH via shutil.which
        if system == "Windows":
            for name in ("gswin64c.exe", "gswin32c.exe", "gswin64.exe", "gswin32.exe"):
                path = shutil.which(name)
                if path:
                    return path
        else:
            path = shutil.which("gs")
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
                Path("/opt/homebrew/bin/gs"),
                Path("/usr/local/bin/gs"),
                Path("/opt/local/bin/gs"),
            ]
        elif system == "Windows":
            paths = []
            for program_dir in (
                Path("C:/Program Files/gs"),
                Path("C:/Program Files (x86)/gs"),
            ):
                if program_dir.exists():
                    for version_dir in sorted(program_dir.iterdir(), reverse=True):
                        bin_dir = version_dir / "bin"
                        if bin_dir.exists():
                            for name in ("gswin64c.exe", "gswin32c.exe", "gswin64.exe", "gswin32.exe"):
                                paths.append(bin_dir / name)
            return paths
        else:
            # Linux
            return [
                Path("/usr/bin/gs"),
                Path("/usr/local/bin/gs"),
                Path("/snap/bin/gs"),
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
                    "homebrew": "brew install ghostscript",
                    "macports": "sudo port install ghostscript",
                },
                "download_url": GHOSTSCRIPT_DOWNLOAD_URL,
            }
        elif system == "Windows":
            return {
                "platform": "windows",
                "download_url": GHOSTSCRIPT_DOWNLOAD_URL,
            }
        else:
            return {
                "platform": "linux",
                "download_url": GHOSTSCRIPT_DOWNLOAD_URL,
            }

    def open_download_page(self) -> None:
        """Open the Ghostscript download page in the default browser."""
        webbrowser.open(GHOSTSCRIPT_DOWNLOAD_URL)

    def verify_path(self, path: str) -> Optional[str]:
        """Check if a path points to a valid Ghostscript executable.

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
                version = result.stdout.strip()
                if version:
                    return version
        except Exception as e:
            self.logger.debug(f"Failed to verify GS path {path}: {e}")

        return None
