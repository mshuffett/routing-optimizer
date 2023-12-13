import logging
from contextlib import contextmanager
from timeit import default_timer as timer

from datetime import datetime
from pathlib import Path

from joblib import Memory

import phocus.utils.files
from phocus.utils.constants import CACHE_DIR

logger = logging.getLogger(__name__)


def current_isotime_for_filename():
    return datetime.utcnow().replace(microsecond=0).isoformat().replace(':', '.')


def bootstrap_project(log_title='phocus'):
    """Setup logging and other required setup for running project"""
    output_path = phocus.utils.files.make_output_dir() / 'logs'
    output_path.mkdir(parents=True, exist_ok=True)
    log_filename = f'{log_title}-{current_isotime_for_filename()}.log'
    _configure_logging(output_path / log_filename)


def _configure_logging(log_path: Path):
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ],
        level=logging.INFO)


class HashableDict(dict):
    def __key(self):
        return tuple((k, self[k]) for k in sorted(self))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()


@contextmanager
def log_time_context_manager(name):
    """Context manager that logs the time that it is open"""
    start = timer()
    yield
    end = timer()
    logger.info('%s completed after %.0f seconds', name, end - start)


"""job.Memory Singleton for use for memoization"""
memory = Memory(cachedir=str(CACHE_DIR), verbose=0)
