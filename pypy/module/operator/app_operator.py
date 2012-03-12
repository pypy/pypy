'''NOT_RPYTHON: because of attrgetter and itemgetter
Operator interface.

This module exports a set of operators as functions. E.g. operator.add(x,y) is
equivalent to x+y.
'''
from __pypy__ import builtinify

def countOf(a,b): 
    'countOf(a, b) -- Return the number of times b occurs in a.'
    count = 0
    for x in a:
        if x == b:
            count += 1
    return count

def indexOf(a, b):
    'indexOf(a, b) -- Return the first index of b in a.'
    index = 0
    for x in a:
        if x == b:
            return index
        index += 1
    raise ValueError('sequence.index(x): x not in sequence')


def attrgetter(attr, *attrs):
    if attrs:
        getters = [single_attr_getter(a) for a in (attr,) + attrs]
        def getter(obj):
            return tuple([getter(obj) for getter in getters])
    else:
        getter = single_attr_getter(attr)
    return builtinify(getter)

def single_attr_getter(attr):
    if not isinstance(attr, str):
        def _raise_typeerror(obj):
            raise TypeError("argument must be a string, not %r" %
                            (type(attr).__name__,))
        return _raise_typeerror
    #
    def make_getter(name, prevfn=None):
        if prevfn is None:
            def getter(obj):
                return getattr(obj, name)
        else:
            def getter(obj):
                return getattr(prevfn(obj), name)
        return getter
    #
    last = 0
    getter = None
    while True:
        dot = attr.find(".", last)
        if dot < 0: break
        getter = make_getter(attr[last:dot], getter)
        last = dot + 1
    return make_getter(attr[last:], getter)


def itemgetter(item, *items):
    if items:
        list_of_indices = [item] + list(items)
        def getter(obj):
            return tuple([obj[i] for i in list_of_indices])
    else:
        def getter(obj):
            return obj[item]
    return builtinify(getter)


def methodcaller(method_name, *args, **kwargs):
    def call(obj):
        return getattr(obj, method_name)(*args, **kwargs)
    return builtinify(call)
