from pypy.interpreter.error import OperationError
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.dictproxyobject import dictproxy_descr


def descr__new__(space, w_typetype, w_name, w_bases, w_dict):
    "This is used to create user-defined classes only."
    from pypy.objspace.std.typeobject import W_TypeObject
    # XXX check types 
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
    w_type.__init__(space, name, bases_w or [space.w_object], dict_w)
    return w_type

def descr_get__mro__(space, w_type):
    # XXX this should be inside typeobject.py
    return space.newtuple(w_type.mro_w)

def descr_mro(space, w_type):
    return space.newlist(w_type.compute_mro())

def descr__bases(space, w_type):
    return space.newtuple(w_type.bases_w)

def descr__base(space, w_type):
    if w_type is space.w_object:
        return space.w_None
    b = w_type.instancetypedef.base
    if b is not None:
        return space.gettypeobject(b)
    else:
        return space.w_object

def descr__doc(space, w_type):
    return w_type.dict_w.get('__doc__')

# ____________________________________________________________

type_typedef = StdTypeDef("type",
    __new__ = newmethod(descr__new__),
    __name__ = attrproperty('name'),
    __bases__ = GetSetProperty(descr__bases),
    __base__ = GetSetProperty(descr__base),
    __mro__ = GetSetProperty(descr_get__mro__),
    __dict__ = dictproxy_descr,
    __doc__ = GetSetProperty(descr__doc),
    mro = newmethod(descr_mro),
    )
