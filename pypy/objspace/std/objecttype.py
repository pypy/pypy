from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_ObjectType(W_TypeObject):
    """The single instance of W_ObjectType is what the user sees as
    '__builtin__.object'."""

    typename = 'object'
    staticbases = ()

    # all multimethods that we want to be visible as object.__xxx__
    # should be defined here.

    object_getattr = StdObjSpace.getattr
    object_setattr = StdObjSpace.setattr
    object_delattr = StdObjSpace.delattr
    object_type    = StdObjSpace.type
    object_repr    = StdObjSpace.repr
    object_str     = StdObjSpace.str
    object_hash    = StdObjSpace.hash


# XXX we'll worry about the __new__/__init__ distinction later
def new__ObjectType_ANY_ANY(space, w_objecttype, w_args, w_kwds):
    # XXX 2.2 behavior: ignoring all arguments
    from objectobject import W_ObjectObject
    return W_ObjectObject(space)


### The following implementations are registered to the
#   W_ObjectType.object_xxx multimethods, which binds them to
#   the 'object' type. They are however implemented on W_ANY, not
#   on W_ObjectObject, so that they can receive any wrapped object
#   unmodified (instead of an object converted to W_ObjectObject).
#   The difference between these implementations and the ones
#   defined in default.py lies in the fact that the latter are
#   not registered against any particular type, which makes them
#   invisible to application-level Python, whereas the functions
#   below appear as object.__xxx__.


# give objects some default attributes and a default way to complain
# about missing attributes

def object_getattr__ANY_ANY(space, w_obj, w_attr):
    # XXX build a nicer error message along these lines:
    #w_type = space.type(w_obj)
    #w_typename = space.getattr(w_type, space.wrap('__name__'))
    #...

    w_type = space.type(w_obj)
    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
        return w_type

    # 1) look for descriptor
    # 2) if data descriptor, call it
    # 3) check __dict__
    # 4) if present, return that
    # 5) if descriptor found in 2), call that
    # 6) raise AttrbuteError

    w_descr = None

    from typeobject import W_TypeObject
    if isinstance(w_type, W_TypeObject):  # XXX must always be true at some point
        try:
            w_descr = w_type.lookup(w_attr)
        except KeyError:
            pass
        else:
            if space.is_data_descr(w_descr):
                return space.get(w_descr, w_obj, w_type) # XXX 3rd arg is wrong
    
    try:
        w_dict = space.getdict(w_obj)
    except OperationError, e:
        if not e.match(space, space.w_TypeError): # 'unsupported type for getdict'
            raise
    else:
        if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
            return w_dict
        try:
            w_value = space.getitem(w_dict, w_attr)
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
        else:
            return w_value  # got a value from 'obj.__dict__[attr]'

    if w_descr is not None:
        return space.get(w_descr, w_obj, w_type)
        
    raise OperationError(space.w_AttributeError, w_attr)


# set attributes, complaining about read-only ones --
# a more declarative way to define attributes would be welcome

def object_setattr__ANY_ANY_ANY(space, w_obj, w_attr, w_value):

    # 1) look for descriptor
    # 2) if data descriptor, call it
    # 3) try to set item in __dict__

    w_type = space.type(w_obj)
    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
        raise OperationError(space.w_AttributeError,
                             space.wrap("read-only attribute"))
    if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
        raise OperationError(space.w_AttributeError,
                             space.wrap("read-only attribute"))

    from typeobject import W_TypeObject
    if isinstance(w_type, W_TypeObject):
        try:
            w_descr = w_type.lookup(w_attr)
        except KeyError:
            pass
        else:
            if space.is_data_descr(w_descr):
                return space.set(w_descr, w_obj, w_value)
    
    try:
        w_dict = space.getdict(w_obj)
    except OperationError, e:
        if not e.match(space, space.w_TypeError): # "unsupported type for getdict"
            raise
        raise OperationError(space.w_AttributeError, w_attr)
    else:
        space.setitem(w_dict, w_attr, w_value)
            

def object_delattr__ANY_ANY(space, w_obj, w_attr):
    w_type = space.type(w_obj)
    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
        raise OperationError(space.w_AttributeError,
                             space.wrap("read-only attribute"))
    if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
        raise OperationError(space.w_AttributeError,
                             space.wrap("read-only attribute"))

    from typeobject import W_TypeObject
    if isinstance(w_type, W_TypeObject):
        try:
            w_descr = w_type.lookup(w_attr)
        except KeyError:
            pass
        else:
            #space.type(w_descr).lookup(space.wrap('__delete__'))
            if space.is_data_descr(w_descr):
                return space.delete(w_descr, w_obj)
    
    try:
        w_dict = space.getdict(w_obj)
    except OperationError, e:
        if not e.match(space, space.w_TypeError): # "unsupported type for getdict"
            raise
        raise OperationError(space.w_AttributeError, w_attr)
    else:
        try:
            space.delitem(w_dict, w_attr)
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
            raise OperationError(space.w_AttributeError, w_attr)

    raise OperationError(space.w_AttributeError, w_attr)


# static types

def object_type__ANY(space, w_obj):
    if w_obj.statictype is None:
        # XXX remove me, temporary
        return space.wrap(space.unwrap(w_obj).__class__)
    else:
        w_type = space.get_typeinstance(w_obj.statictype)
        return w_type


# repr(), str(), hash()

def object_repr__ANY(space, w_obj):
    return space.wrap('<%s object at %s>'%(
        space.type(w_obj).typename, space.unwrap(space.id(w_obj))))

def object_str__ANY(space, w_obj):
    return space.repr(w_obj)

def object_hash__ANY(space, w_obj):
    return space.id(w_obj)


register_all(vars(), W_ObjectType)
