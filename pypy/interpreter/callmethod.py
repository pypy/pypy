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
from pypy.interpreter.error import OperationError
from pypy.objspace.descroperation import DescrOperation, raiseattrerror


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
        if isinstance(space, DescrOperation):
            w_getattribute = space.lookup(w_obj, '__getattribute__')
            ok_to_optimize = w_getattribute is object_getattribute(space)
        else:
            ok_to_optimize = False

        if not ok_to_optimize:
            w_value = space.getattr(w_obj, w_name)
        else:
            name = space.str_w(w_name)
            w_descr = space.lookup(w_obj, name)
            if type(w_descr) is function.Function:
                w_value = w_obj.getdictvalue_attr_is_in_class(space, w_name)
                if w_value is None:
                    # fast method path: a function object in the class,
                    # nothing in the instance
                    f.pushvalue(w_descr)
                    f.pushvalue(w_obj)
                    return
                # else we have a function object in the class, but shadowed
                # by an instance attribute
            else:
                # anything else than a function object in the class
                # => use the default lookup logic, without re-looking-up
                #    w_descr and __getattribute__, though
                w_value = default_lookup_logic(space, w_obj, w_descr, w_name)
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


def object_getattribute(space):
    w_src, w_getattribute = space.lookup_in_type_where(space.w_object,
                                                       '__getattribute__')
    return w_getattribute
object_getattribute._annspecialcase_ = 'specialize:memo'


def default_getattribute(space, w_obj, w_descr, w_name):
    # code copied from descroperation.Object.descr__getattribute__()
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            return space.get(w_descr, w_obj)
        w_value = w_obj.getdictvalue_attr_is_in_class(space, w_name)
    else:
        w_value = w_obj.getdictvalue(space, w_name)
    if w_value is not None:
        return w_value
    if w_descr is not None:
        return space.get(w_descr, w_obj)
    raiseattrerror(space, w_obj, space.str_w(w_name))

def default_lookup_logic(space, w_obj, w_descr, w_name):
    # code copied from descroperation.DescrOperation.getattr()
    try:
        return default_getattribute(space, w_obj, w_descr, w_name)
    except OperationError, e:
        if not e.match(space, space.w_AttributeError):
            raise
        w_descr = space.lookup(w_obj, '__getattr__')
        if w_descr is None:
            raise
        return space.get_and_call_function(w_descr, w_obj, w_name)
