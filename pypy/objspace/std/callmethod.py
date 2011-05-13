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
from pypy.rlib import jit
from pypy.objspace.std.mapdict import LOOKUP_METHOD_mapdict, \
    LOOKUP_METHOD_mapdict_fill_cache_method


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

    if space.config.objspace.std.withmapdict and not jit.we_are_jitted():
        # mapdict has an extra-fast version of this function
        from pypy.objspace.std.mapdict import LOOKUP_METHOD_mapdict
        if LOOKUP_METHOD_mapdict(f, nameindex, w_obj):
            return

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
                w_value = w_obj.getdictvalue(space, name)
                if w_value is None:
                    # fast method path: a function object in the class,
                    # nothing in the instance
                    f.pushvalue(w_descr)
                    f.pushvalue(w_obj)
                    if (space.config.objspace.std.withmapdict and
                            not jit.we_are_jitted()):
                        # let mapdict cache stuff
                        LOOKUP_METHOD_mapdict_fill_cache_method(
                            f.getcode(), nameindex, w_obj, w_type, w_descr)
                    return
    if w_value is None:
        w_value = space.getattr(w_obj, w_name)
    f.pushvalue(w_value)
    f.pushvalue(None)

@jit.unroll_safe
def CALL_METHOD(f, oparg, *ignored):
    # opargs contains the arg, and kwarg count, excluding the implicit 'self'
    n_args = oparg & 0xff
    n_kwargs = (oparg >> 8) & 0xff
    w_self = f.peekvalue(n_args + (2 * n_kwargs))
    n = n_args + (w_self is not None)
    
    if not n_kwargs:
        w_callable = f.peekvalue(n_args + (2 * n_kwargs) + 1)
        try:
            w_result = f.space.call_valuestack(w_callable, n, f)
        finally:
            f.dropvalues(n_args + 2)
    else:
        keywords = [None] * n_kwargs
        keywords_w = [None] * n_kwargs
        while True:
            n_kwargs -= 1
            if n_kwargs < 0:
                break
            w_value = f.popvalue()
            w_key = f.popvalue()
            key = f.space.str_w(w_key)
            keywords[n_kwargs] = key
            keywords_w[n_kwargs] = w_value
    
        arguments = f.popvalues(n)    # includes w_self if it is not None
        args = f.argument_factory(arguments, keywords, keywords_w, None, None)
        if w_self is None:
            f.popvalue()    # removes w_self, which is None
        w_callable = f.popvalue()
        if f.is_being_profiled and function.is_builtin_code(w_callable):
            w_result = f.space.call_args_and_c_profile(f, w_callable, args)
        else:
            w_result = f.space.call_args(w_callable, args)
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
            w_value = w_obj.getdictvalue(space, methname)
            if w_value is None:
                # fast method path: a function object in the class,
                # nothing in the instance
                return space.call_function(w_descr, w_obj, *arg_w)
    w_name = space.wrap(methname)
    w_meth = space.getattr(w_obj, w_name)
    return space.call_function(w_meth, *arg_w)
