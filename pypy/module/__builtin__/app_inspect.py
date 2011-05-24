"""
Plain Python definition of the builtin functions related to run-time
program introspection.
"""

import sys

from __pypy__ import lookup_special

def _caller_locals(): 
    # note: the reason why this is working is because the functions in here are
    # compiled by geninterp, so they don't have a frame
    return sys._getframe(0).f_locals 

def vars(*obj):
    """Return a dictionary of all the attributes currently bound in obj.  If
    called with no argument, return the variables bound in local scope."""

    if len(obj) == 0:
        return _caller_locals()
    elif len(obj) != 1:
        raise TypeError, "vars() takes at most 1 argument."
    else:
        try:
            return obj[0].__dict__
        except AttributeError:
            raise TypeError, "vars() argument must have __dict__ attribute"

# Replaced by the interp-level helper space.callable(): 
##def callable(ob):
##    import __builtin__ # XXX this is insane but required for now for geninterp
##    for c in type(ob).__mro__:
##        if '__call__' in c.__dict__:
##            if isinstance(ob, __builtin__._instance): # old style instance!
##                return getattr(ob, '__call__', None) is not None
##            return True
##    else:
##        return False

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
        raise TypeError("dir expected at most 1 arguments, got %d"
                        % len(args))
    if len(args) == 0:
        local_names = _caller_locals().keys() # 2 stackframes away
        if not isinstance(local_names, list):
            raise TypeError("expected locals().keys() to be a list")
        local_names.sort()
        return local_names

    import types

    obj = args[0]

    dir_meth = None
    if isinstance(obj, types.InstanceType):
        try:
            dir_meth = getattr(obj, "__dir__")
        except AttributeError:
            pass
    else:
        dir_meth = lookup_special(obj, "__dir__")
    if dir_meth is not None:
        result = dir_meth()
        if not isinstance(result, list):
            raise TypeError("__dir__() must return a list, not %r" % (
                type(result),))
        result.sort()
        return result
    elif isinstance(obj, types.ModuleType):
        try:
            result = list(obj.__dict__)
            result.sort()
            return result
        except AttributeError:
            return []

    elif isinstance(obj, (types.TypeType, types.ClassType)):
        #Don't look at __class__, as metaclass methods would be confusing.
        result = _classdir(obj).keys()
        result.sort()
        return result

    else: #(regular item)
        Dict = {}
        try:
            if isinstance(obj.__dict__, dict):
                Dict.update(obj.__dict__)
        except AttributeError:
            pass
        try:
            Dict.update(_classdir(obj.__class__))
        except AttributeError:
            pass

        ## Comment from object.c:
        ## /* Merge in __members__ and __methods__ (if any).
        ## XXX Would like this to go away someday; for now, it's
        ## XXX needed to get at im_self etc of method objects. */
        for attr in ['__members__','__methods__']:
            try:
                l = getattr(obj, attr)
                if not isinstance(l, list):
                    continue
                for item in l:
                    if isinstance(item, types.StringTypes):
                        Dict[item] = None
            except (AttributeError, TypeError):
                pass

        result = Dict.keys()
        result.sort()
        return result

def _classdir(klass):
    """Return a dict of the accessible attributes of class/type klass.

    This includes all attributes of klass and all of the
    base classes recursively.

    The values of this dict have no meaning - only the keys have
    meaning.  
    """
    Dict = {}
    try:
        Dict.update(klass.__dict__)
    except AttributeError: pass 
    try:
        # XXX - Use of .__mro__ would be suggested, if the existance
        #   of that attribute could be guarranted.
        bases = klass.__bases__
    except AttributeError: pass
    else:
        try:
            #Note that since we are only interested in the keys,
            #  the order we merge classes is unimportant
            for base in bases:
                Dict.update(_classdir(base))
        except TypeError: pass
    return Dict
