"""Shared pytest fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Make backend/ importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def tmp_output_dir(tmp_path_factory):
    """Ephemeral directory for generator output across a test session."""
    return tmp_path_factory.mktemp("dlg_gen_output")
