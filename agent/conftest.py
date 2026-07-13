"""Make `ringback_agent` and `evals` importable when running `pytest` / `python -m evals.run`
from the agent/ directory without a prior `pip install -e`.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
