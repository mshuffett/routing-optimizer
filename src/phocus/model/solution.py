import datetime
import json
import logging
from pathlib import Path
from typing import Sequence

from phocus.model.location import Location, locations_dicts
from phocus.utils.files import make_output_dir
from phocus.utils.mixins import Base


logger = logging.getLogger(__name__)


class Solution(Base):
    def __init__(self, model_name, run_datetime, route, metrics):
        self.model_name = model_name
        self.run_datetime = run_datetime
        self.route: Sequence[Location] = route
        self.metrics = metrics

    def save(self, filename, output_dir=make_output_dir() / 'solutions'):
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        solution_dict = {
            'model_name': self.model_name,
            'run_datetime': self.run_datetime.replace(microsecond=0).isoformat(),
            'route': locations_dicts(self.route),
            'metrics': self.metrics
        }
        with path.open(mode='w') as f:
            json.dump(solution_dict, f, indent=2)

    @staticmethod
    def load(path: Path):
        with path.open() as f:
            solution_json = json.load(f)

        return Solution(
            model_name=solution_json['model_name'],
            run_datetime=datetime.datetime.strptime(solution_json['run_datetime'], '%Y-%m-%dT%H:%M:%S'),
            route=[Location(**x) for x in solution_json['route']],
            metrics=solution_json['metrics']
        )


def solution_str_paths(output_dir=make_output_dir() / 'solutions'):
    return [str(x) for x in output_dir.iterdir()]


def load_all_solutions(output_dir=make_output_dir() / 'solutions'):
    solutions = []
    paths = sorted(output_dir.resolve().iterdir())
    for path in paths:
        logger.info('Loading solution %s', path)
        solutions.append(Solution.load(path))
    return solutions
