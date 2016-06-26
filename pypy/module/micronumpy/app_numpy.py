from __future__ import absolute_import

import math
import pickle
import struct
import types

import _numpypy
from _numpypy.multiarray import set_docstring, _reconstruct
from copy_reg import _extension_registry


def _save_global_reconstruct(self, obj, name=None, pack=struct.pack):
    """
    This function is responsible for essentially lying about the origins of the
    numpy _reconstruct function so that pickles of numpy ndarrays can be
    pickled in pypy and unpickled in cpython. Going in the other direction
    worked without needing a change.

    :param self: Pickler (or subclass) instance.
    :param obj: Object to pickle; in this case always a BuiltinFunctionType.
    :param name: Ignored in the _reconstruct case.
    :param pack: Ignored in the _reconstruct case.
    :return: None
    """
    if obj is _reconstruct:
        module = 'numpy.core.multiarray'
        name = '_reconstruct'

        # It's not clear how to handle this properly. Perhaps fall back to
        # original implementation?
        assert not _extension_registry.get((module, name))
        assert not _extension_registry.get(('_numpypy.multiarray', name))

        self.write(pickle.GLOBAL + module + '\n' + name + '\n')
        self.memoize(obj)
    else:
        self.save_global(obj, name, pack)

pickle.Pickler.dispatch[types.BuiltinFunctionType] = _save_global_reconstruct


def arange(start, stop=None, step=1, dtype=None):
    '''arange([start], stop[, step], dtype=None)
    Generate values in the half-interval [start, stop).
    '''
    if stop is None:
        stop = start
        start = 0
    if dtype is None:
        # find minimal acceptable dtype but not less than int
        dtype = _numpypy.multiarray.result_type(start, stop, step, int)
    length = math.ceil((float(stop) - start) / step)
    length = int(length)
    arr = _numpypy.multiarray.empty(length, dtype=dtype)
    i = start
    for j in xrange(arr.size):
        arr[j] = i
        i += step
    return arr


def add_docstring(obj, docstring):
    old_doc = getattr(obj, '__doc__', None)
    if old_doc is not None:
        raise RuntimeError("%s already has a docstring" % obj)
    try:
        set_docstring(obj, docstring)
    except:
        raise TypeError("Cannot set a docstring for %s" % obj)
