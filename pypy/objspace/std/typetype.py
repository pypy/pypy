from pypy.interpreter.error import OperationError
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.dictproxyobject import descr_get_dictproxy

def descr__new__(space, w_typetype, w_name, w_bases, w_dict):
    "This is used to create user-defined classes only."
    from pypy.objspace.std.typeobject import W_TypeObject
    # XXX check types

    w_typetype = _precheck_for_new(space, w_typetype)
    
    bases_w = space.unpackiterable(w_bases)

    w_winner = w_typetype
    for base in bases_w:
        w_typ = space.type(base)
        if space.is_w(w_typ, space.w_classobj):
            continue # special-case old-style classes
        if space.is_true(space.issubtype(w_winner, w_typ)):
            continue
        if space.is_true(space.issubtype(w_typ, w_winner)):
            w_winner = w_typ
            continue
        raise OperationError(space.w_TypeError,
                             space.wrap("metaclass conflict: "
                                        "the metaclass of a derived class "
                                        "must be a (non-strict) subclass "
                                        "of the metaclasses of all its bases"))

    if not space.is_w(w_winner, w_typetype):
        newfunc = space.getattr(w_winner, space.wrap('__new__'))
        if not space.is_w(newfunc, space.getattr(space.w_type, space.wrap('__new__'))):
            return space.call_function(newfunc, w_winner, w_name, w_bases, w_dict)
        w_typetype = w_winner
        
    name = space.str_w(w_name)
    assert isinstance(name, str)
    dict_w = {}
    dictkeys_w = space.unpackiterable(w_dict)
    for w_key in dictkeys_w:
        key = space.str_w(w_key)
        dict_w[key] = space.getitem(w_dict, w_key)
    w_type = space.allocate_instance(W_TypeObject, w_typetype)
    W_TypeObject.__init__(w_type, space, name, bases_w or [space.w_object],
                          dict_w)
    return w_type

def _precheck_for_new(space, w_type):
    from pypy.objspace.std.typeobject import W_TypeObject
    if not isinstance(w_type, W_TypeObject):
        raise OperationError(space.w_TypeError,
                             space.wrap("X is not a type object (%s)" % (space.type(w_type).name)))
    return w_type

def _check(space, w_type, msg=None):
    from pypy.objspace.std.typeobject import W_TypeObject
    if not isinstance(w_type, W_TypeObject):
        raise OperationError(space.w_TypeError, 
                             space.wrap(msg or "descriptor is for 'type'"))
    return w_type


def descr_get__name__(space, w_type):
    w_type = _check(space, w_type)
    return space.wrap(w_type.name)

def descr_get__mro__(space, w_type):
    w_type = _check(space, w_type)
    # XXX this should be inside typeobject.py
    return space.newtuple(w_type.mro_w)

def descr_mro(space, w_type):
    w_type = _check(space, w_type,"expected type")
    return space.newlist(w_type.compute_mro())

def descr__bases(space, w_type):
    w_type = _check(space, w_type)
    from pypy.objspace.std.typeobject import W_TypeObject
    if not isinstance(w_type, W_TypeObject):
        raise OperationError(space.w_TypeError, 
                             space.wrap("descriptor is for 'type'"))
    return space.newtuple(w_type.bases_w)

def descr__base(space, w_type):
    w_type = _check(space, w_type)
    if w_type.w_bestbase is not None:
        return w_type.w_bestbase
    elif w_type is not space.w_object:
        return space.w_object
    else:
        return space.w_None

def descr__doc(space, w_type):
    w_type = _check(space, w_type)
    w_result = w_type.getdictvalue(space, '__doc__')
    if w_result is None:
        return space.w_None
    else:
        return space.get(w_result, space.w_None, w_type)

def descr__flags(space, w_type):
    w_type = _check(space, w_type)    
    return space.wrap(w_type.__flags__)

def defunct_descr_get__module(space, w_type):
    if w_type.is_heaptype():
        return w_type.dict_w['__module__']
    else:
        # here CPython checks for a module.name in the type description.
        # we skip that here and only provide the default
        return space.wrap('__builtin__')

# heaptypeness is not really the right criteria, because we
# also might get a module attribute from a faked type.
# therefore, we use the module attribute whenever it exists.

def descr_get__module(space, w_type):
    w_type = _check(space, w_type)
    return w_type.get_module()

def descr_set__module(space, w_type, w_value):
    w_type = _check(space, w_type)    
    if not w_type.is_heaptype():
        raise OperationError(space.w_TypeError, 
                             space.wrap("can't set %s.__module__" %
                                        w_type.name))
    if w_value is None:
        raise OperationError(space.w_TypeError, 
                             space.wrap("can't delete %s.__module__" %
                                        w_type.name))
    w_type.dict_w['__module__'] = w_value

# ____________________________________________________________

type_typedef = StdTypeDef("type",
    __new__ = newmethod(descr__new__),
    __name__ = GetSetProperty(descr_get__name__),
    __bases__ = GetSetProperty(descr__bases),
    __base__ = GetSetProperty(descr__base),
    __mro__ = GetSetProperty(descr_get__mro__),
    __dict__ = GetSetProperty(descr_get_dictproxy),
    __doc__ = GetSetProperty(descr__doc),
    mro = gateway.interp2app(descr_mro),
    __flags__ = GetSetProperty(descr__flags),
    __module__ = GetSetProperty(descr_get__module, descr_set__module),
    )
