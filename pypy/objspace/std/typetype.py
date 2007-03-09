from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import weakref_descr
from pypy.objspace.std.stdtypedef import *

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
    w_type.ready()
    return w_type

def _precheck_for_new(space, w_type):
    from pypy.objspace.std.typeobject import W_TypeObject
    if not isinstance(w_type, W_TypeObject):
        raise OperationError(space.w_TypeError,
                             space.wrap("X is not a type object (%s)" %
                                     (space.type(w_type).getname(space, '?'))))
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

def descr_set__name__(space, w_type, w_value):
    w_type = _check(space, w_type)    
    if not w_type.is_heaptype():
        raise OperationError(space.w_TypeError, 
                             space.wrap("can't set %s.__name__" %
                                        w_type.name))
    w_type.name = space.str_w(w_value)

def descr_get__mro__(space, w_type):
    w_type = _check(space, w_type)
    # XXX this should be inside typeobject.py
    return space.newtuple(w_type.mro_w)

def descr_mro(space, w_type):
    """Return a type's method resolution order."""
    w_type = _check(space, w_type,"expected type")
    return space.newlist(w_type.compute_mro())

def descr_get__bases__(space, w_type):
    w_type = _check(space, w_type)
    return space.newtuple(w_type.bases_w)

def mro_subclasses(space, w_type, temp):
    from pypy.objspace.std.typeobject import W_TypeObject
    if not w_type.weak_subclasses_w:
        return
    for w_ref in w_type.weak_subclasses_w:
        w_sc = space.call_function(w_ref)
        if not space.is_w(w_sc, space.w_None):
            assert isinstance(w_sc, W_TypeObject)
            temp.append((w_sc, w_sc.mro_w))
            mro_internal(space, w_sc)
            mro_subclasses(space, w_sc, temp)

# should be a W_TypeObject method i guess
def mro_internal(space, w_type):
    if not space.is_w(space.type(w_type), space.w_type):
        #w_type.mro_w = []
        mro_func = space.lookup(w_type, 'mro')
        mro_func_args = Arguments(space, [w_type])
        w_mro = space.call_args(mro_func, mro_func_args)
        w_type.mro_w = space.unpackiterable(w_mro)
        # do some checking here
    else:
        w_type.mro_w = w_type.compute_mro()

def best_base(space, newstyle_bases_w):
    if not newstyle_bases_w:
        raise OperationError(space.w_TypeError,
                             space.wrap("a new-style class can't have only classic bases"))
    w_bestbase = None
    w_winner = None
    for w_base in newstyle_bases_w:
        w_candidate = w_base.get_layout()
        if w_winner is None:
            w_winner = w_candidate
            w_bestbase = w_base
        elif space.is_true(space.issubtype(w_winner, w_candidate)):
            pass
        elif space.is_true(space.issubtype(w_candidate, w_winner)):
            w_winner = w_candidate
            w_bestbase = w_base
        else:
            raise OperationError(space.w_TypeError,
                                 space.wrap("multiple bases have instance lay-out conflict"))
    return w_bestbase

def descr_set__bases__(space, w_type, w_value):
    from pypy.objspace.std.typeobject import W_TypeObject
    # this assumes all app-level type objects are W_TypeObject
    w_type = _check(space, w_type)
    if not w_type.is_heaptype():
        raise OperationError(space.w_TypeError,
                             space.wrap("can't set %s.__bases__" %
                                        w_type.name))
    if not space.is_true(space.isinstance(w_value, space.w_tuple)):
        raise OperationError(space.w_TypeError,
                             space.wrap("can only assign tuple"
                                        " to %s.__bases__, not %s"%
                                     (w_type.name,
                                      space.type(w_value).getname(space, '?'))))
    if space.int_w(space.len(w_value)) == 0:
        raise OperationError(space.w_TypeError,
                             space.wrap("can only assign non-empty tuple to %s.__bases__, not ()"%
                                        w_type.name))
    new_newstyle_bases = []
    for w_base in space.unpackiterable(w_value):
        if not isinstance(w_base, W_TypeObject):
            w_typ = space.type(w_base)
            if not space.is_w(w_typ, space.w_classobj):
                raise OperationError(space.w_TypeError,
                                     space.wrap("%s.__bases__ must be tuple "
                                                "of old- or new-style classes"
                                                ", not '%s'"%
                                                (w_type.name,
                                                 w_typ.getname(space, '?'))))
        else:
            new_newstyle_bases.append(w_base)
            if space.is_true(space.issubtype(w_base, w_type)):
                raise OperationError(space.w_TypeError,
                                     space.wrap("a __bases__ item causes an inheritance cycle"))

    new_base = best_base(space, new_newstyle_bases)

    if w_type.w_bestbase.get_full_instance_layout() != new_base.get_full_instance_layout():
        raise OperationError(space.w_TypeError,
                             space.wrap("__bases__ assignment: '%s' object layout differs from '%s'" %
                                        (w_type.getname(space, '?'), new_base.getname(space, '?'))))
    if space.config.objspace.std.withtypeversion:
        # it does not make sense to cache this type, it changes bases
        w_type.version_tag = None

    saved_bases = w_type.bases_w
    saved_base = w_type.w_bestbase
    saved_mro = w_type.mro_w

    w_type.bases_w = space.unpackiterable(w_value)
    w_type.w_bestbase = new_base

    temp = []
    try:
        mro_internal(space, w_type)

        mro_subclasses(space, w_type, temp)

        for old_base in saved_bases:
            if isinstance(old_base, W_TypeObject):
                old_base.remove_subclass(w_type)
        for new_base in new_newstyle_bases:
            new_base.add_subclass(w_type)
    except:
        for cls, old_mro in temp:
            cls.mro_w = old_mro
        w_type.bases_w = saved_bases
        w_type.w_bestbase = saved_base
        w_type.mro_w = saved_mro
        raise
    
def descr__base(space, w_type):
    w_type = _check(space, w_type)
    if w_type.w_bestbase is not None:
        return w_type.w_bestbase
    elif w_type is not space.w_object:
        return space.w_object
    else:
        return space.w_None

def descr__doc(space, w_type):
    if space.is_w(w_type, space.w_type):
        return space.wrap("""type(object) -> the object's type
type(name, bases, dict) -> a new type""")
    w_type = _check(space, w_type)
    w_result = w_type.getdictvalue_w(space, '__doc__')
    if w_result is None:
        return space.w_None
    else:
        return space.get(w_result, space.w_None, w_type)

def descr__flags(space, w_type):
    w_type = _check(space, w_type)    
    return space.wrap(w_type.__flags__)

def descr_get__module(space, w_type):
    w_type = _check(space, w_type)
    return w_type.get_module()

def descr_set__module(space, w_type, w_value):
    w_type = _check(space, w_type)    
    if not w_type.is_heaptype():
        raise OperationError(space.w_TypeError, 
                             space.wrap("can't set %s.__module__" %
                                        w_type.name))
    w_type.dict_w['__module__'] = w_value

def descr___subclasses__(space, w_type):
    """Return the list of immediate subclasses."""
    w_type = _check(space, w_type)
    return space.newlist(w_type.get_subclasses())

# ____________________________________________________________

type_typedef = StdTypeDef("type",
    __new__ = newmethod(descr__new__),
    __name__ = GetSetProperty(descr_get__name__, descr_set__name__),
    __bases__ = GetSetProperty(descr_get__bases__, descr_set__bases__),
    __base__ = GetSetProperty(descr__base),
    __mro__ = GetSetProperty(descr_get__mro__),
    __dict__ = GetSetProperty(descr_get_dict),
    __doc__ = GetSetProperty(descr__doc),
    mro = gateway.interp2app(descr_mro),
    __flags__ = GetSetProperty(descr__flags),
    __module__ = GetSetProperty(descr_get__module, descr_set__module),
    __subclasses__ = gateway.interp2app(descr___subclasses__),
    __weakref__ = weakref_descr,
    )
