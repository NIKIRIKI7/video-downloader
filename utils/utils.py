import os
import shutil
from typing import Optional
import constants

def ensure_dir(path: str) -> None:
    """
    Creates a directory at the specified path if it doesn't exist.

    Args:
        path: The directory path.
    """
    if not os.path.isdir(path):
        try:
            os.makedirs(path, exist_ok=True) # exist_ok=True handles race conditions
            print(f"[INFO] Created directory: {path}")
        except OSError as e:
            print(f"[ERROR] Failed to create directory {path}: {e}")
            raise # Re-raise the exception as directory creation is crucial

def find_executable(name: str, configured_path: Optional[str]) -> Optional[str]:
    """
    Finds the executable path for a given tool.
    Checks the configured path first, then searches the system PATH.

    Args:
        name: The name of the executable (e.g., 'ffmpeg', 'yt-dlp').
        configured_path: The path specified in constants.py (or None).

    Returns:
        The full path to the executable, or None if not found.
    """
    # 1. Check configured path
    if configured_path and os.path.exists(configured_path) and os.access(configured_path, os.X_OK):
         # print(f"[DEBUG] Found {name} via configured path: {configured_path}")
         return configured_path

    # 2. Check system PATH
    found_path = shutil.which(name)
    if found_path:
        # print(f"[DEBUG] Found {name} in PATH: {found_path}")
        return found_path

    # 3. Not found
    print(f"[WARN] Executable '{name}' not found in configured path or system PATH.")
    return None

def get_tool_path(tool_name: str) -> str:
    """
    Gets the path for a required tool (ffmpeg or yt-dlp), raising FileNotFoundError if not found.
    """
    path_const = getattr(constants, f"{tool_name.upper()}_PATH", None)
    path = find_executable(tool_name, path_const)
    if not path:
        raise FileNotFoundError(
            f"Required tool '{tool_name}' not found. "
            f"Please ensure it is installed and in your system PATH, or set the "
            f"{tool_name.upper()}_PATH in constants.py."
        )
    return path