from pypy.interpreter.error import OperationError
from pypy.objspace.descroperation import Object
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.objspace import StdObjSpace
from pypy.tool.rarithmetic import r_uint


def descr__repr__(space, w_obj):
    w = space.wrap
    classname = space.str_w(space.getattr(space.type(w_obj), w("__name__")))
    id = space.int_w(space.id(w_obj))# xxx ids could be long
    id = r_uint(id) # XXX what about sizeof(void*) > sizeof(long) !!
    return w("<%s object at 0x%x>" % (classname, id))

def descr__str__(space, w_obj):
    return space.repr(w_obj)

def descr__class__(space, w_obj):
    return space.type(w_obj)

def descr__new__(space, w_type, __args__):
    from pypy.objspace.std.objectobject import W_ObjectObject
    # don't allow arguments if the default object.__init__() is about
    # to be called
    w_parentinit, w_ignored = w_type.lookup_where('__init__')
    if w_parentinit is space.w_object:
        try:
            __args__.fixedunpack(0)
        except ValueError:
            raise OperationError(space.w_TypeError,
                                 space.wrap("default __new__ takes "
                                            "no parameters"))
    w_obj = space.allocate_instance(W_ObjectObject, w_type)
    w_obj.__init__(space)
    return w_obj

def descr__hash__(space, w_obj):
    return space.id(w_obj)

def descr__init__(space, w_obj, __args__):
    pass

def descr__reduce_ex__(space, w_obj, proto=0):
    w_st_reduce = space.wrap('__reduce__')
    try: w_reduce = space.getattr(w_obj, w_st_reduce)
    except OperationError: pass
    else:
        w_cls = space.getattr(w_obj, space.wrap('__class__'))
        w_cls_reduce_meth = space.getattr(w_cls, w_st_reduce)
        w_cls_reduce = space.getattr(w_cls_reduce_meth, space.wrap('im_func'))
        w_objtype = space.w_object
        w_obj_dict = space.getattr(w_objtype, space.wrap('__dict__'))
        w_obj_reduce = space.getitem(w_obj_dict, w_st_reduce)
        override = space.is_true(space.ne(w_cls_reduce, w_obj_reduce))
        # print 'OVR', override, w_cls_reduce, w_obj_reduce
        if override:
            return space.call(w_reduce, space.newtuple([]))
    if proto >= 2:
        return reduce_2(space, w_obj)
    w_proto = space.wrap(proto)
    return reduce_1(space, w_obj, w_proto)

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
    __class__ = GetSetProperty(descr__class__),
    __new__ = newmethod(descr__new__,
                        unwrap_spec = [gateway.ObjSpace,gateway.W_Root,gateway.Arguments]),
    __hash__ = gateway.interp2app(descr__hash__),
    __reduce_ex__ = gateway.interp2app(descr__reduce_ex__,
                                  unwrap_spec=[gateway.ObjSpace,gateway.W_Root,int]),
    __reduce__ = gateway.interp2app(descr__reduce_ex__,
                                  unwrap_spec=[gateway.ObjSpace,gateway.W_Root,int]),
    __init__ = gateway.interp2app(descr__init__,
                                  unwrap_spec=[gateway.ObjSpace,gateway.W_Root,gateway.Arguments]),
    )
