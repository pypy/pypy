"""
Reviewed 03-06-22
This object implements "instances of custom types" completely and
accurately.  We have selectively tested (in the testfile) a key
selection of features: setting and getting attributes and the
correct working of inheritance from both builtin and user types
as well as of normal and special attributes.
"""
from pypy.objspace.std.objspace import *
from usertype import W_UserType
import typeobject


class W_UserObject(W_Object):
    """Instances of this class are what the user sees as instances of custom
    types.  All such instances are implemented by the present W_UserObject
    class."""
    statictype = W_UserType

    def __init__(w_self, space, w_type, w_args, w_kwds):
        # the restriction that a single built-in type is allowed among the
        # bases is specific to our W_UserObject implementation of user
        # objects, and should thus not be enforced in W_UserType.
        # Note: w_type may be any object, not necessarily a W_UserType
        # (in case 'type' is subclassed).
        
        # create an instance of the parent built-in type
        w_builtintype = getsinglebuiltintype(space, w_type)
        w_self.w_embedded = space.call(w_builtintype, w_args, w_kwds)
        w_self.w_type = w_type
        w_self.w_dict = space.newdict([])


registerimplementation(W_UserObject)


def getsinglebuiltintype(space, w_type):
    "Return the (asserted unique) built-in type that w_type inherits from."
    mostspecialized = space.w_object
    mro = space.getattr(w_type, space.wrap('__mro__'))
    mro = space.unpacktuple(mro)
    mro.reverse()
    for w_base in mro:
        if not isinstance(w_base, W_UserType):
            if not space.is_true(space.issubtype(w_base, mostspecialized)):
                raise OperationError(space.w_TypeError,
                                     space.wrap("instance layout conflicts in "
                                                "multiple inheritance"))
            mostspecialized = w_base
    return mostspecialized


# W_UserObject-to-the-parent-builtin-type delegation
# So far this is the only delegation that produces a result
# of a variable type.
def delegate__User(space, w_userobj):
    return w_userobj.w_embedded
delegate__User.priority = PRIORITY_PARENT_TYPE


def type__User(space, w_userobj):
    return w_userobj.w_type

def getdict__User(space, w_userobj):
    # XXX check getdict() of the base built-in implementation
    return w_userobj.w_dict


# register an implementation for all multimethods that define special names
def user_specialmethod(space, *args_w):
    # args_w is in the standard multimethod order
    # we need it in the Python-friendly order (i.e. swapped for __rxxx__)
    args_w = list(args_w)
    w_userobj = args_w.pop(g_bound_position)
    w_args = space.newtuple(args_w)
    w_key = space.wrap(g_method_name)
    mro = space.getattr(w_userobj.w_type, space.wrap('__mro__'))
    mro = space.unpacktuple(mro)
    for w_base in mro:
        if not isinstance(w_base, W_UserType):
            continue
        try:
            w_function = w_base.lookup_exactly_here(w_key)
        except KeyError:
            continue
        w_method = space.get(w_function, w_userobj, w_base)
        w_result = space.call(w_method, w_args, space.newdict([]))
        # XXX hack to accept real Nones from operations with no return value
        if w_result is None:
            return space.w_None
        elif space.is_true(space.is_(w_result, space.w_NotImplemented)):
            raise FailedToImplement
        else:
            return w_result
    raise FailedToImplement

import new
for multimethod in typeobject.hack_out_multimethods(StdObjSpace):
    for i in range(len(multimethod.specialnames)):
        # a hack to avoid nested scopes is to give the function
        # a custom globals dictionary

        g = {'W_UserType'       : W_UserType,
             'FailedToImplement': FailedToImplement,
             '__builtins__'     : __builtins__,
             'g_method_name'    : multimethod.specialnames[i],
             'g_bound_position' : i}
        f = new.function(user_specialmethod.func_code, g,
                         'user_%s' % multimethod.specialnames[i])

        signature = [W_ANY] * multimethod.arity
        signature[i] = W_UserObject
        multimethod.register(f, *signature)


register_all(vars())
