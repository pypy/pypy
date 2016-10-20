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
    import copy_reg
    return copy_reg._reduce_ex(obj, proto)

def reduce_2(obj):
    cls = obj.__class__

    try:
        getnewargs = obj.__getnewargs__
    except AttributeError:
        args = ()
    else:
        args = getnewargs()
        if not isinstance(args, tuple):
            raise TypeError("__getnewargs__ should return a tuple")

    try:
        getstate = obj.__getstate__
    except AttributeError:
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

    listitems = iter(obj) if isinstance(obj, list) else None
    dictitems = obj.iteritems() if isinstance(obj, dict) else None

    import copy_reg
    newobj = copy_reg.__newobj__

    args2 = (cls,) + args
    return newobj, args2, state, listitems, dictitems

def slotnames(cls):
    if not isinstance(cls, type):
        return None

    try:
        return cls.__dict__["__slotnames__"]
    except KeyError:
        pass

    import copy_reg
    slotnames = copy_reg._slotnames(cls)
    if not isinstance(slotnames, list) and slotnames is not None:
        raise TypeError("copy_reg._slotnames didn't return a list or None")
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

    # don't allow arguments if the default object.__init__() is about
    # to be called
    if _excess_args(__args__):
        w_parent_init, _ = space.lookup_in_type_where(w_type, '__init__')
        if w_parent_init is space.w_object:
            raise oefmt(space.w_TypeError,
                        "object() takes no parameters")
    if w_type.is_abstract():
        _abstract_method_error(space, w_type)
    return space.allocate_instance(W_ObjectObject, w_type)


def descr___subclasshook__(space, __args__):
    return space.w_NotImplemented


def descr__init__(space, w_obj, __args__):
    # don't allow arguments unless __new__ is overridden
    if _excess_args(__args__):
        w_type = space.type(w_obj)
        w_parent_new, _ = space.lookup_in_type_where(w_type, '__new__')
        if w_parent_new is space.w_object:
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
    w_type = space.type(w_obj)
    classname = w_type.name
    if w_type.is_heaptype():
        w_module = w_type.lookup("__module__")
        if w_module is not None:
            try:
                modulename = space.str_w(w_module)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise
            else:
                classname = '%s.%s' % (modulename, classname)
    return w_obj.getrepr(space, '%s object' % (classname,))


def descr__str__(space, w_obj):
    w_type = space.type(w_obj)
    w_impl = w_type.lookup("__repr__")
    if w_impl is None:
        # can it really occur?
        raise oefmt(space.w_TypeError, "operand does not support unary str")
    return space.get_and_call_function(w_impl, w_obj)


@unwrap_spec(proto=int)
def descr__reduce__(space, w_obj, proto=0):
    if proto >= 2:
        return reduce_2(space, w_obj)
    w_proto = space.newint(proto)
    return reduce_1(space, w_obj, w_proto)

@unwrap_spec(proto=int)
def descr__reduce_ex__(space, w_obj, proto=0):
    w_st_reduce = space.newtext('__reduce__')
    w_reduce = space.findattr(w_obj, w_st_reduce)
    if w_reduce is not None:
        w_cls = space.getattr(w_obj, space.newtext('__class__'))
        w_cls_reduce_meth = space.getattr(w_cls, w_st_reduce)
        try:
            w_cls_reduce = space.getattr(w_cls_reduce_meth, space.newtext('im_func'))
        except OperationError as e:
            # i.e. PyCFunction from cpyext
            if not e.match(space, space.w_AttributeError):
                raise
            w_cls_reduce = space.w_None
        w_objtype = space.w_object
        w_obj_dict = space.getattr(w_objtype, space.newtext('__dict__'))
        w_obj_reduce = space.getitem(w_obj_dict, w_st_reduce)
        override = not space.is_w(w_cls_reduce, w_obj_reduce)
        # print 'OVR', override, w_cls_reduce, w_obj_reduce
        if override:
            return space.call(w_reduce, space.newtuple([]))
    return descr__reduce__(space, w_obj, proto)

def descr___format__(space, w_obj, w_format_spec):
    if space.isinstance_w(w_format_spec, space.w_unicode):
        w_as_str = space.call_function(space.w_unicode, w_obj)
    elif space.isinstance_w(w_format_spec, space.w_str):
        w_as_str = space.str(w_obj)
    else:
        raise oefmt(space.w_TypeError, "format_spec must be a string")
    if space.len_w(w_format_spec) > 0:
        msg = "object.__format__ with a non-empty format string is deprecated"
        space.warn(space.newtext(msg), space.w_PendingDeprecationWarning)
    return space.format(w_as_str, w_format_spec)


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
)
