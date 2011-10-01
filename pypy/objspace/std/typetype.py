from pypy.interpreter import gateway
from pypy.interpreter.argument import Arguments
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.typedef import (GetSetProperty, descr_get_dict,
                                      weakref_descr)
from pypy.objspace.std.stdtypedef import StdTypeDef


def descr__new__(space, w_typetype, w_name, w_bases=gateway.NoneNotWrapped,
    w_dict=gateway.NoneNotWrapped):

    "This is used to create user-defined classes only."
    from pypy.objspace.std.typeobject import W_TypeObject
    # XXX check types

    w_typetype = _precheck_for_new(space, w_typetype)

    # special case for type(x)
    if (space.is_w(space.type(w_typetype), space.w_type) and w_bases is None and
        w_dict is None):
        return space.type(w_name)
    elif w_bases is None or w_dict is None:
        raise OperationError(space.w_TypeError, space.wrap("type() takes 1 or 3 arguments"))


    bases_w = space.fixedview(w_bases)

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
    dictkeys_w = space.listview(w_dict)
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
        raise operationerrfmt(space.w_TypeError,
                              "X is not a type object (%s)",
                              space.type(w_type).getname(space))
    return w_type

# ____________________________________________________________

def _check(space, w_type, w_msg=None):
    from pypy.objspace.std.typeobject import W_TypeObject
    if not isinstance(w_type, W_TypeObject):
        if w_msg is None:
            w_msg = space.wrap("descriptor is for 'type'")
        raise OperationError(space.w_TypeError, w_msg)
    return w_type


def descr_get__name__(space, w_type):
    w_type = _check(space, w_type)
    return space.wrap(w_type.name)

def descr_set__name__(space, w_type, w_value):
    w_type = _check(space, w_type)    
    if not w_type.is_heaptype():
        raise operationerrfmt(space.w_TypeError, 
                              "can't set %s.__name__", w_type.name)
    w_type.name = space.str_w(w_value)

def descr_get__mro__(space, w_type):
    w_type = _check(space, w_type)
    return space.newtuple(w_type.mro_w)

def descr_mro(space, w_type):
    """Return a type's method resolution order."""
    w_type = _check(space, w_type, space.wrap("expected type"))
    return space.newlist(w_type.compute_default_mro())

def descr_get__bases__(space, w_type):
    w_type = _check(space, w_type)
    return space.newtuple(w_type.bases_w)

def mro_subclasses(space, w_type, temp):
    from pypy.objspace.std.typeobject import W_TypeObject, compute_mro
    temp.append((w_type, w_type.mro_w))
    compute_mro(w_type)
    for w_sc in w_type.get_subclasses():
        assert isinstance(w_sc, W_TypeObject)
        mro_subclasses(space, w_sc, temp)

def descr_set__bases__(space, w_type, w_value):
    # this assumes all app-level type objects are W_TypeObject
    from pypy.objspace.std.typeobject import W_TypeObject
    from pypy.objspace.std.typeobject import check_and_find_best_base
    from pypy.objspace.std.typeobject import get_parent_layout
    from pypy.objspace.std.typeobject import is_mro_purely_of_types
    w_type = _check(space, w_type)
    if not w_type.is_heaptype():
        raise operationerrfmt(space.w_TypeError,
                              "can't set %s.__bases__", w_type.name)
    if not space.isinstance_w(w_value, space.w_tuple):
        raise operationerrfmt(space.w_TypeError,
                              "can only assign tuple to %s.__bases__, not %s",
                              w_type.name,
                              space.type(w_value).getname(space))
    newbases_w = space.fixedview(w_value)
    if len(newbases_w) == 0:
        raise operationerrfmt(space.w_TypeError,
                    "can only assign non-empty tuple to %s.__bases__, not ()",
                              w_type.name)

    for w_newbase in newbases_w:
        if isinstance(w_newbase, W_TypeObject):
            if w_type in w_newbase.compute_default_mro():
                raise OperationError(space.w_TypeError,
                                     space.wrap("a __bases__ item causes"
                                                " an inheritance cycle"))

    w_oldbestbase = check_and_find_best_base(space, w_type.bases_w)
    w_newbestbase = check_and_find_best_base(space, newbases_w)
    oldlayout = w_oldbestbase.get_full_instance_layout()
    newlayout = w_newbestbase.get_full_instance_layout()

    if oldlayout != newlayout:
        raise operationerrfmt(space.w_TypeError,
                           "__bases__ assignment: '%s' object layout"
                           " differs from '%s'",
                           w_newbestbase.getname(space),
                           w_oldbestbase.getname(space))

    # invalidate the version_tag of all the current subclasses
    w_type.mutated(None)

    # now we can go ahead and change 'w_type.bases_w'
    saved_bases_w = w_type.bases_w
    temp = []
    try:
        for w_oldbase in saved_bases_w:
            if isinstance(w_oldbase, W_TypeObject):
                w_oldbase.remove_subclass(w_type)
        w_type.bases_w = newbases_w
        for w_newbase in newbases_w:
            if isinstance(w_newbase, W_TypeObject):
                w_newbase.add_subclass(w_type)
        # try to recompute all MROs
        mro_subclasses(space, w_type, temp)
    except:
        for cls, old_mro in temp:
            cls.mro_w = old_mro
        w_type.bases_w = saved_bases_w
        raise
    if (space.config.objspace.std.withtypeversion and
        w_type.version_tag() is not None and
        not is_mro_purely_of_types(w_type.mro_w)):
        # Disable method cache if the hierarchy isn't pure.
        w_type._version_tag = None
        for w_subclass in w_type.get_subclasses():
            if isinstance(w_subclass, W_TypeObject):
                w_subclass._version_tag = None
    assert w_type.w_same_layout_as is get_parent_layout(w_type)  # invariant

def descr__base(space, w_type):
    from pypy.objspace.std.typeobject import find_best_base
    w_type = _check(space, w_type)
    return find_best_base(space, w_type.bases_w)

def descr__doc(space, w_type):
    if space.is_w(w_type, space.w_type):
        return space.wrap("""type(object) -> the object's type
type(name, bases, dict) -> a new type""")
    w_type = _check(space, w_type)
    if not w_type.is_heaptype():
        return w_type.w_doc
    w_result = w_type.getdictvalue(space, '__doc__')
    if w_result is None:
        return space.w_None
    else:
        return space.get(w_result, space.w_None, w_type)

def descr__flags(space, w_type):
    from copy_reg import _HEAPTYPE
    _CPYTYPE = 1 # used for non-heap types defined in C
    _ABSTRACT = 1 << 20
    #
    w_type = _check(space, w_type)
    flags = 0
    if w_type.flag_heaptype: flags |= _HEAPTYPE
    if w_type.flag_cpytype:  flags |= _CPYTYPE
    if w_type.flag_abstract: flags |= _ABSTRACT
    return space.wrap(flags)

def descr_get__module(space, w_type):
    w_type = _check(space, w_type)
    return w_type.get_module()

def descr_set__module(space, w_type, w_value):
    w_type = _check(space, w_type)
    w_type.setdictvalue(space, '__module__', w_value)

def descr_get___abstractmethods__(space, w_type):
    w_type = _check(space, w_type)
    # type itself has an __abstractmethods__ descriptor (this). Don't return it
    if not space.is_w(w_type, space.w_type):
        w_result = w_type.getdictvalue(space, "__abstractmethods__")
        if w_result is not None:
            return w_result
    raise OperationError(space.w_AttributeError,
                         space.wrap("__abstractmethods__"))

def descr_set___abstractmethods__(space, w_type, w_new):
    w_type = _check(space, w_type)
    w_type.setdictvalue(space, "__abstractmethods__", w_new)
    w_type.set_abstract(space.is_true(w_new))

def descr_del___abstractmethods__(space, w_type):
    w_type = _check(space, w_type)
    if not w_type.deldictvalue(space, "__abstractmethods__"):
        raise OperationError(space.w_AttributeError,
                             space.wrap("__abstractmethods__"))
    w_type.set_abstract(False)

def descr___subclasses__(space, w_type):
    """Return the list of immediate subclasses."""
    w_type = _check(space, w_type)
    return space.newlist(w_type.get_subclasses())

# ____________________________________________________________

type_typedef = StdTypeDef("type",
    __new__ = gateway.interp2app(descr__new__),
    __name__ = GetSetProperty(descr_get__name__, descr_set__name__),
    __bases__ = GetSetProperty(descr_get__bases__, descr_set__bases__),
    __base__ = GetSetProperty(descr__base),
    __mro__ = GetSetProperty(descr_get__mro__),
    __dict__ = GetSetProperty(descr_get_dict),
    __doc__ = GetSetProperty(descr__doc),
    mro = gateway.interp2app(descr_mro),
    __flags__ = GetSetProperty(descr__flags),
    __module__ = GetSetProperty(descr_get__module, descr_set__module),
    __abstractmethods__ = GetSetProperty(descr_get___abstractmethods__,
                                         descr_set___abstractmethods__,
                                         descr_del___abstractmethods__),
    __subclasses__ = gateway.interp2app(descr___subclasses__),
    __weakref__ = weakref_descr,
    )
