"""API validators are methods that take in the API parameters and either return a list of error messages or
nothing if the parameters are valid"""
from phocus.utils.constants import START_LOCATION, END_LOCATION
from phocus.utils.mixins import Base


class APIValidator(Base):
    """Allows validators to be registered and calls all validations"""
    def __init__(self):
        self.validators = []

    def validate(self, api_params):
        """Calls all registered validators and raises an error if there were any downstream errors"""
        errors = []
        for validator in self.validators:
            result = validator(api_params)
            errors.extend(result if result else [])
        if errors:
            raise RuntimeError('APIValidator failed with following errors:\n%s' % '\n'.join(errors))


def start_location_validator(api_params):
    top_level_start_location = api_params.get(START_LOCATION)
    has_work_period_start_location = any(START_LOCATION in p for p in api_params['workPeriods'])
    if top_level_start_location and has_work_period_start_location:
        return ['Should not have both a top level and work period level startLocation']

    # Make sure all work period locations are present
    if has_work_period_start_location:
        if not all(START_LOCATION in p and END_LOCATION in p for p in api_params['workPeriods']):
            return ['Not all start and end work period locations were present']
