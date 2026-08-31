"""Shared pytest fixtures for sam-graph-agent tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure `src/` is importable so tests work without an editable install.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture
def neo4j_connection_params():
    return {
        "host": "localhost",
        "port": 7687,
        "user": "neo4j",
        "password": "password",
        "database": "neo4j",
    }


@pytest.fixture
def mock_driver():
    """A MagicMock standing in for a neo4j Driver."""
    driver = MagicMock(name="Neo4jDriver")
    driver.session.return_value = MagicMock(name="Neo4jSession")
    return driver


@pytest.fixture
def mock_session(mock_driver):
    """The session returned by `driver.session()`."""
    return mock_driver.session.return_value
