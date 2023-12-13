from functools import wraps
import inspect


def auto_assign_arguments(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        _assign_args(self, list(args), kwargs, function)
        function(self, *args, **kwargs)

    return wrapped


def _assign_args(instance, args, kwargs, function):
    def set_attribute(instance, parameter, default_arg):
        if not (parameter.startswith("_")):
            setattr(instance, parameter, default_arg)

    def assign_keyword_defaults(parameters, defaults):
        for parameter, default_arg in zip(reversed(parameters), reversed(defaults)):
            set_attribute(instance, parameter, default_arg)

    def assign_positional_args(parameters, args):
        for parameter, arg in zip(parameters, args.copy()):
            set_attribute(instance, parameter, arg)
            args.remove(arg)

    def assign_keyword_args(kwargs):
        for parameter, arg in kwargs.items():
            set_attribute(instance, parameter, arg)

    def assign_keyword_only_defaults(defaults):
        return assign_keyword_args(defaults)

    def assign_variable_args(parameter, args):
        set_attribute(instance, parameter, args)

    positional_params, variable_param, _, keyword_defaults, _, keyword_only_defaults, _ = inspect.getfullargspec(
        function)
    positional_params = positional_params[1:]  # remove 'self'

    if keyword_defaults:
        assign_keyword_defaults(parameters=positional_params, defaults=keyword_defaults)
    if keyword_only_defaults:
        assign_keyword_only_defaults(defaults=keyword_only_defaults)
    if args:
        assign_positional_args(parameters=positional_params, args=args)
    if kwargs:
        assign_keyword_args(kwargs=kwargs)
    if variable_param:
        assign_variable_args(parameter=variable_param, args=args)
