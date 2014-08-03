"""
Plain Python definition of the builtin functions related to run-time
program introspection.
"""

import sys

from __pypy__ import lookup_special

def _caller_locals():
    return sys._getframe(0).f_locals

def vars(*obj):
    """Return a dictionary of all the attributes currently bound in obj.  If
    called with no argument, return the variables bound in local scope."""

    if len(obj) == 0:
        return _caller_locals()
    elif len(obj) != 1:
        raise TypeError("vars() takes at most 1 argument.")
    try:
        return obj[0].__dict__
    except AttributeError:
        raise TypeError("vars() argument must have __dict__ attribute")

def dir(*args):
    """dir([object]) -> list of strings

    Return an alphabetized list of names comprising (some of) the attributes
    of the given object, and of attributes reachable from it:

    No argument:  the names in the current scope.
    Module object:  the module attributes.
    Type or class object:  its attributes, and recursively the attributes of
        its bases.
    Otherwise:  its attributes, its class's attributes, and recursively the
        attributes of its class's base classes.
    """
    if len(args) > 1:
        raise TypeError("dir expected at most 1 arguments, got %d" % len(args))
    if len(args) == 0:
        local_names = list(_caller_locals().keys()) # 2 stackframes away
        local_names.sort()
        return local_names

    import types
    obj = args[0]
    dir_meth = lookup_special(obj, "__dir__")
    if dir_meth is not None:
        names = dir_meth()
        if not isinstance(names, list):
            raise TypeError("__dir__() must return a list, not %r" % (
                type(names),))
        names.sort()
        return names
    elif isinstance(obj, types.ModuleType):
        try:
            return sorted(obj.__dict__)
        except AttributeError:
            return []
    elif isinstance(obj, type):
        # Don't look at __class__, as metaclass methods would be confusing.
        return sorted(_classdir(obj))
    else:
        names = set()
        ns = getattr(obj, '__dict__', None)
        if isinstance(ns, dict):
            names.update(ns)
        klass = getattr(obj, '__class__', None)
        if klass is not None:
            names.update(_classdir(klass))
        return sorted(names)

def _classdir(klass):
    """Return a set of the accessible attributes of class/type klass.

    This includes all attributes of klass and all of the base classes
    recursively.
    """
    names = set()
    try:
        names.update(klass.__dict__)
    except AttributeError:
        pass
    try:
        # XXX - Use of .__mro__ would be suggested, if the existance of
        # that attribute could be guarranted.
        bases = klass.__bases__
    except AttributeError:
        pass
    else:
        try:
            # Note that since we are only interested in the keys, the
            # order we merge classes is unimportant
            for base in bases:
                names.update(_classdir(base))
        except TypeError:
            pass
    return names
