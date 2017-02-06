from __pypy__ import reversed_dict, move_to_end
from _operator import eq as _eq
from reprlib import recursive_repr as _recursive_repr

class OrderedDict(dict):
    '''Dictionary that remembers insertion order.

    In PyPy all dicts are ordered anyway.  This is mostly useful as a
    placeholder to mean "this dict must be ordered even on CPython".

    Known difference: iterating over an OrderedDict which is being
    concurrently modified raises RuntimeError in PyPy.  In CPython
    instead we get some behavior that appears reasonable in some
    cases but is nonsensical in other cases.  This is officially
    forbidden by the CPython docs, so we forbid it explicitly for now.
    '''

    def __reversed__(self):
        return reversed_dict(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if last:
            return dict.popitem(self)
        else:
            it = dict.__iter__(self)
            try:
                k = next(it)
            except StopIteration:
                raise KeyError('dictionary is empty')
            return (k, self.pop(k))

    def move_to_end(self, key, last=True):
        '''Move an existing element to the end (or beginning if last==False).

        Raises KeyError if the element does not exist.
        When last=True, acts like a fast version of self[key]=self.pop(key).

        '''
        return move_to_end(self, key, last)

    @_recursive_repr()
    def __repr__(self):
        'od.__repr__() <==> repr(od)'
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self.items()))

    def __reduce__(self):
        'Return state information for pickling'
        inst_dict = vars(self).copy()
        return self.__class__, (), inst_dict or None, None, iter(self.items())

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return dict.__eq__(self, other) and all(map(_eq, self, other))
        return dict.__eq__(self, other)

    __ne__ = object.__ne__

    def keys(self):
        "D.keys() -> a set-like object providing a view on D's keys"
        return _OrderedDictKeysView(self)

    def items(self):
        "D.items() -> a set-like object providing a view on D's items"
        return _OrderedDictItemsView(self)

    def values(self):
        "D.values() -> an object providing a view on D's values"
        return _OrderedDictValuesView(self)


class _OrderedDictKeysView(KeysView):
    def __reversed__(self):
        yield from reversed_dict(self._mapping)

class _OrderedDictItemsView(ItemsView):
    def __reversed__(self):
        for key in reversed_dict(self._mapping):
            yield (key, self._mapping[key])

class _OrderedDictValuesView(ValuesView):
    def __reversed__(self):
        for key in reversed_dict(self._mapping):
            yield self._mapping[key]
