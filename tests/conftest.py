import pytest

from phocus.utils import bootstrap_project


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    bootstrap_project()
