import inspect

import logging


class ReprMixin(object):
    """Mixin that provides a sane __repr__ from an object's vars"""
    def __repr__(self):
        attributes = []
        for key in vars(self):
            if not key.startswith('_') and not inspect.ismethod(getattr(self, key)):
                attributes.append('%s=%s' % (key, getattr(self, key)))
        return '%s(%s)' % (self.__class__.__name__, ', '.join(attributes))


class LoggingMixin(object):
    """Mixin that provides a logger property

    Note: does not call logs.setup_logging as that should generally only be called from __main__"""
    @property
    def log(self) -> logging.Logger:
        try:
            return self._logger
        except AttributeError:
            self._logger = logging.root.getChild(self.__class__.__module__ + '.' + self.__class__.__name__)
            return self._logger


class Base(LoggingMixin, ReprMixin):
    """Mixin to use as the base of other classes

    Currently extends LoggingMixing and ReprMixin
    """
    pass
