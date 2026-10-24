"""Global constants."""

from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data"
"""Repo-root data directory for checked-in assets and generated images."""

ASSETS = DATA / "assets"
"""Checked-in fonts and sample images."""
