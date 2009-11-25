"""
ref = UnionRef(x) -> creates a reference to x, such that ref() is x.

Two references can be merged: ref.merge(ref2) make ref and ref2 interchangeable.
After a merge, ref() is ref2().  This is done by asking the two older objects
that ref and ref2 pointed to how they should be merged.  The point is that
large equivalence relations can be built this way:

    >>> ref1.merge(ref2)
    >>> ref3.merge(ref4)
    >>> ref1() is ref4()
    False
    >>> ref2.merge(ref3)
    >>> ref1() is ref4()
    True

By default, two objects x and y are merged by calling x.update(y).
"""

import UserDict
from pypy.tool.uid import uid


class UnionRef(object):
    __slots__ = ('_obj', '_parent', '_weight')

    def __init__(self, obj):
        "Build a new reference to 'obj'."
        self._obj = obj
        self._parent = None
        self._weight = 1

    def __call__(self):
        "Return the 'obj' that self currently references."
        return self._findrep()._obj

    def _findrep(self):
        p = self._parent
        if p:
            if p._parent:
                # this linked list is unnecessarily long, shorten it
                path = [self]
                while p._parent:
                    path.append(p)
                    p = p._parent
                for q in path:
                    q._parent = p
            return p
        return self

    def merge(self, other, union=None):
        "Merge two references.  After a.merge(b), a() and b() are identical."
        self  = self ._findrep()
        other = other._findrep()
        if self is not other:
            w1 = self ._weight
            w2 = other._weight
            if w1 < w2:
                self, other = other, self
            self._weight = w1 + w2
            other._parent = self
            o = other._obj
            del other._obj
            if union is not None:
                self._obj = union(self._obj, o)
            else:
                self.update(o)
        return self

    def update(self, obj):
        "Merge 'obj' in self.  Default implementation, can be overridden."
        self._obj.update(obj)

    def __hash__(self):
        raise TypeError("UnionRef objects are unhashable")

    def __eq__(self, other):
        return (isinstance(other, UnionRef) and
                self._findrep() is other._findrep())

    def __ne__(self, other):
        return not (self == other)


class UnionDict(object, UserDict.DictMixin):
    """Mapping class whose items can be unified.  Conceptually, instead of
    a set of (key, value) pairs, this is a set of ({keys}, value) pairs.
    The method merge(key1, key2) merges the two pairs containing, respectively,
    key1 and key2.
    """
    _slots = ('_data',)

    def __init__(self, dict=None, **kwargs):
        self._data = {}
        if dict is not None:
            self.update(dict)
        if len(kwargs):
            self.update(kwargs)

    def merge(self, key1, key2, union=None):
        self._data[key1] = self._data[key1].merge(self._data[key2], union)

    def copy(self):
        result = UnionDict()
        newrefs = {}
        for key, valueref in self._data.iteritems():
            valueref = valueref._findrep()
            try:
                newref = newrefs[valueref]
            except KeyError:
                newref = newrefs[valueref] = UnionRef(valueref())
            result._data[key] = newref
        return result

    def __repr__(self):
        return "<UnionDict at 0x%x>" % uid(self)

    def __getitem__(self, key):
        return self._data[key]()

    def __setitem__(self, key, value):
        self._data[key] = UnionRef(value)

    def __delitem__(self, key):
        del self._data[key]

    def keys(self):
        return self._data.keys()

    def has_key(self, key):
        return key in self._data

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def iteritems(self):
        for key, valueref in self._data.iteritems():
            yield (key, valueref())

    def clear(self):
        self._data.clear()

    def popitem(self):
        key, valueref = self._data.popitem()
        return key, valueref()

    def __len__(self):
        return len(self._data)
