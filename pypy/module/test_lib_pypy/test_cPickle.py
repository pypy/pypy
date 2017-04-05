from __future__ import absolute_import
import py

from lib_pypy import cPickle

def test_stack_underflow():
    py.test.raises(cPickle.UnpicklingError, cPickle.loads, "a string")

def test_bad_key():
    e = py.test.raises(cPickle.UnpicklingError, cPickle.loads, "v")
    assert str(e.value) == "invalid load key, 'v'."
