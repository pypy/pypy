"""
Reviewed 03-06-22
"""
from __future__ import nested_scopes
from pypy.objspace.std.objspace import *
import typeobject, objecttype
from typeobject import W_TypeObject

class W_UserType(W_TypeObject):
    """Instances of this class are user-defined Python type objects.
    All user-defined types are instances of the present class.
    Builtin-in types, on the other hand, each have their own W_XxxType
    class."""

    # 'typename' is an instance property here

    def __init__(w_self, space, w_name, w_bases, w_dict):
        w_self.typename = space.unwrap(w_name)
        W_TypeObject.__init__(w_self, space)
        w_self.w_name   = w_name
        w_self.w_bases  = w_bases
        w_self.w_dict   = w_dict

    def __repr__(self):
        return '<usertype %s>'%(self.space.unwrap(self.w_name),)

    def getbases(w_self):
        bases = w_self.space.unpackiterable(w_self.w_bases)
        if bases:
            return bases
        else:
            return W_TypeObject.getbases(w_self)   # defaults to (w_object,)

    def lookup_exactly_here(w_self, w_key):
        space = w_self.space
        try:
            w_value = space.getitem(w_self.w_dict, w_key)
        except OperationError, e:
            # catch KeyErrors and turn them into KeyErrors (real ones!)
            if not e.match(space, space.w_KeyError):
                raise
            raise KeyError
        return w_value

# XXX we'll worry about the __new__/__init__ distinction later
# XXX NOTE: currently (03-06-21) user-object can only sublass
#   types which register an implementation for 'new' -- currently
#   this means that e.g. subclassing list or str works, subclassing
#   int or float does not -- this is not a bug fixable in userobject
#   (perhaps in the object-space, perhaps in each builtin type...?)
#   but we're documenting it here as there seems no better place!!!
#   The problem is actually that, currently, several types such as
#   int and float just cannot be CALLED -- this needs to be fixed soon.
def new__UserType_ANY_ANY(space, w_usertype, w_args, w_kwds):
    from userobject import W_UserObject
    newobj = W_UserObject(space, w_usertype, w_args, w_kwds)
    try:
        init = space.getattr(newobj, space.wrap('__init__'))
    except OperationError, err:
        if not err.match(space, space.w_AttributeError):
            raise
    else:
        space.call(init, w_args, w_kwds)
    return newobj

def getdict__UserType(space, w_usertype):
    return w_usertype.w_dict

def repr__UserType(space, w_usertype):
    return space.wrap("<class '%s'>" % w_usertype.typename)
    
register_all(vars())
