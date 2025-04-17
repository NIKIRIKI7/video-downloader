from view.gui import create_gui
from utils.utils import ensure_dir
import constants
import os

if __name__ == '__main__':
    # Optional: Ensure the default directory exists at startup
    # Can also be handled by the GUI/Commands when first needed
    try:
        ensure_dir(constants.VIDEO_DIR_DEFAULT)
    except Exception as e:
         print(f"Warning: Could not create default output directory "
               f"'{constants.VIDEO_DIR_DEFAULT}': {e}")
         print("Please ensure you have write permissions or select a different directory.")

    # Start the GUI application
    create_gui()