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

def make_user_object(space, w_type, w_args, w_kwds):
    # the restriction that a single built-in type is allowed among the
    # bases is specific to our W_UserObject implementation of user
    # objects, and should thus not be enforced in W_UserType.
    # Note: w_type may be any object, not necessarily a W_UserType
    # (in case 'type' is subclassed).

    # create an instance of the parent built-in type
    w_builtintype = getsinglebuiltintype(space, w_type)
    newobj = space.call(w_builtintype, w_args, w_kwds)

    morph_into_user_object(space,w_type,newobj)
    
    return newobj


registerimplementation(W_UserObject)

_bltin_subclass_cache = {}

def _make_bltin_subclass(cls):
    global _bltin_subclass_cache
    try:
        return _bltin_subclass_cache[cls]
    except:
        subcls = type(W_Object)("%s_sub" % cls.__name__, (W_UserObject, cls),
                                {'statictype': W_UserType})

        # W_UserObject-to-the-parent-builtin-type delegation
        def delegate_to_parent_builtin(space, w_userobj):
            return w_userobj
        delegate_to_parent_builtin.trivial_delegation = True
        delegate_to_parent_builtin.result_class = cls
        delegate_to_parent_builtin.priority = PRIORITY_PARENT_TYPE
        StdObjSpace.delegate.register(delegate_to_parent_builtin, subcls)

        _bltin_subclass_cache[cls] = subcls
        return subcls

def morph_into_user_object(space,w_type,newobj):
    newobj.__class__ = _make_bltin_subclass(newobj.__class__)
    newobj.w_type = w_type
    if not hasattr(newobj,'w_dict'):
        newobj.w_dict = space.newdict([])
    return newobj


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


def type__User(space, w_userobj):
    return w_userobj.w_type

def getdict__User(space, w_userobj):
    # XXX check getdict() of the base built-in implementation
    return w_userobj.w_dict

def is_data_descr__User(space, w_userobj):
    try:
        space.type(w_userobj).lookup(space.wrap("__set__"))
    except:
        try:
            space.type(w_userobj).lookup(space.wrap("__delete__"))
        except:
            return 0
        else:
            return 1
    else:
        return 1        


class SpecialMethod:
    """An implementation for a multimethod that looks for a user-defined
    special __xxx__ method."""

    def __init__(self, method_name, bound_position=0):
        self.method_name = method_name
        self.bound_position = bound_position

    def internal_do_call(self, space, w_userobj, w_args, w_kwds):
        w_key = space.wrap(self.method_name)
        w_mro = space.getattr(w_userobj.w_type, space.wrap('__mro__'))
        mro = space.unpacktuple(w_mro)
        for w_base in mro:
            if not isinstance(w_base, W_UserType):
                continue
            try:
                w_function = w_base.lookup_exactly_here(w_key)
            except KeyError:
                continue
            w_method = space.get(w_function, w_userobj, w_base)
            return space.call(w_method, w_args, w_kwds)
        raise FailedToImplement

    def do_call(self, space, args_w):
        # args_w is in the standard multimethod order
        # we need it in the Python-friendly order (i.e. swapped for __rxxx__)
        args_w = list(args_w)
        w_userobj = args_w.pop(self.bound_position)
        w_args = space.newtuple(args_w)
        return self.internal_do_call(space, w_userobj, w_args, space.newdict([]))

    def normal_call(self, space, *args_w):
        "Call a user-defined __xxx__ method and convert the result back."
        w_result = self.do_call(space, args_w)
        # interpret 'NotImplemented' as meaning not implemented (duh).
        if space.is_true(space.is_(w_result, space.w_NotImplemented)):
            raise FailedToImplement
        return w_result

    def next_call(self, space, *args_w):
        "For .next()."
        # don't accept NotImplemented nor a real None, but catch StopIteration
        try:
            return self.do_call(space, args_w)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            raise NoValue

    def nonzero_call(self, space, *args_w):
        "For __nonzero__()."
        # accept any object and return its truth value
        # XXX if the user returns another custom object he can
        #     force the interpreter into an infinite loop
        w_result = self.do_call(space, args_w)
        return space.is_true(w_result)

    def argskwds_call(self, space, w_userobj, w_args, w_kwds):
        "For __init__()."
        return self.internal_do_call(space, w_userobj, w_args, w_kwds)

    def iter_call(self, space, *args_w):
        try:
            return self.do_call(space, args_w)
        except FailedToImplement:
            w_userobj = args_w[0]
            try:
                space.type(w_userobj).lookup(space.wrap('__getitem__'))
            except KeyError:
                raise FailedToImplement
            else:
                from iterobject import W_SeqIterObject
                return W_SeqIterObject(space, args_w[0])


import new
for multimethod in typeobject.hack_out_multimethods(StdObjSpace):
    for i in range(len(multimethod.specialnames)):
        f = SpecialMethod(multimethod.specialnames[i], i).normal_call
        signature = [W_ANY] * multimethod.arity
        signature[i] = W_UserObject
        multimethod.register(f, *signature)

next__User    = SpecialMethod('next').next_call
is_true__User = SpecialMethod('nonzero').nonzero_call
object_init__User = SpecialMethod('__init__').argskwds_call
iter__User = SpecialMethod('__iter__').iter_call

register_all(vars())
