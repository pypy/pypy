"""
Two bytecodes to speed up method calls.  Here is how a method call looks
like: (on the left, without the new bytecodes; on the right, with them)

    <push self>                    <push self>
    LOAD_ATTR       name           LOOKUP_METHOD   name
    <push arg 0>                   <push arg 0>
    ...                            ...
    <push arg n-1>                 <push arg n-1>
    CALL_FUNCTION   n              CALL_METHOD     n
"""

from pypy.interpreter import function
from pypy.objspace.descroperation import object_getattribute
from pypy.rlib import rstack # for resume points

# This module exports two extra methods for StdObjSpaceFrame implementing
# the LOOKUP_METHOD and CALL_METHOD opcodes in an efficient way, as well
# as a version of space.call_method() that uses the same approach.
# See pypy.objspace.std.objspace for where these functions are used from.


def LOOKUP_METHOD(f, nameindex, *ignored):
    #   stack before                 after
    #  --------------    --fast-method----fallback-case------------
    #
    #                      w_object       None
    #    w_object    =>    w_function     w_boundmethod_or_whatever
    #   (more stuff)      (more stuff)   (more stuff)
    #
    space = f.space
    w_obj = f.popvalue()
    w_name = f.getname_w(nameindex)
    w_value = None

    w_type = space.type(w_obj)
    if w_type.has_object_getattribute():
        name = space.str_w(w_name)
        w_descr = w_type.lookup(name)
        if w_descr is None:
            # this handles directly the common case
            #   module.function(args..)
            w_value = w_obj.getdictvalue(space, name)
        else:
            typ = type(w_descr)
            if typ is function.Function or typ is function.FunctionWithFixedCode:
                w_value = w_obj.getdictvalue_attr_is_in_class(space, name)
                if w_value is None:
                    # fast method path: a function object in the class,
                    # nothing in the instance
                    f.pushvalue(w_descr)
                    f.pushvalue(w_obj)
                    return
    if w_value is None:
        w_value = space.getattr(w_obj, w_name)
    f.pushvalue(w_value)
    f.pushvalue(None)

def CALL_METHOD(f, nargs, *ignored):
    # 'nargs' is the argument count excluding the implicit 'self'
    w_self = f.peekvalue(nargs)
    w_callable = f.peekvalue(nargs + 1)
    n = nargs + (w_self is not None)
    try:
        w_result = f.space.call_valuestack(w_callable, n, f)
        rstack.resume_point("CALL_METHOD", f, nargs, returns=w_result)
    finally:
        f.dropvalues(nargs + 2)
    f.pushvalue(w_result)


def call_method_opt(space, w_obj, methname, *arg_w):
    """An optimized version of space.call_method()
    based on the same principle as above.
    """
    w_type = space.type(w_obj)
    if w_type.has_object_getattribute():
        w_descr = space.lookup(w_obj, methname)
        typ = type(w_descr)
        if typ is function.Function or typ is function.FunctionWithFixedCode:
            w_value = w_obj.getdictvalue_attr_is_in_class(space, methname)
            if w_value is None:
                # fast method path: a function object in the class,
                # nothing in the instance
                return space.call_function(w_descr, w_obj, *arg_w)
    w_name = space.wrap(methname)
    w_meth = space.getattr(w_obj, w_name)
    return space.call_function(w_meth, *arg_w)
