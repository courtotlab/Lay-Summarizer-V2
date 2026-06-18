"""
Run this file from the project root:

    python run_pipeline.py

This is intentionally small. The real workflow is in:
    src/lay_summary/pipeline.py
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_FOLDER = PROJECT_ROOT / "src"

if str(SRC_FOLDER) not in sys.path:
    sys.path.insert(0, str(SRC_FOLDER))

from lay_summary.pipeline import run_pipeline

if __name__ == "__main__":
    run_pipeline()
