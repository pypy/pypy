from pypy.objspace.std.objspace import *


class W_ObjectObject(W_Object):
    """Instances of this class are what the user can directly see with an
    'object()' call.  Internally, they play the important role of ,,,,
    types.  All such instances are implemented by the present W_UserObject
    class."""
    #statictype = W_ObjectType    (hacked into place below)


import objecttype
W_ObjectObject.statictype = objecttype.W_ObjectType
registerimplementation(W_ObjectObject)


# default global delegation from W_ANY to W_ObjectObject
W_ANY.delegate_once[W_ObjectObject] = None  # None means identity function


# these are the globally-defined operations that must appear as object.__xxx__.
# See also default.py.


# give objects some default attributes and a default way to complain
# about missing attributes

def object_getattr(space, w_obj, w_attr):
    # XXX build a nicer error message along these lines:
    #w_type = space.type(w_obj)
    #w_typename = space.getattr(w_type, space.wrap('__name__'))
    #...

    w_type = space.type(w_obj)
    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
        return w_type

    try:
        w_dict = space.getdict(w_obj)
    except OperationError, e:
        # catch TypeError("unsupported type for getdict")
        if not e.match(space, space.w_TypeError):
            raise
    else:
        if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
            return w_dict
        try:
            w_value = space.getitem(w_dict, w_attr)
        except OperationError, e:
            # catch KeyErrors
            if not e.match(space, space.w_KeyError):
                raise
        else:
            return w_value  # got a value from 'obj.__dict__[attr]'

    # XXX implement lookup as a multimethod?
    from typeobject import W_TypeObject
    if isinstance(w_type, W_TypeObject):  # XXX must always be true at some point
        try:
            w_value = w_type.lookup(w_attr)
        except KeyError:
            pass
        else:
            return space.get(w_value, w_obj, w_type)
        
    raise OperationError(space.w_AttributeError, w_attr)

StdObjSpace.getattr.register(object_getattr, W_ObjectObject, W_ANY)


# set attributes, complaining about read-only ones --
# a more declarative way to define attributes would be welcome

def object_setattr(space, w_obj, w_attr, w_value):
    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
        raise OperationError(space.w_AttributeError,
                             space.wrap("read-only attribute"))
    try:
        w_dict = space.getdict(w_obj)
    except OperationError, e:
        # catch TypeError("unsupported type for getdict")
        if not e.match(space, space.w_TypeError):
            raise
    else:
        if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
            raise OperationError(space.w_AttributeError,
                                 space.wrap("read-only attribute"))
        space.setitem(w_dict, w_attr, w_value)
        return
    
    raise OperationError(space.w_AttributeError, w_attr)

StdObjSpace.setattr.register(object_setattr, W_ObjectObject, W_ANY, W_ANY)


def object_delattr(space, w_obj, w_attr):
    if space.is_true(space.eq(w_attr, space.wrap('__class__'))):
        raise OperationError(space.w_AttributeError,
                             space.wrap("read-only attribute"))
    try:
        w_dict = space.getdict(w_obj)
    except OperationError, e:
        # catch TypeError("unsupported type for getdict")
        if not e.match(space, space.w_TypeError):
            raise
    else:
        if space.is_true(space.eq(w_attr, space.wrap('__dict__'))):
            raise OperationError(space.w_AttributeError,
                                 space.wrap("read-only attribute"))
        space.delitem(w_dict, w_attr)
        return
    
    raise OperationError(space.w_AttributeError, w_attr)

StdObjSpace.delattr.register(object_delattr, W_ObjectObject, W_ANY)


# static types

def object_type(space, w_obj):
    if w_obj.statictype is None:
        # XXX remove me, temporary
        return space.wrap(space.unwrap(w_obj).__class__)
    else:
        w_type = space.get_typeinstance(w_obj.statictype)
        return w_type

StdObjSpace.type.register(object_type, W_ObjectObject)


# repr()

def object_repr(space, w_obj):
    return space.wrap('<%s object at %s>'%(
        space.type(w_obj).typename, space.unwrap(space.id(w_obj))))

StdObjSpace.repr.register(object_repr, W_ObjectObject)


# str() defaults to repr() and hash() defaults to id().
# these should really be defined in default.py, but in CPython they
# are visible in the 'object' class.

def object_str(space, w_obj):
    return space.repr(w_obj)

StdObjSpace.str.register(object_str, W_ObjectObject)

def object_hash(space, w_obj):
    return space.id(w_obj)

StdObjSpace.hash.register(object_hash, W_ObjectObject)
