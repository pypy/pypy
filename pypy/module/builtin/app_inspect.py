"""
Plain Python definition of the builtin functions related to run-time
program introspection.
"""

import sys

def globals():
    return sys._getframe(1).f_globals

def locals():
    return sys._getframe(1).f_locals

def _caller_locals(): 
    return sys._getframe(2).f_locals 

def _recursive_issubclass(cls, klass_or_tuple):
    if cls is klass_or_tuple:
        return True
    for base in cls.__bases__:
        if _recursive_issubclass(base, klass_or_tuple):
            return True
    return False

def issubclass(cls, klass_or_tuple):
    if _issubtype(type(klass_or_tuple), tuple):
        for klass in klass_or_tuple:
            if issubclass(cls, klass):
                return True
        return False
    try:
        return _issubtype(cls, klass_or_tuple)
    except TypeError:
        if not hasattr(cls, '__bases__'):
            raise TypeError, "arg 1 must be a class or type"
        if not hasattr(klass_or_tuple, '__bases__'):
            raise TypeError, "arg 2 must be a class or type or a tuple thereof"
        return _recursive_issubclass(cls, klass_or_tuple)


def isinstance(obj, klass_or_tuple):
    if issubclass(type(obj), klass_or_tuple):
        return True
    try:
        objcls = obj.__class__
    except AttributeError:
        return False
    else:
        return objcls is not type(obj) and issubclass(objcls, klass_or_tuple)


def vars(*obj):
    """return a dictionary of all the attributes currently bound in obj.  If
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

def hasattr(ob, attr):
    try:
        getattr(ob, attr)
        return True
    except AttributeError:
        return False

def callable(ob):
    for c in type(ob).__mro__:
        if '__call__' in c.__dict__:
            return True
    else:
        return False

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
        local_names.sort()
        return local_names

    import types
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
    #End _classdir

    obj = args[0]

    if isinstance(obj, types.ModuleType):
        try:
            result = obj.__dict__.keys()
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
            Dict.update(obj.__dict__)
        except AttributeError: pass
        try:
            Dict.update(_classdir(obj.__class__))
        except AttributeError: pass

        ## Comment from object.c:
        ## /* Merge in __members__ and __methods__ (if any).
        ## XXX Would like this to go away someday; for now, it's
        ## XXX needed to get at im_self etc of method objects. */
        for attr in ['__members__','__methods__']:
            try:
                for item in getattr(obj, attr):
                    if isinstance(item, types.StringTypes):
                        Dict[item] = None
            except (AttributeError, TypeError): pass

        result = Dict.keys()
        result.sort()
        return result
