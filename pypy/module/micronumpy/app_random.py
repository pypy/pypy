from __future__ import absolute_import

from numpy import array
import random

_random = random.Random()

def get_state():
    return _random.getstate()

def set_state(state):
    _random.setstate(state)

def seed(seed):
    _random.seed(seed)

def rand(*shape):
    assert len(shape) == 1

    return array(_random.random() for x in range(shape[0]))

def randn(*shape):
    if len(shape) == 0:
        return _random.gauss(0, 1)
    assert len(shape) == 1

    return array(_random.gauss(0, 1) for x in range(shape[0]))

def standard_normal(size=None):
    return randn(*size)

def random_integers(low, high=None, size=None):
    print "random_integers called with %s, %s" % (low, high)

    if high is None:
        low, high = 1, low
    else:
        low, high = low, high

    print "values are now %s, %s"% (low, high)

    if size is None:
        return _random.randint(low, high)
    else:
        assert len(size) == 1

        return array(_random.randint(low, high) for x in range(size[0]))

def randint(low, high=None, size=None):
    print "randint called with %s, %s"% (low, high)
    if high is None:
        low, high = 0, low - 1
    else:
        low, high = low, high - 1

    print "values are now %s, %s"% (low, high)

    return random_integers(low, high, size)

