# -*- coding: utf-8 -*-

"""
Main entry point for the Visual Workflow Editor application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from work_flow_ui import MainWindow

def main():
    """
    Initializes and runs the PyQt6 application.
    """
    app = QApplication(sys.argv)

    # The logic for prompting the user to "New" or "Open" a workflow
    # will be handled within the MainWindow's initialization process.
    main_window = MainWindow()

    # The MainWindow will be responsible for showing itself after a
    # workflow context is established.

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
