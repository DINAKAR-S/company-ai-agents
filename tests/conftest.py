from pathlib import Path

import pytest

from orgchart import load_catalog

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def catalog():
    return load_catalog(ROOT)
