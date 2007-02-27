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
        w_typ = space.type(w_obj)
        w_src, w_dummy = space.lookup_in_type_where(w_typ, '__getattribute__')
        w_value = None
        if space.is_w(w_src, space.w_object):
            name = space.str_w(w_name)
            w_descr = space.lookup(w_obj, name)
            descr = space.interpclass_w(w_descr)
            if descr is None:
                # this handles directly the common case
                #   module.function(args..)
                w_value = w_obj.getdictvalue(space, w_name)
            elif type(descr) is function.Function:
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
        w_self     = f.peekvalue(nargs)
        w_callable = f.peekvalue(nargs + 1)
        try:
            n = nargs + (w_self is not None)
            w_result = f.space.call_valuestack(w_callable, n, f)
        finally:
            f.dropvalues(nargs + 2)
        f.pushvalue(w_result)
