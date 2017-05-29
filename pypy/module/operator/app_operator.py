'''NOT_RPYTHON: because of attrgetter and itemgetter
Operator interface.

This module exports a set of operators as functions. E.g. operator.add(x,y) is
equivalent to x+y.
'''

import __pypy__


def countOf(a,b):
    'countOf(a, b) -- Return the number of times b occurs in a.'
    count = 0
    for x in a:
        if x == b:
            count += 1
    return count

def delslice(obj, start, end):
    'delslice(a, b, c) -- Same as del a[b:c].'
    if not isinstance(start, int) or not isinstance(end, int):
        raise TypeError("an integer is expected")
    del obj[start:end]
__delslice__ = delslice

def getslice(a, start, end):
    'getslice(a, b, c) -- Same as a[b:c].'
    if not isinstance(start, int) or not isinstance(end, int):
        raise TypeError("an integer is expected")
    return a[start:end]
__getslice__ = getslice

def indexOf(a, b):
    'indexOf(a, b) -- Return the first index of b in a.'
    index = 0
    for x in a:
        if x == b:
            return index
        index += 1
    raise ValueError('sequence.index(x): x not in sequence')

def isNumberType(obj,):
    'isNumberType(a) -- Return True if a has a numeric type, False otherwise.'
    return (__pypy__.lookup_special(obj, '__int__') is not None or
            __pypy__.lookup_special(obj, '__float__') is not None)

def repeat(obj, num):
    'repeat(a, b) -- Return a * b, where a is a sequence, and b is an integer.'
    import operator

    if not isinstance(num, (int, long)):
        raise TypeError('an integer is required')
    if not operator.isSequenceType(obj):
        raise TypeError("non-sequence object can't be repeated")

    return obj * num

__repeat__ = repeat

def setslice(a, b, c, d):
    'setslice(a, b, c, d) -- Same as a[b:c] = d.'
    a[b:c] = d
__setslice__ = setslice


def _resolve_attr_chain(chain, obj, idx=0):
    obj = getattr(obj, chain[idx])
    if idx + 1 == len(chain):
        return obj
    else:
        return _resolve_attr_chain(chain, obj, idx + 1)

class attrgetter(object):
    def __init__(self, attr, *attrs):
        if not isinstance(attr, basestring):
            self._error(attr)
            return
        if attrs:
            for a in attrs:
                if not isinstance(a, basestring):
                    self._error(a)
                    return
            self._multi_attrs = [
                a.split(".") for a in [attr] + list(attrs)
            ]
            self._call = self._multi_attrgetter
        elif "." not in attr:
            self._simple_attr = attr
            self._call = self._simple_attrgetter
        else:
            self._single_attr = attr.split(".")
            self._call = self._single_attrgetter

    def _error(self, attr):
        def _raise_typeerror(obj):
            raise TypeError(
                "attribute name must be a string, not %r" % type(attr).__name__
            )
        self._call = _raise_typeerror

    def __call__(self, obj):
        return self._call(obj)

    def _simple_attrgetter(self, obj):
        return getattr(obj, self._simple_attr)

    def _single_attrgetter(self, obj):
        return _resolve_attr_chain(self._single_attr, obj)

    def _multi_attrgetter(self, obj):
        return tuple([
            _resolve_attr_chain(attrs, obj)
            for attrs in self._multi_attrs
        ])


class itemgetter(object):
    def __init__(self, item, *items):
        self._single = not bool(items)
        if self._single:
            self._idx = item
        else:
            self._idx = [item] + list(items)

    def __call__(self, obj):
        if self._single:
            return obj[self._idx]
        else:
            return tuple([obj[i] for i in self._idx])


class methodcaller(object):
    def __init__(*args, **kwargs):
        if len(args) < 2:
            raise TypeError("methodcaller() called with not enough arguments")
        self, method_name = args[:2]
        self._method_name = method_name
        self._args = args[2:]
        self._kwargs = kwargs

    def __call__(self, obj):
        return getattr(obj, self._method_name)(*self._args, **self._kwargs)
