class SolutionError(RuntimeError):
    pass


class NoSolutionFoundError(SolutionError):
    pass


class InvalidSolutionError(SolutionError):
    pass
