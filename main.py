from gui.main_window import create_gui
from utils.utils import ensure_dir
import constants
import os

if __name__ == '__main__':
    try:
        ensure_dir(constants.VIDEO_DIR_DEFAULT)
    except Exception as e:
         print(f"Warning: Could not create default output directory "
               f"'{constants.VIDEO_DIR_DEFAULT}': {e}")
         print("Please ensure you have write permissions or select a different directory.")

    create_gui() # Запуск остался прежним