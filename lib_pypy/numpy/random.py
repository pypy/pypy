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

