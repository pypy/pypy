from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.inttype import int_typedef

def descr__new__(space, w_booltype, w_obj=None):
    space.w_bool.check_user_subclass(w_booltype)
    if space.is_true(w_obj):
        return space.w_True
    else:
        return space.w_False

# ____________________________________________________________

bool_typedef = StdTypeDef("bool", int_typedef,
    __doc__ = '''bool(x) -> bool

Returns True when the argument x is true, False otherwise.
The builtins True and False are the only two instances of the class bool.
The class bool is a subclass of the class int, and cannot be subclassed.''',
    __new__ = newmethod(descr__new__),
    )
bool_typedef.acceptable_as_base_class = False
