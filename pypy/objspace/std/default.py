"""Default implementation for some operation."""

from pypy.objspace.std.objspace import *


# The default delegation mecanism is to allow any W_XxxObject class
# to be regarded as an instance of any of its parent classes.

def class_to_parent_classes(space, w_obj):
    converted = []
    W_Cls = w_obj.__class__
    while W_Cls is not W_Object:
        assert len(W_Cls.__bases__) == 1, (
            "multimethod call with non wrapped argument: %r" % w_obj)
        W_Cls, = W_Cls.__bases__
        converted.append((W_Cls, w_obj))
    return converted

class_to_parent_classes.priority = PRIORITY_PARENT_IMPL
StdObjSpace.delegate.register(class_to_parent_classes, Ellipsis)
# 'Ellipsis' should not be used in other calls to register()


# These are operations that must fall back to some default behavior,
# but that should not appear explicitly at application-level.
# There is no default object.__xxx__() method for these.


# 'eq' falls back to 'is'

def eq__ANY_ANY(space, w_a, w_b):
    return space.is_(w_a, w_b)

# 'ne' -> 'eq', 'le/gt/ge' -> 'lt'

def ne__ANY_ANY(space, w_a, w_b):
    return space.not_(space.eq(w_a, w_b))
def le__ANY_ANY(space, w_a, w_b):
    return space.not_(space.lt(w_b, w_a))
def gt__ANY_ANY(space, w_a, w_b):
    return space.lt(w_b, w_a)
def ge__ANY_ANY(space, w_a, w_b):
    return space.not_(space.lt(w_a, w_b))

# 'id' falls back to the address of the wrapper

def id__ANY(space, w_obj):
    import intobject
    return intobject.W_IntObject(space, id(w_obj))

# this 'not' implementation should be fine for most cases

def not__ANY(space, w_obj):
    return space.newbool(not space.is_true(w_obj))

# everything is True unless otherwise specified

def is_true__ANY(space, w_obj):
    return True

# in-place operators fall back to their non-in-place counterpart

for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    if _name.startswith('inplace_'):
        def default_inplace(space, w_1, w_2, baseop=_name[8:]):
            op = getattr(space, baseop)
            return op(w_1, w_2)
        getattr(StdObjSpace, _name).register(default_inplace, W_ANY, W_ANY)


# 'contains' falls back to iteration

def contains__ANY_ANY(space, w_iterable, w_lookfor):
    w_iter = space.iter(w_iterable)
    while 1:
        try:
            w_next = space.next(w_iter)
        except NoValue:
            return space.w_False
        if space.is_true(space.eq(w_next, w_lookfor)):
            return space.w_True

# '__get__(descr, inst, cls)' returns 'descr' by default

def get__ANY_ANY_ANY(space, w_descr, w_inst, w_cls):
    return w_descr

def issubtype__ANY_ANY(space, w_one, w_two):
    # XXX -- mwh
    return space.newbool(0)

register_all(vars())
