import os
import shutil
from typing import Optional
# Import constants only if needed for default paths, but get_tool_path gets it passed now
# import constants

def ensure_dir(path: str) -> None:
    """
    Creates a directory at the specified path if it doesn't exist.
    Raises OSError if creation fails.
    """
    if not os.path.isdir(path):
        try:
            os.makedirs(path, exist_ok=True) # exist_ok=True avoids error if dir exists
            # Use print for utils as logger might not be available here
            print(f"[INFO] Created directory: {path}")
        except OSError as e:
            print(f"[ERROR] Failed to create directory {path}: {e}")
            raise # Re-raise the exception as directory creation is often crucial

def find_executable(name: str, configured_path: Optional[str]) -> Optional[str]:
    """
    Finds the executable path for a given tool.
    Checks the configured path first, then searches the system PATH.

    Args:
        name: The name of the executable (e.g., 'ffmpeg', 'yt-dlp').
        configured_path: The path specified in constants.py (or None/empty).

    Returns:
        The full path to the executable if found and executable, or None otherwise.
    """
    # 1. Check configured path (if provided and valid)
    if configured_path and os.path.isfile(configured_path):
        # Check if it's executable
        if os.access(configured_path, os.X_OK):
             # print(f"[DEBUG] Found '{name}' via configured path: {configured_path}")
             return configured_path
        else:
            print(f"[WARN] Configured path for '{name}' exists but is not executable: {configured_path}")
            # Continue to check PATH

    # 2. Check system PATH using shutil.which (handles .exe on Windows etc.)
    found_path = shutil.which(name)
    if found_path:
        # shutil.which already verifies it's executable to some extent
        # print(f"[DEBUG] Found '{name}' in system PATH: {found_path}")
        return found_path

    # 3. Not found
    # Warning message is printed by the caller (_check_tool_availability)
    # print(f"[WARN] Executable '{name}' not found in configured path ('{configured_path}') or system PATH.")
    return None

def get_tool_path(tool_name: str) -> str:
    """
    Gets the path for a required tool (e.g., 'ffmpeg', 'yt-dlp'),
    checking constants for a configured path first, then the system PATH.

    Args:
        tool_name: The name of the tool.

    Returns:
        The full path to the executable.

    Raises:
        FileNotFoundError: If the tool cannot be found.
    """
    # Dynamically get the constant variable name (e.g., FFMPEG_PATH)
    # Need to import constants here
    import constants
    path_const_name = f"{tool_name.upper()}_PATH"
    configured_path = getattr(constants, path_const_name, None)

    path = find_executable(tool_name, configured_path)
    if not path:
        error_message = (
            f"Required tool '{tool_name}' not found.\n"
            f"Please ensure it is installed and added to your system's PATH environment variable.\n"
            f"Alternatively, you can specify the full path to the executable "
            f"in the 'constants.py' file using the variable '{path_const_name}'."
        )
        raise FileNotFoundError(error_message)
    return path