"""Default implementation for some operation."""

from pypy.objspace.std.objspace import *


# 'eq' and 'ne' fall back to 'is'

def default_eq(space, w_a, w_b):
    return space.is_(w_a, w_b)

StdObjSpace.eq.register(default_eq, W_ANY, W_ANY)

def default_ne(space, w_a, w_b):
    return space.not_(space.is_(w_a, w_b))

StdObjSpace.ne.register(default_ne, W_ANY, W_ANY)


# 'id' falls back to the address of the wrapper

def default_id(space, w_obj):
    import intobject
    return intobject.W_IntObject(space, id(w_obj))

StdObjSpace.id.register(default_id, W_ANY)


# this 'not' implementation should be fine for most cases

def default_not(space, w_obj):
    return space.newbool(not space.is_true(w_obj))

StdObjSpace.not_.register(default_not, W_ANY)


# everything is True unless otherwise specified

def default_is_true(space, w_obj):
    return True

StdObjSpace.is_true.register(default_is_true, W_ANY)


# give objects some default attributes and a default way to complain
# about missing attributes

def default_getattr(space, w_obj, w_attr):
    # XXX build a nicer error message along these lines:
    #w_type = space.type(w_obj)
    #w_typename = space.getattr(w_type, space.wrap('__name__'))
    #...
    
    # XXX as long as don't have types...
    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
        return space.wrap(space.unwrap(w_obj).__class__)

    raise OperationError(space.w_AttributeError, w_attr)

StdObjSpace.getattr.register(default_getattr, W_ANY, W_ANY)

def default_setattr(space, w_obj, w_attr, w_value):
    raise OperationError(space.w_AttributeError, w_attr)

StdObjSpace.setattr.register(default_setattr, W_ANY, W_ANY, W_ANY)

def default_delattr(space, w_obj, w_attr, w_value):
    raise OperationError(space.w_AttributeError, w_attr)

StdObjSpace.delattr.register(default_delattr, W_ANY, W_ANY)


# in-place operators fall back to their non-in-place counterpart

for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    if _name.startswith('inplace_'):
        def default_inplace(space, w_1, w_2, baseop=_name[8:]):
            op = getattr(space, baseop)
            return op(w_1, w_2)
        getattr(StdObjSpace, _name).register(default_inplace, W_ANY, W_ANY)


# 'contains' falls back to iteration

def default_contains(space, w_iterable, w_lookfor):
    w_iter = space.iter(w_iterable)
    while 1:
        try:
            w_next = space.next(w_iter)
        except NoValue:
            return space.w_False
        if space.is_true(space.eq(w_next, w_lookfor)):
            return space.w_True

StdObjSpace.contains.register(default_contains, W_ANY, W_ANY)
