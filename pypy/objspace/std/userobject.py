from pypy.objspace.std.objspace import *
from usertype import W_UserType
import typeobject


class W_UserObject(W_Object):
    """Instances of this class are what the user sees as instances of custom
    types.  All such instances are implemented by the present W_UserObject
    class."""
    statictype = W_UserType

    # Nota Bene: we expect W_UserObject instances whose type inherits
    # from a built-in type to also contain the attributes of the
    # corresponding W_XxxObject class.  This is a non-restricted-Python-
    # compliant hack that we may have to rethink at some point.
    # It is similar to CPython's instances of subtypes of built-in
    # types whose memory layout start with what looks like an instance
    # of the parent built-in type.

    def __init__(w_self, space, w_type, w_args, w_kwds):
        # the restriction that a single built-in type is allowed among the
        # bases is specific to our W_UserObject implementation of user
        # objects, and should thus not be enforced in W_UserType.
        w_builtintype = getsinglebuiltintype(space, w_type)
        
        # first create an instance of the parent built-in type
        w_preself = space.call(w_builtintype, w_args, w_kwds)
        if not space.is_true(space.is_(space.type(w_preself), w_builtintype)):
            raise OperationError(space.w_TypeError,
                                 space.wrap("instantiating a subtype of a type "
                                            "with a misbehaving constructor"))

        # add custom attributes
        w_self.__dict__.update(
            {'w_uo_preself': w_preself,
             'w_uo_type': w_type,
             'w_uo_dict': space.newdict([]),
             })

    def __getattr__(w_self, attr):
        return getattr(w_self.w_uo_preself, attr)

    def __setattr__(w_self, attr, value):
        if attr in w_self.__dict__:
            w_self.__dict__[attr] = value
        else:
            setattr(w_self.w_preself, attr, value)

    def __delattr__(w_self, attr):
        raise AttributeError, "we don't wants attribute deletion in RPython"

    def get_builtin_impl_class(w_self):
        return w_self.w_uo_preself.get_builtin_impl_class()


registerimplementation(W_UserObject)


def getsinglebuiltintype(space, w_type):
    "Return the (asserted unique) built-in type that w_type inherits from."
    mostspecialized = space.w_object
    mro = list(w_type.getmro())
    mro.reverse()
    for w_base in mro:
        if not isinstance(w_base, W_UserType):
            if not space.is_true(space.issubtype(w_base, mostspecialized)):
                raise OperationError(space.w_TypeError,
                                     space.wrap("instance layout conflicts in "
                                                "multiple inheritance"))
            mostspecialized = w_base
    return mostspecialized


def user_type(space, w_userobj):
    return w_userobj.w_uo_type

StdObjSpace.type.register(user_type, W_UserObject)


def user_getdict(space, w_userobj):
    # XXX check getdict() of the base built-in implementation
    return w_userobj.w_uo_dict

StdObjSpace.getdict.register(user_getdict, W_UserObject)


# We register here all multimethods with at least one W_UserObject.
# No multimethod must be explicitely registered on W_UserObject except
# here, unless you want to completely override a behavior for user-defined
# types, as in user_type and user_getdict.

def build_user_operation(multimethod):
    def user_operation(space, *args_w):
        if len(args_w) != multimethod.arity:
            raise TypeError, "wrong number of arguments"
        for i in range(len(multimethod.specialnames)):
            w_arg = args_w[i]
            if isinstance(w_arg, W_UserObject):
                specialname = multimethod.specialnames[i]
                try:
                    w_value = w_arg.w_uo_type.lookup(space.wrap(specialname))
                except KeyError:
                    pass
                else:
                    # 'w_value' is a __xxx__ function object
                    w_value = space.get(w_value, w_arg, w_arg.w_uo_type)
                    # 'w_value' is now a bound method.
                    # if it is a sliced multimethod it should do the
                    # get_builtin_impl_class() trick automatically, not
                    # dispatching again on W_UserObject.
                    rest_args = list(args_w)
                    del rest_args[i]
                    w_args_w = space.newtuple(rest_args)
                    w_result = space.call(w_value, w_args_w, space.newdict([]))
                    if not space.is_true(space.is_(w_result,
                                                   space.w_NotImplemented)):
                        return w_result   # if w_result is not NotImplemented
        raise FailedToImplement
    return user_operation

for multimethod in typeobject.hack_out_multimethods(StdObjSpace):
    if multimethod not in (StdObjSpace.getdict,
                           StdObjSpace.type):
        user_operation = build_user_operation(multimethod)
        for i in range(multimethod.arity):
            signature = [W_ANY] * multimethod.arity
            signature[i] = W_UserObject
            multimethod.register(user_operation, *signature)
