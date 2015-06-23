# Copied and adapted from lib-python/2.7/weakref.py.
# In PyPy (at least -STM), this is not used: a more
# efficient version is found in the _weakref module.

import UserDict, weakref


class idref(weakref.ref):

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, idref):
            return NotImplementedError
        s = self()
        o = other()
        return s is o is not None

    def __hash__(self):
        try:
            return self._hash_cache
        except AttributeError:
            self._hash_cache = id(self())
            return self._hash_cache


class weakkeyiddict(object):
    """ Mapping class that references keys weakly.
    In addition, uses the identity of the keys, rather than the equality.
    (Only a subset of the dict interface is available.)
    """

    def __init__(self):
        self.data = {}
        def remove(k, selfref=weakref.ref(self)):
            self = selfref()
            if self is not None:
                del self.data[k]
        self._remove = remove

    def __delitem__(self, key):
        del self.data[idref(key)]

    def __getitem__(self, key):
        return self.data[idref(key)]

    def __setitem__(self, key, value):
        self.data[idref(key, self._remove)] = value

    def get(self, key, default=None):
        return self.data.get(idref(key),default)

    def __contains__(self, key):
        return idref(key) in self.data

    def pop(self, key, *args):
        return self.data.pop(idref(key), *args)

    def setdefault(self, key, default=None):
        return self.data.setdefault(idref(key, self._remove),default)
