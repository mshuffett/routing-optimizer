from unittest.mock import MagicMock

import pendulum
import pytest

from phocus.cp.solution_validator import SolutionValidator
from phocus.model.appointment import Appointment
from phocus.model.solution import Solution
from phocus.utils.constants import TEST_DATA_PATH


@pytest.fixture
def validator():
    return SolutionValidator(MagicMock(), MagicMock(), MagicMock(), MagicMock())


@pytest.fixture
def solution():
    return Solution.load(TEST_DATA_PATH / 'solution_validator' / 'solution.json')


class TestValidateAppointments:
    def test_validate_calls_validate_appointments(self, validator):
        mock_call = MagicMock()
        validator._validate_appointments = mock_call
        validator.validate(_raise=False)
        mock_call.assert_called_once()

    def test_validate_appointments_gives_empty_list_with_no_appointments(self):
        validator = SolutionValidator(
            appointments=[],
            locations=MagicMock(),
            repeat_locations=MagicMock(),
            solution=MagicMock(),
        )
        assert [] == validator._validate_appointments()

    def test_validate_appointments_single_missed_appointment(self, solution):
        appointments = [
            Appointment(
                solution.route[1],
                pendulum.parse('2018-06-18T14:17:24+00:00'),
                pendulum.parse('2018-06-18T14:47:24+00:00')
            )
        ]
        validator = SolutionValidator(
            appointments=appointments,
            locations=MagicMock(),
            repeat_locations=MagicMock(),
            solution=solution,
        )
        error_messages = validator._validate_appointments()
        assert 1 == len(error_messages)
        assert 'juan goez' in error_messages[0]

    def test_validate_appointments_multiple_missed_appointment(self, solution):
        appointments = [
            Appointment(
                solution.route[1],
                pendulum.parse('2018-06-18T14:17:24+00:00'),
                pendulum.parse('2018-06-18T14:47:24+00:00')
            ),
            Appointment(
                solution.route[2],
                pendulum.parse('2018-06-18T14:17:23+00:00'),
                pendulum.parse('2018-06-18T14:47:25+00:00')
            )
        ]
        validator = SolutionValidator(
            appointments=appointments,
            locations=MagicMock(),
            repeat_locations=MagicMock(),
            solution=solution,
        )
        error_messages = validator._validate_appointments()
        assert 2 == len(error_messages)

        error_message_text = ';'.join(error_messages)
        assert 'juan goez' in error_message_text
        assert 'corey' in error_message_text

    def test_validate_appointments_multiple_missed_appointment_multiple_fulfilled_appointments(self, solution):
        appointments = [
            Appointment(
                solution.route[1],
                pendulum.parse('2018-06-18T13:59:01+00:00'),
                pendulum.parse('2018-06-18T14:09:01+00:00')
            ),
            Appointment(
                solution.route[2],
                pendulum.parse('2018-06-18T14:17:24+00:00'),
                pendulum.parse('2018-06-18T14:47:24+00:00')
            ),
            Appointment(
                solution.route[3],
                pendulum.parse('2018-06-18T13:59:01+00:00'),
                pendulum.parse('2018-06-18T14:09:01+00:00')
            ),
            Appointment(
                solution.route[4],
                pendulum.parse('2018-06-18T14:17:24+00:00'),
                pendulum.parse('2018-06-18T14:47:24+00:00')
            ),
        ]
        validator = SolutionValidator(
            appointments=appointments,
            locations=MagicMock(),
            repeat_locations=MagicMock(),
            solution=solution,
        )
        assert 2 == len(validator._validate_appointments())

    def test_single_fulfilled_appointment(self, solution):
        appointments = [
            Appointment(
                solution.route[1],
                pendulum.parse('2018-06-18T13:59:01+00:00'),
                pendulum.parse('2018-06-18T14:09:01+00:00')
            ),
        ]
        validator = SolutionValidator(
            appointments=appointments,
            locations=MagicMock(),
            repeat_locations=MagicMock(),
            solution=solution,
        )
        assert [] == validator._validate_appointments()

    def test_multiple_fulfilled_appointment(self, solution):
        appointments = [
            Appointment(
                solution.route[1],
                pendulum.parse('2018-06-18T13:59:01+00:00'),
                pendulum.parse('2018-06-18T14:09:01+00:00')
            ),
            Appointment(
                solution.route[2],
                pendulum.parse('2018-06-18T14:17:24+00:00'),
                pendulum.parse('2018-06-18T14:47:24+00:00')
            ),
        ]
        validator = SolutionValidator(
            appointments=appointments,
            locations=MagicMock(),
            repeat_locations=MagicMock(),
            solution=solution,
        )
        assert [] == validator._validate_appointments()
