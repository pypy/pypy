from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.typedef import GetSetProperty, default_identity_hash
from pypy.interpreter import gateway
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.objspace.descroperation import Object
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.register_all import register_all


def descr__repr__(space, w_obj):
    w = space.wrap
    w_type = space.type(w_obj)
    classname = w_type.getname(space)
    w_module = w_type.lookup("__module__")
    if w_module is not None:
        try:
            modulename = space.str_w(w_module)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
        else:
            classname = '%s.%s' % (modulename, classname)
    return w_obj.getrepr(space, '%s object' % (classname,))

def descr__str__(space, w_obj):
    return space.repr(w_obj)

def descr__class__(space, w_obj):
    return space.type(w_obj)

def descr_set___class__(space, w_obj, w_newcls):
    from pypy.objspace.std.typeobject import W_TypeObject
    if not isinstance(w_newcls, W_TypeObject):
        raise operationerrfmt(space.w_TypeError,
                              "__class__ must be set to new-style class, not '%s' object",
                              space.type(w_newcls).getname(space))
    if not w_newcls.is_heaptype():
        raise OperationError(space.w_TypeError,
                             space.wrap("__class__ assignment: only for heap types"))
    w_oldcls = space.type(w_obj)
    # XXX taint space should raise a TaintError here if w_oldcls is tainted
    assert isinstance(w_oldcls, W_TypeObject)
    if w_oldcls.get_full_instance_layout() == w_newcls.get_full_instance_layout():
        w_obj.setclass(space, w_newcls)
        if space.config.objspace.std.trackcomparebyidentity:
            if not w_oldcls.overrides_hash_eq_or_cmp and not w_newcls.compares_by_identity():
                space.bump_compares_by_identity_version()
    else:
        raise operationerrfmt(space.w_TypeError,
                              "__class__ assignment: '%s' object layout differs from '%s'",
                              w_oldcls.getname(space), w_newcls.getname(space))


app = gateway.applevel("""
def _abstract_method_error(typ):
    methods = ", ".join(sorted(typ.__abstractmethods__))
    err = "Can't instantiate abstract class %s with abstract methods %s"
    raise TypeError(err % (typ.__name__, methods))
""")
_abstract_method_error = app.interphook("_abstract_method_error")


def descr__new__(space, w_type, __args__):
    from pypy.objspace.std.objectobject import W_ObjectObject
    from pypy.objspace.std.typetype import _precheck_for_new
    # don't allow arguments if the default object.__init__() is about
    # to be called
    w_type = _precheck_for_new(space, w_type)
    w_parentinit, w_ignored = w_type.lookup_where('__init__')
    if w_parentinit is space.w_object:
        try:
            __args__.fixedunpack(0)
        except ValueError:
            raise OperationError(space.w_TypeError,
                                 space.wrap("default __new__ takes "
                                            "no parameters"))
    if w_type.is_abstract():
        _abstract_method_error(space, w_type)
    w_obj = space.allocate_instance(W_ObjectObject, w_type)
    return w_obj

def descr__init__(space, w_obj, __args__):
    # don't allow arguments unless __new__ is overridden
    w_type = space.type(w_obj)
    w_parent_new, _ = w_type.lookup_where('__new__')
    if w_parent_new is space.w_object:
        try:
            __args__.fixedunpack(0)
        except ValueError:
            raise OperationError(space.w_TypeError,
                space.wrap("object.__init__() takes no parameters"))


@gateway.unwrap_spec(proto=int)
def descr__reduce__(space, w_obj, proto=0):
    if proto >= 2:
        return reduce_2(space, w_obj)
    w_proto = space.wrap(proto)
    return reduce_1(space, w_obj, w_proto)

@gateway.unwrap_spec(proto=int)
def descr__reduce_ex__(space, w_obj, proto=0):
    w_st_reduce = space.wrap('__reduce__')
    w_reduce = space.findattr(w_obj, w_st_reduce)
    if w_reduce is not None:
        w_cls = space.getattr(w_obj, space.wrap('__class__'))
        w_cls_reduce_meth = space.getattr(w_cls, w_st_reduce)
        w_cls_reduce = space.getattr(w_cls_reduce_meth, space.wrap('im_func'))
        w_objtype = space.w_object
        w_obj_dict = space.getattr(w_objtype, space.wrap('__dict__'))
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
        msg = "format_spec must be a string"
        raise OperationError(space.w_TypeError, space.wrap(msg))
    if space.len_w(w_format_spec) > 0:
        space.warn(
            ("object.__format__ with a non-empty format string is "
                "deprecated"),
            space.w_PendingDeprecationWarning
        )
    return space.format(w_as_str, w_format_spec)

def descr___subclasshook__(space, __args__):
    return space.w_NotImplemented


app = gateway.applevel(r'''
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
            raise TypeError, "__getnewargs__ should return a tuple"

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

    if isinstance(obj, list):
        listitems = iter(obj)
    else:
        listitems = None

    if isinstance(obj, dict):
        dictitems = obj.iteritems()
    else:
        dictitems = None

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
        raise TypeError, "copy_reg._slotnames didn't return a list or None"
    return slotnames
''', filename=__file__)

reduce_1 = app.interphook('reduce_1')
reduce_2 = app.interphook('reduce_2')

# ____________________________________________________________

object_typedef = StdTypeDef("object",
    __getattribute__ = gateway.interp2app(Object.descr__getattribute__.im_func),
    __setattr__ = gateway.interp2app(Object.descr__setattr__.im_func),
    __delattr__ = gateway.interp2app(Object.descr__delattr__.im_func),
    __str__ = gateway.interp2app(descr__str__),
    __repr__ = gateway.interp2app(descr__repr__),
    __class__ = GetSetProperty(descr__class__, descr_set___class__),
    __doc__ = '''The most base type''',
    __new__ = gateway.interp2app(descr__new__),
    __hash__ = gateway.interp2app(default_identity_hash),
    __reduce_ex__ = gateway.interp2app(descr__reduce_ex__),
    __reduce__ = gateway.interp2app(descr__reduce__),
    __format__ = gateway.interp2app(descr___format__),
    __subclasshook__ = gateway.interp2app(descr___subclasshook__,
                                          as_classmethod=True),
    __init__ = gateway.interp2app(descr__init__),
    )
