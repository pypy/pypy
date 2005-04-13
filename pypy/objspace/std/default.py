"""Default implementation for some operation."""

from pypy.objspace.std.objspace import *


# The following default implementations are used before delegation is tried.
# 'id' is normally the address of the wrapper.

def id__ANY(space, w_obj):
    #print 'id:', w_obj
    from pypy.objspace.std import intobject
    return intobject.W_IntObject(space, id(w_obj))

# __init__ should succeed if called internally as a multimethod

def init__ANY(space, w_obj, __args__):
    pass


# __nonzero__ falls back to __len__

##def is_true__ANY(space, w_obj):
##    w_descr = space.lookup(w_obj, '__len__')
##    if w_descr is None:
##        return True
##    else:
##        w_len = space.get_and_call_function(w_descr, w_obj)
##        return space.is_true(w_len)

### in-place operators fall back to their non-in-place counterpart

##for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
##    if _name.startswith('inplace_'):
##        def default_inplace(space, w_1, w_2, baseop=_name[8:]):
##            op = getattr(space, baseop)
##            return op(w_1, w_2)
##        getattr(StdObjSpace.MM, _name).register(default_inplace,
##                                                W_Object, W_ANY)

# '__get__(descr, inst, cls)' returns 'descr' by default

#def get__Object_ANY_ANY(space, w_descr, w_inst, w_cls):
#    return w_descr

#def is_data_descr__Object(space, w_descr):
#    return 0

# give objects some default attributes and a default way to complain
# about missing attributes

##def getattribute__Object_ANY(space, w_obj, w_attr):
##    # XXX build a nicer error message along these lines:
##    #w_type = space.type(w_obj)
##    #w_typename = space.getattr(w_type, space.wrap('__name__'))
##    #...

##    w_type = space.type(w_obj)
##    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
##        return w_type

##    # 1) look for descriptor
##    # 2) if data descriptor, call it
##    # 3) check __dict__
##    # 4) if present, return that
##    # 5) if descriptor found in 2), call that
##    # 6) raise AttrbuteError

##    w_descr = None

##    from typeobject import W_TypeObject
##    if isinstance(w_type, W_TypeObject):  # XXX must always be true at some point
##        try:
##            w_descr = w_type.lookup(w_attr)
##        except KeyError:
##            pass
##        else:
##            if space.is_data_descr(w_descr):
##                return space.get(w_descr, w_obj, w_type) # XXX 3rd arg is wrong
    
##    try:
##        w_dict = space.getdict(w_obj)
##    except OperationError, e:
##        if not e.match(space, space.w_TypeError): # 'unsupported type for getdict'
##            raise
##    else:
##        if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
##            return w_dict
##        try:
##            w_value = space.getitem(w_dict, w_attr)
##        except OperationError, e:
##            if not e.match(space, space.w_KeyError):
##                raise
##        else:
##            return w_value  # got a value from 'obj.__dict__[attr]'

##    if w_descr is not None:
##        return space.get(w_descr, w_obj, w_type)
        
##    raise OperationError(space.w_AttributeError, w_attr)


# set attributes, complaining about read-only ones --
# a more declarative way to define attributes would be welcome

##def setattr__Object_ANY_ANY(space, w_obj, w_attr, w_value):

##    # 1) look for descriptor
##    # 2) if data descriptor, call it
##    # 3) try to set item in __dict__

##    w_type = space.type(w_obj)
##    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
##        raise OperationError(space.w_AttributeError,
##                             space.wrap("read-only attribute"))
##    if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
##        raise OperationError(space.w_AttributeError,
##                             space.wrap("read-only attribute"))

##    from typeobject import W_TypeObject
##    if isinstance(w_type, W_TypeObject):
##        try:
##            w_descr = w_type.lookup(w_attr)
##        except KeyError:
##            pass
##        else:
##            if space.is_data_descr(w_descr):
##                return space.set(w_descr, w_obj, w_value)
    
##    try:
##        w_dict = space.getdict(w_obj)
##    except OperationError, e:
##        if not e.match(space, space.w_TypeError): # "unsupported type for getdict"
##            raise
##        raise OperationError(space.w_AttributeError, w_attr)
##    else:
##        space.setitem(w_dict, w_attr, w_value)
            

##def delattr__Object_ANY(space, w_obj, w_attr):
##    w_type = space.type(w_obj)
##    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
##        raise OperationError(space.w_AttributeError,
##                             space.wrap("read-only attribute"))
##    if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
##        raise OperationError(space.w_AttributeError,
##                             space.wrap("read-only attribute"))

##    from typeobject import W_TypeObject
##    if isinstance(w_type, W_TypeObject):
##        try:
##            w_descr = w_type.lookup(w_attr)
##        except KeyError:
##            pass
##        else:
##            #space.type(w_descr).lookup(space.wrap('__delete__'))
##            if space.is_data_descr(w_descr):
##                return space.delete(w_descr, w_obj)
    
##    try:
##        w_dict = space.getdict(w_obj)
##    except OperationError, e:
##        if not e.match(space, space.w_TypeError): # "unsupported type for getdict"
##            raise
##        raise OperationError(space.w_AttributeError, w_attr)
##    else:
##        try:
##            space.delitem(w_dict, w_attr)
##        except OperationError, e:
##            if not e.match(space, space.w_KeyError):
##                raise
##            raise OperationError(space.w_AttributeError, w_attr)

# static types

##def type__Object(space, w_obj):
##    if w_obj.statictype is None:
##        # XXX remove me, temporary
##        return space.wrap(space.unwrap(w_obj).__class__)
##    else:
##        w_type = space.get_typeinstance(w_obj.statictype)
##        return w_type

# repr(), str(), hash()

##def repr__Object(space, w_obj):
##    return space.wrap('<%s object at %s>'%(
##        space.type(w_obj).typename, space.unwrap(space.id(w_obj))))

##def str__Object(space, w_obj):
##    return space.repr(w_obj)

##def hash__ANY(space, w_obj):
##    return space.id(w_obj)


# The following operations are fall-backs if we really cannot find
# anything else even with delegation.
# 'eq' falls back to 'is'

##def eq__ANY_ANY(space, w_a, w_b):
##    return space.is_(w_a, w_b)

# 'contains' falls back to iteration.

##def contains__ANY_ANY(space, w_iterable, w_lookfor):
##    w_iter = space.iter(w_iterable)
##    while 1:
##        try:
##            w_next = space.next(w_iter)
##        except OperationError, e:
##            if not e.match(space, space.w_StopIteration):
##                raise
##            return space.w_False
##        if space.is_true(space.eq(w_next, w_lookfor)):
##            return space.w_True

# ugh

def typed_unwrap_error_msg(space, expected, w_obj):
    w = space.wrap
    type_name = space.str_w(space.getattr(space.type(w_obj),w("__name__")))
    return w("expected %s, got %s object" % (expected, type_name))

def int_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "integer", w_obj))

def str_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "string", w_obj))

def float_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "float", w_obj))

def uint_w__ANY(space,w_obj):
    raise OperationError(space.w_TypeError,
                         typed_unwrap_error_msg(space, "integer", w_obj))

register_all(vars())
