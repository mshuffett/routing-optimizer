__version__ = '0.1.0'


import pendulum

# Monkeypatch pendulum.Period to make it have sane __hash__ and __eq__ methods
# PR pending to integrate this directly into pendulum https://github.com/sdispater/pendulum/pull/207
def _monkeypatch_pendulum_period():
    def __hash__(self):
        return hash((self.start, self.end, self._absolute))

    def __eq__(self, other):
        return (self.start, self.end, self._absolute) == (other.start, other.end, other._absolute)

    pendulum.Period.__hash__ = __hash__
    pendulum.Period.__eq__ == __eq__


_monkeypatch_pendulum_period()
