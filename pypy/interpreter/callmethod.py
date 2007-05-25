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

from pypy.interpreter import pyframe, function
from pypy.rlib.jit import we_are_jitted
from pypy.interpreter.argument import Arguments


def object_getattribute(space):
    w_src, w_getattribute = space.lookup_in_type_where(space.w_object,
                                                       '__getattribute__')
    return w_getattribute
object_getattribute._annspecialcase_ = 'specialize:memo'


class __extend__(pyframe.PyFrame):

    def LOOKUP_METHOD(f, nameindex, *ignored):
        #   stack before                 after
        #  --------------    --fast-method----fallback-case------------
        #
        #                      w_object       None
        #    w_object    =>    w_function     w_boundmethod_or_whatever
        #   (more stuff)      (more stuff)   (more stuff)
        #
        # NB. this assumes a space based on pypy.objspace.descroperation.
        space = f.space
        w_obj = f.popvalue()
        w_name = f.getname_w(nameindex)
        w_value = None
        w_getattribute = space.lookup(w_obj, '__getattribute__')
        if w_getattribute is object_getattribute(space):
            name = space.str_w(w_name)
            w_descr = space.lookup(w_obj, name)
            if w_descr is None:
                # this handles directly the common case
                #   module.function(args..)
                w_value = w_obj.getdictvalue(space, w_name)
            elif type(w_descr) is function.Function:
                w_value = w_obj.getdictvalue_attr_is_in_class(space, w_name)
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
        finally:
            f.dropvalues(nargs + 2)
        f.pushvalue(w_result)
