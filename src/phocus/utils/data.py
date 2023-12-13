import os
import pickle
from contextlib import contextmanager


@contextmanager
def pickled(filename):
    """Use filename as a pickle store

    Example Usage:
    with pickled("foo.db") as p:
        p("users", list).append(["srid", "passwd", 23])
    """
    if os.path.isfile(filename):
        data = pickle.load(open(filename))
    else:
        data = {}

    def getter(item, type):
        if item in data:
            return data[item]
        else:
            data[item] = type()
            return data[item]

    yield getter

    pickle.dump(data, open(filename, "w"))

