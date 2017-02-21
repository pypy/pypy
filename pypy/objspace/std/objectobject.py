"""The builtin object type implementation"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import applevel, interp2app, unwrap_spec
from pypy.interpreter.typedef import (
    GetSetProperty, TypeDef, default_identity_hash)
from pypy.objspace.descroperation import Object


app = applevel(r'''
def _abstract_method_error(typ):
    methods = ", ".join(sorted(typ.__abstractmethods__))
    err = "Can't instantiate abstract class %s with abstract methods %s"
    raise TypeError(err % (typ.__name__, methods))

def reduce_1(obj, proto):
    import copyreg
    return copyreg._reduce_ex(obj, proto)

def _getstate(obj):
    cls = obj.__class__

    try:
        getstate = obj.__getstate__
    except AttributeError:
        # and raises a TypeError if the condition holds true, this is done
        # just before reduce_2 is called in pypy
        state = getattr(obj, "__dict__", None)
        names = slotnames(cls) # not checking for list
        if names is not None:
            slots = {}
            for name in names:
                try:
                    value = getattr(obj, name)
                except AttributeError:
                    pass
                else:
                    slots[name] =  value
            if slots:
                state = state, slots
    else:
        state = getstate()
    return state

def reduce_2(obj, proto, args, kwargs):
    cls = obj.__class__

    if not hasattr(type(obj), "__new__"):
        raise TypeError("can't pickle %s objects" % type(obj).__name__)

    import copyreg

    if not isinstance(args, tuple):
        raise TypeError("__getnewargs__ should return a tuple")
    if not kwargs:
       newobj = copyreg.__newobj__
       args2 = (cls,) + args
    elif proto >= 4:
       newobj = copyreg.__newobj_ex__
       args2 = (cls, args, kwargs)
    else:
       raise ValueError("must use protocol 4 or greater to copy this "
                        "object; since __getnewargs_ex__ returned "
                        "keyword arguments.")
    state = _getstate(obj)
    listitems = iter(obj) if isinstance(obj, list) else None
    dictitems = iter(obj.items()) if isinstance(obj, dict) else None

    return newobj, args2, state, listitems, dictitems


def slotnames(cls):
    if not isinstance(cls, type):
        return None

    try:
        return cls.__dict__["__slotnames__"]
    except KeyError:
        pass

    import copyreg
    slotnames = copyreg._slotnames(cls)
    if not isinstance(slotnames, list) and slotnames is not None:
        raise TypeError("copyreg._slotnames didn't return a list or None")
    return slotnames
''', filename=__file__)

_abstract_method_error = app.interphook("_abstract_method_error")
reduce_1 = app.interphook('reduce_1')
reduce_2 = app.interphook('reduce_2')


class W_ObjectObject(W_Root):
    """Instances of this class are what the user can directly see with an
    'object()' call."""


def _excess_args(__args__):
    return bool(__args__.arguments_w) or bool(__args__.keywords)

def descr__new__(space, w_type, __args__):
    from pypy.objspace.std.typeobject import _precheck_for_new
    w_type = _precheck_for_new(space, w_type)

    if _excess_args(__args__):
        w_parent_new, _ = space.lookup_in_type_where(w_type, '__new__')
        w_parent_init, _ = space.lookup_in_type_where(w_type, '__init__')
        w_parent_new, _ = space.lookup_in_type_where(w_type, '__new__')
        if (w_parent_init is space.w_object or
            w_parent_new is not space.w_object):
            raise oefmt(space.w_TypeError,
                        "object() takes no parameters")
    if w_type.is_abstract():
        _abstract_method_error(space, w_type)
    return space.allocate_instance(W_ObjectObject, w_type)


def descr___subclasshook__(space, __args__):
    return space.w_NotImplemented


def descr__init__(space, w_obj, __args__):
    if _excess_args(__args__):
        w_type = space.type(w_obj)
        w_parent_init, _ = space.lookup_in_type_where(w_type, '__init__')
        w_parent_new, _ = space.lookup_in_type_where(w_type, '__new__')
        w_parent_init, _ = space.lookup_in_type_where(w_type, '__init__')
        if (w_parent_new is space.w_object or
            w_parent_init is not space.w_object):
            raise oefmt(space.w_TypeError,
                        "object.__init__() takes no parameters")


def descr_get___class__(space, w_obj):
    return space.type(w_obj)


def descr_set___class__(space, w_obj, w_newcls):
    from pypy.objspace.std.typeobject import W_TypeObject
    if not isinstance(w_newcls, W_TypeObject):
        raise oefmt(space.w_TypeError,
                    "__class__ must be set to new-style class, not '%T' "
                    "object", w_newcls)
    if not w_newcls.is_heaptype():
        raise oefmt(space.w_TypeError,
                    "__class__ assignment: only for heap types")
    w_oldcls = space.type(w_obj)
    assert isinstance(w_oldcls, W_TypeObject)
    if (w_oldcls.get_full_instance_layout() ==
        w_newcls.get_full_instance_layout()):
        w_obj.setclass(space, w_newcls)
    else:
        raise oefmt(space.w_TypeError,
                    "__class__ assignment: '%N' object layout differs from "
                    "'%N'", w_oldcls, w_newcls)


def descr__repr__(space, w_obj):
    classname = space.getfulltypename(w_obj)
    return w_obj.getrepr(space, u'%s object' % (classname,))


def descr__str__(space, w_obj):
    w_type = space.type(w_obj)
    w_impl = w_type.lookup("__repr__")
    if w_impl is None:
        # can it really occur?
        raise oefmt(space.w_TypeError, "operand does not support unary str")
    return space.get_and_call_function(w_impl, w_obj)


@unwrap_spec(proto=int)
def descr__reduce__(space, w_obj, proto=0):
    w_proto = space.newint(proto)
    if proto >= 2:
        w_descr = space.lookup(w_obj, '__getnewargs_ex__')
        hasargs = True
        if w_descr is not None:
            w_result = space.get_and_call_function(w_descr, w_obj)
            w_args, w_kwargs = space.fixedview(w_result, 2)
        else:
            w_descr = space.lookup(w_obj, '__getnewargs__')
            if w_descr is not None:
                w_args = space.get_and_call_function(w_descr, w_obj)
            else:
                hasargs = False
                w_args = space.newtuple([])
            w_kwargs = space.w_None
        w_getstate = space.lookup(w_obj, '__get_state__')
        if w_getstate is None:
            required = not hasargs and \
                       not space.isinstance_w(w_obj, space.w_list) and \
                       not space.isinstance_w(w_obj, space.w_dict)
            w_obj_type = space.type(w_obj)
            if required and w_obj_type.layout.typedef.variable_sized:
                raise oefmt(space.w_TypeError, "cannot pickle %N objects", w_obj_type)
        return reduce_2(space, w_obj, w_proto, w_args, w_kwargs)
    return reduce_1(space, w_obj, w_proto)

@unwrap_spec(proto=int)
def descr__reduce_ex__(space, w_obj, proto=0):
    w_st_reduce = space.newtext('__reduce__')
    w_reduce = space.findattr(w_obj, w_st_reduce)
    if w_reduce is not None:
        # Check if __reduce__ has been overridden:
        # "type(obj).__reduce__ is not object.__reduce__"
        w_cls_reduce = space.getattr(space.type(w_obj), w_st_reduce)
        w_obj_reduce = space.getattr(space.w_object, w_st_reduce)
        override = not space.is_w(w_cls_reduce, w_obj_reduce)
        if override:
            return space.call_function(w_reduce)
    return descr__reduce__(space, w_obj, proto)

def descr___format__(space, w_obj, w_format_spec):
    if space.isinstance_w(w_format_spec, space.w_unicode):
        w_as_str = space.call_function(space.w_unicode, w_obj)
    elif space.isinstance_w(w_format_spec, space.w_bytes):
        w_as_str = space.str(w_obj)
    else:
        raise oefmt(space.w_TypeError, "format_spec must be a string")
    if space.len_w(w_format_spec) > 0:
        raise oefmt(space.w_TypeError,
                    "non-empty format string passed to object.__format__")
    return space.format(w_as_str, w_format_spec)

def descr__eq__(space, w_self, w_other):
    if space.is_w(w_self, w_other):
        return space.w_True
    # Return NotImplemented instead of False, so if two objects are
    # compared, both get a chance at the comparison (issue #1393)
    return space.w_NotImplemented

def descr__ne__(space, w_self, w_other):
    # By default, __ne__() delegates to __eq__() and inverts the result,
    # unless the latter returns NotImplemented.
    w_eq = space.lookup(w_self, '__eq__')
    w_res = space.get_and_call_function(w_eq, w_self, w_other)
    if space.is_w(w_res, space.w_NotImplemented):
        return w_res
    return space.not_(w_res)

def descr_richcompare(space, w_self, w_other):
    return space.w_NotImplemented

def descr__dir__(space, w_obj):
    from pypy.objspace.std.util import _objectdir
    return space.call_function(space.w_list, _objectdir(space, w_obj))

W_ObjectObject.typedef = TypeDef("object",
    __doc__ = "The most base type",
    __new__ = interp2app(descr__new__),
    __subclasshook__ = interp2app(descr___subclasshook__, as_classmethod=True),

    # these are actually implemented in pypy.objspace.descroperation
    __getattribute__ = interp2app(Object.descr__getattribute__.im_func),
    __setattr__ = interp2app(Object.descr__setattr__.im_func),
    __delattr__ = interp2app(Object.descr__delattr__.im_func),

    __init__ = interp2app(descr__init__),
    __class__ = GetSetProperty(descr_get___class__, descr_set___class__),
    __repr__ = interp2app(descr__repr__),
    __str__ = interp2app(descr__str__),
    __hash__ = interp2app(default_identity_hash),
    __reduce__ = interp2app(descr__reduce__),
    __reduce_ex__ = interp2app(descr__reduce_ex__),
    __format__ = interp2app(descr___format__),
    __dir__ = interp2app(descr__dir__),

    __eq__ = interp2app(descr__eq__),
    __ne__ = interp2app(descr__ne__),
    __le__ = interp2app(descr_richcompare),
    __lt__ = interp2app(descr_richcompare),
    __ge__ = interp2app(descr_richcompare),
    __gt__ = interp2app(descr_richcompare),
)
