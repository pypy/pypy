import operator
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.function import Function, Method, FunctionWithFixedCode
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import default_identity_hash
from pypy.tool.sourcetools import compile2, func_with_new_name
from pypy.rlib.objectmodel import specialize

def object_getattribute(space):
    "Utility that returns the app-level descriptor object.__getattribute__."
    w_src, w_getattribute = space.lookup_in_type_where(space.w_object,
                                                       '__getattribute__')
    return w_getattribute
object_getattribute._annspecialcase_ = 'specialize:memo'

def object_setattr(space):
    "Utility that returns the app-level descriptor object.__setattr__."
    w_src, w_setattr = space.lookup_in_type_where(space.w_object,
                                                  '__setattr__')
    return w_setattr
object_setattr._annspecialcase_ = 'specialize:memo'

def object_delattr(space):
    "Utility that returns the app-level descriptor object.__delattr__."
    w_src, w_delattr = space.lookup_in_type_where(space.w_object,
                                                  '__delattr__')
    return w_delattr
object_delattr._annspecialcase_ = 'specialize:memo'

def object_hash(space):
    "Utility that returns the app-level descriptor object.__hash__."
    w_src, w_hash = space.lookup_in_type_where(space.w_object,
                                                  '__hash__')
    return w_hash
object_hash._annspecialcase_ = 'specialize:memo'

def type_eq(space):
    "Utility that returns the app-level descriptor type.__eq__."
    w_src, w_eq = space.lookup_in_type_where(space.w_type,
                                             '__eq__')
    return w_eq
type_eq._annspecialcase_ = 'specialize:memo'

def raiseattrerror(space, w_obj, name, w_descr=None):
    w_type = space.type(w_obj)
    typename = w_type.getname(space)
    if w_descr is None:
        raise operationerrfmt(space.w_AttributeError,
                              "'%s' object has no attribute '%s'",
                              typename, name)
    else:
        raise operationerrfmt(space.w_AttributeError,
                              "'%s' object attribute '%s' is read-only",
                              typename, name)

def _same_class_w(space, w_obj1, w_obj2, w_typ1, w_typ2):
    return space.is_w(w_typ1, w_typ2)


class Object(object):
    def descr__getattribute__(space, w_obj, w_name):
        name = space.str_w(w_name)
        w_descr = space.lookup(w_obj, name)
        if w_descr is not None:
            if space.is_data_descr(w_descr):
                # Only override if __get__ is defined, too, for compatibility
                # with CPython.
                w_get = space.lookup(w_descr, "__get__")
                if w_get is not None:
                    w_type = space.type(w_obj)
                    return space.get_and_call_function(w_get, w_descr, w_obj,
                                                       w_type)
        w_value = w_obj.getdictvalue(space, name)
        if w_value is not None:
            return w_value
        if w_descr is not None:
            return space.get(w_descr, w_obj)
        raiseattrerror(space, w_obj, name)

    def descr__setattr__(space, w_obj, w_name, w_value):
        name = space.str_w(w_name)
        w_descr = space.lookup(w_obj, name)
        if w_descr is not None:
            if space.is_data_descr(w_descr):
                space.set(w_descr, w_obj, w_value)
                return
        if w_obj.setdictvalue(space, name, w_value):
            return
        raiseattrerror(space, w_obj, name, w_descr)

    def descr__delattr__(space, w_obj, w_name):
        name = space.str_w(w_name)
        w_descr = space.lookup(w_obj, name)
        if w_descr is not None:
            if space.is_data_descr(w_descr):
                space.delete(w_descr, w_obj)
                return
        if w_obj.deldictvalue(space, name):
            return
        raiseattrerror(space, w_obj, name, w_descr)

    def descr__init__(space, w_obj, __args__):
        pass

class DescrOperation(object):
    _mixin_ = True

    def is_data_descr(space, w_obj):
        return space.lookup(w_obj, '__set__') is not None

    def get_and_call_args(space, w_descr, w_obj, args):
        descr = space.interpclass_w(w_descr)
        # a special case for performance and to avoid infinite recursion
        if isinstance(descr, Function):
            return descr.call_obj_args(w_obj, args)
        else:
            w_impl = space.get(w_descr, w_obj)
            return space.call_args(w_impl, args)

    def get_and_call_function(space, w_descr, w_obj, *args_w):
        descr = space.interpclass_w(w_descr)
        typ = type(descr)
        # a special case for performance and to avoid infinite recursion
        if typ is Function or typ is FunctionWithFixedCode:
            # isinstance(typ, Function) would not be correct here:
            # for a BuiltinFunction we must not use that shortcut, because a
            # builtin function binds differently than a normal function
            # see test_builtin_as_special_method_is_not_bound
            # in interpreter/test/test_function.py

            # the fastcall paths are purely for performance, but the resulting
            # increase of speed is huge
            return descr.funccall(w_obj, *args_w)
        else:
            args = Arguments(space, list(args_w))
            w_impl = space.get(w_descr, w_obj)
            return space.call_args(w_impl, args)

    def call_args(space, w_obj, args):
        # two special cases for performance
        if isinstance(w_obj, Function):
            return w_obj.call_args(args)
        if isinstance(w_obj, Method):
            return w_obj.call_args(args)
        w_descr = space.lookup(w_obj, '__call__')
        if w_descr is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' object is not callable",
                                  typename)
        return space.get_and_call_args(w_descr, w_obj, args)

    def get(space, w_descr, w_obj, w_type=None):
        w_get = space.lookup(w_descr, '__get__')
        if w_get is None:
            return w_descr
        if w_type is None:
            w_type = space.type(w_obj)
        return space.get_and_call_function(w_get, w_descr, w_obj, w_type)

    def set(space, w_descr, w_obj, w_val):
        w_set = space.lookup(w_descr, '__set__')
        if w_set is None:
            typename = space.type(w_descr).getname(space)
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' object is not a descriptor with set",
                                  typename)
        return space.get_and_call_function(w_set, w_descr, w_obj, w_val)

    def delete(space, w_descr, w_obj):
        w_delete = space.lookup(w_descr, '__delete__')
        if w_delete is None:
            typename = space.type(w_descr).getname(space)
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' object is not a descriptor with delete",
                                  typename)
        return space.get_and_call_function(w_delete, w_descr, w_obj)

    def getattr(space, w_obj, w_name):
        # may be overridden in StdObjSpace
        w_descr = space.lookup(w_obj, '__getattribute__')
        return space._handle_getattribute(w_descr, w_obj, w_name)

    def _handle_getattribute(space, w_descr, w_obj, w_name):
        try:
            if w_descr is None:   # obscure case
                raise OperationError(space.w_AttributeError, space.w_None)
            return space.get_and_call_function(w_descr, w_obj, w_name)
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
            w_descr = space.lookup(w_obj, '__getattr__')
            if w_descr is None:
                raise
            return space.get_and_call_function(w_descr, w_obj, w_name)

    def setattr(space, w_obj, w_name, w_val):
        w_descr = space.lookup(w_obj, '__setattr__')
        if w_descr is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_AttributeError,
                                  "'%s' object is readonly",
                                  typename)
        return space.get_and_call_function(w_descr, w_obj, w_name, w_val)

    def delattr(space, w_obj, w_name):
        w_descr = space.lookup(w_obj, '__delattr__')
        if w_descr is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_AttributeError,
                                  "'%s' object does not support attribute removal",
                                  typename)
        return space.get_and_call_function(w_descr, w_obj, w_name)

    def is_true(space, w_obj):
        method = "__bool__"
        w_descr = space.lookup(w_obj, method)
        if w_descr is None:
            method = "__len__"
            w_descr = space.lookup(w_obj, method)
            if w_descr is None:
                return True
        w_res = space.get_and_call_function(w_descr, w_obj)
        # more shortcuts for common cases
        if space.is_w(w_res, space.w_False):
            return False
        if space.is_w(w_res, space.w_True):
            return True
        w_restype = space.type(w_res)
        if method == '__len__':
            return space._check_len_result(w_res) != 0
        else:
            raise OperationError(space.w_TypeError, space.wrap(
                    "__bool__ should return bool"))

    def nonzero(space, w_obj):
        if space.is_true(w_obj):
            return space.w_True
        else:
            return space.w_False

    def len(space, w_obj):
        w_descr = space.lookup(w_obj, '__len__')
        if w_descr is None:
            name = space.type(w_obj).getname(space)
            msg = "'%s' has no length" % (name,)
            raise OperationError(space.w_TypeError, space.wrap(msg))
        w_res = space.get_and_call_function(w_descr, w_obj)
        return space.wrap(space._check_len_result(w_res))

    def _check_len_result(space, w_obj):
        # Will complain if result is too big.
        result = space.int_w(space.int(w_obj))
        if result < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("__len__() should return >= 0"))
        return result

    def iter(space, w_obj):
        w_descr = space.lookup(w_obj, '__iter__')
        if w_descr is None:
            w_descr = space.lookup(w_obj, '__getitem__')
            if w_descr is None:
                typename = space.type(w_obj).getname(space)
                raise operationerrfmt(space.w_TypeError,
                                      "'%s' object is not iterable",
                                      typename)
            return space.newseqiter(w_obj)
        w_iter = space.get_and_call_function(w_descr, w_obj)
        w_next = space.lookup(w_iter, '__next__')
        if w_next is None:
            raise OperationError(space.w_TypeError,
                                 space.wrap("iter() returned non-iterator"))
        return w_iter

    def next(space, w_obj):
        w_descr = space.lookup(w_obj, '__next__')
        if w_descr is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' object is not an iterator",
                                  typename)
        return space.get_and_call_function(w_descr, w_obj)

    def getitem(space, w_obj, w_key):
        w_descr = space.lookup(w_obj, '__getitem__')
        if w_descr is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' object is not subscriptable",
                                  typename)
        return space.get_and_call_function(w_descr, w_obj, w_key)

    def setitem(space, w_obj, w_key, w_val):
        w_descr = space.lookup(w_obj, '__setitem__')
        if w_descr is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_TypeError,
                              "'%s' object does not support item assignment",
                                  typename)
        return space.get_and_call_function(w_descr, w_obj, w_key, w_val)

    def delitem(space, w_obj, w_key):
        w_descr = space.lookup(w_obj, '__delitem__')
        if w_descr is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_TypeError,
                                "'%s' object does not support item deletion",
                                  typename)
        return space.get_and_call_function(w_descr, w_obj, w_key)

    def getslice(space, w_obj, w_start, w_stop):
        w_slice = space.newslice(w_start, w_stop, space.w_None)
        return space.getitem(w_obj, w_slice)

    def setslice(space, w_obj, w_start, w_stop, w_sequence):
        w_slice = space.newslice(w_start, w_stop, space.w_None)
        return space.setitem(w_obj, w_slice, w_sequence)

    def delslice(space, w_obj, w_start, w_stop):
        w_slice = space.newslice(w_start, w_stop, space.w_None)
        return space.delitem(w_obj, w_slice)

    def format(space, w_obj, w_format_spec):
        w_descr = space.lookup(w_obj, '__format__')
        if w_descr is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' object does not define __format__",
                                  typename)
        w_res = space.get_and_call_function(w_descr, w_obj, w_format_spec)
        if not space.is_true(space.isinstance(w_res, space.w_unicode)):
            typename = space.type(w_obj).getname(space)
            restypename = space.type(w_res).getname(space)
            raise operationerrfmt(space.w_TypeError,
                "%s.__format__ must return a string, not %s",
                                  typename, restypename)
        return w_res

    def pow(space, w_obj1, w_obj2, w_obj3):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_in_type_where(w_typ1, '__pow__')
        if space.is_w(w_typ1, w_typ2):
            w_right_impl = None
        else:
            w_right_src, w_right_impl = space.lookup_in_type_where(w_typ2, '__rpow__')
            # sse binop_impl
            if (w_left_src is not w_right_src
                and space.is_true(space.issubtype(w_typ2, w_typ1))):
                if (w_left_src and w_right_src and
                    not space.abstract_issubclass_w(w_left_src, w_right_src) and
                    not space.abstract_issubclass_w(w_typ1, w_right_src)):
                    w_obj1, w_obj2 = w_obj2, w_obj1
                    w_left_impl, w_right_impl = w_right_impl, w_left_impl
        if w_left_impl is not None:
            if space.is_w(w_obj3, space.w_None):
                w_res = space.get_and_call_function(w_left_impl, w_obj1, w_obj2)
            else:
                w_res = space.get_and_call_function(w_left_impl, w_obj1, w_obj2, w_obj3)
            if _check_notimplemented(space, w_res):
                return w_res
        if w_right_impl is not None:
           if space.is_w(w_obj3, space.w_None):
               w_res = space.get_and_call_function(w_right_impl, w_obj2, w_obj1)
           else:
               w_res = space.get_and_call_function(w_right_impl, w_obj2, w_obj1,
                                                   w_obj3)
           if _check_notimplemented(space, w_res):
               return w_res

        raise OperationError(space.w_TypeError,
                space.wrap("operands do not support **"))

    def inplace_pow(space, w_lhs, w_rhs):
        w_impl = space.lookup(w_lhs, '__ipow__')
        if w_impl is not None:
            w_res = space.get_and_call_function(w_impl, w_lhs, w_rhs)
            if _check_notimplemented(space, w_res):
                return w_res
        return space.pow(w_lhs, w_rhs, space.w_None)

    def contains(space, w_container, w_item):
        w_descr = space.lookup(w_container, '__contains__')
        if w_descr is not None:
            return space.get_and_call_function(w_descr, w_container, w_item)
        return space.sequence_contains(w_container, w_item)

    def sequence_contains(space, w_container, w_item):
        w_iter = space.iter(w_container)
        while 1:
            try:
                w_next = space.next(w_iter)
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
                return space.w_False
            if space.eq_w(w_next, w_item):
                return space.w_True

    def sequence_count(space, w_container, w_item):
        w_iter = space.iter(w_container)
        count = 0
        while 1:
            try:
                w_next = space.next(w_iter)
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
                return space.wrap(count)
            if space.eq_w(w_next, w_item):
                count += 1

    def hash(space, w_obj):
        w_hash = space.lookup(w_obj, '__hash__')
        if w_hash is None:
            # xxx there used to be logic about "do we have __eq__ or __cmp__"
            # here, but it does not really make sense, as 'object' has a
            # default __hash__.  This path should only be taken under very
            # obscure circumstances.
            return default_identity_hash(space, w_obj)
        if space.is_w(w_hash, space.w_None):
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' objects are unhashable", typename)
        w_result = space.get_and_call_function(w_hash, w_obj)
        w_resulttype = space.type(w_result)
        if space.is_w(w_resulttype, space.w_int):
            return w_result
        elif space.is_true(space.isinstance(w_result, space.w_int)):
            # be careful about subclasses of 'int'...
            return space.wrap(space.int_w(w_result))
        else:
            raise OperationError(space.w_TypeError,
                    space.wrap("__hash__() should return an int"))

    def userdel(space, w_obj):
        w_del = space.lookup(w_obj, '__del__')
        if w_del is not None:
            space.get_and_call_function(w_del, w_obj)

    def cmp(space, w_v, w_w):

        if space.is_w(w_v, w_w):
            return space.wrap(0)

        # The real comparison
        if space.is_w(space.type(w_v), space.type(w_w)):
            # for object of the same type, prefer __cmp__ over rich comparison.
            w_cmp = space.lookup(w_v, '__cmp__')
            w_res = _invoke_binop(space, w_cmp, w_v, w_w)
            if w_res is not None:
                return w_res
        # fall back to rich comparison.
        if space.eq_w(w_v, w_w):
            return space.wrap(0)
        elif space.is_true(space.lt(w_v, w_w)):
            return space.wrap(-1)
        return space.wrap(1)

    def issubtype(space, w_sub, w_type):
        return space._type_issubtype(w_sub, w_type)

    @specialize.arg_or_var(2)
    def isinstance(space, w_inst, w_type):
        return space.wrap(space._type_isinstance(w_inst, w_type))

    def issubtype_allow_override(space, w_sub, w_type):
        w_check = space.lookup(w_type, "__subclasscheck__")
        if w_check is None:
            raise OperationError(space.w_TypeError,
                                 space.wrap("issubclass not supported here"))
        return space.get_and_call_function(w_check, w_type, w_sub)

    def isinstance_allow_override(space, w_inst, w_type):
        w_check = space.lookup(w_type, "__instancecheck__")
        if w_check is not None:
            return space.get_and_call_function(w_check, w_type, w_inst)
        else:
            return space.isinstance(w_inst, w_type)


# helpers

def _check_notimplemented(space, w_obj):
    return not space.is_w(w_obj, space.w_NotImplemented)

def _invoke_binop(space, w_impl, w_obj1, w_obj2):
    if w_impl is not None:
        w_res = space.get_and_call_function(w_impl, w_obj1, w_obj2)
        if _check_notimplemented(space, w_res):
            return w_res
    return None

# helper for invoking __cmp__

def _conditional_neg(space, w_obj, flag):
    if flag:
        return space.neg(w_obj)
    else:
        return w_obj

def _cmp(space, w_obj1, w_obj2, symbol):
    w_typ1 = space.type(w_obj1)
    w_typ2 = space.type(w_obj2)
    w_left_src, w_left_impl = space.lookup_in_type_where(w_typ1, '__cmp__')
    do_neg1 = False
    do_neg2 = True
    if space.is_w(w_typ1, w_typ2):
        w_right_impl = None
    else:
        w_right_src, w_right_impl = space.lookup_in_type_where(w_typ2, '__cmp__')
        if (w_left_src is not w_right_src
            and space.is_true(space.issubtype(w_typ2, w_typ1))):
            w_obj1, w_obj2 = w_obj2, w_obj1
            w_left_impl, w_right_impl = w_right_impl, w_left_impl
            do_neg1, do_neg2 = do_neg2, do_neg1

    w_res = _invoke_binop(space, w_left_impl, w_obj1, w_obj2)
    if w_res is not None:
        return _conditional_neg(space, w_res, do_neg1)
    w_res = _invoke_binop(space, w_right_impl, w_obj2, w_obj1)
    if w_res is not None:
        return _conditional_neg(space, w_res, do_neg2)
    # fall back to internal rules
    if space.is_w(w_obj1, w_obj2):
        return space.wrap(0)
    else:
        typename1 = space.type(w_obj1).getname(space)
        typename2 = space.type(w_obj2).getname(space)
        raise operationerrfmt(space.w_TypeError,
                              "unorderable types: %s %s %s",
                              typename1, symbol, typename2)


# regular methods def helpers

def _make_binop_impl(symbol, specialnames):
    left, right = specialnames
    errormsg = "unsupported operand type(s) for %s: '%%s' and '%%s'" % (
        symbol.replace('%', '%%'),)

    def binop_impl(space, w_obj1, w_obj2):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_in_type_where(w_typ1, left)
        if space.is_w(w_typ1, w_typ2):
            w_right_impl = None
        else:
            w_right_src, w_right_impl = space.lookup_in_type_where(w_typ2, right)
            # the logic to decide if the reverse operation should be tried
            # before the direct one is very obscure.  For now, and for
            # sanity reasons, we just compare the two places where the
            # __xxx__ and __rxxx__ methods where found by identity.
            # Note that space.is_w() is potentially not happy if one of them
            # is None (e.g. with the thunk space)...
            if w_left_src is not w_right_src:    # XXX
                # -- end of bug compatibility
                if space.is_true(space.issubtype(w_typ2, w_typ1)):
                    if (w_left_src and w_right_src and
                        not space.abstract_issubclass_w(w_left_src, w_right_src) and
                        not space.abstract_issubclass_w(w_typ1, w_right_src)):
                        w_obj1, w_obj2 = w_obj2, w_obj1
                        w_left_impl, w_right_impl = w_right_impl, w_left_impl

        w_res = _invoke_binop(space, w_left_impl, w_obj1, w_obj2)
        if w_res is not None:
            return w_res
        w_res = _invoke_binop(space, w_right_impl, w_obj2, w_obj1)
        if w_res is not None:
            return w_res
        typename1 = w_typ1.getname(space)
        typename2 = w_typ2.getname(space)
        raise operationerrfmt(space.w_TypeError, errormsg,
                              typename1, typename2)

    return func_with_new_name(binop_impl, "binop_%s_impl"%left.strip('_'))

def _make_comparison_impl(symbol, specialnames):
    left, right = specialnames
    op = getattr(operator, left)
    def comparison_impl(space, w_obj1, w_obj2):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_in_type_where(w_typ1, left)
        w_first = w_obj1
        w_second = w_obj2
        #
        if left == right and space.is_w(w_typ1, w_typ2):
            # for __eq__ and __ne__, if the objects have the same
            # class, then don't try the opposite method, which is the
            # same one.
            w_right_impl = None
        else:
            # in all other cases, try the opposite method.
            w_right_src, w_right_impl = space.lookup_in_type_where(w_typ2,right)
            if space.is_w(w_typ1, w_typ2):
                # if the type is the same, then don't reverse: try
                # left first, right next.
                pass
            elif space.is_true(space.issubtype(w_typ2, w_typ1)):
                # if typ2 is a subclass of typ1.
                w_obj1, w_obj2 = w_obj2, w_obj1
                w_left_impl, w_right_impl = w_right_impl, w_left_impl

        w_res = _invoke_binop(space, w_left_impl, w_obj1, w_obj2)
        if w_res is not None:
            return w_res
        w_res = _invoke_binop(space, w_right_impl, w_obj2, w_obj1)
        if w_res is not None:
            return w_res
        # fallback: lt(a, b) <= lt(cmp(a, b), 0) ...
        w_res = _cmp(space, w_first, w_second, symbol)
        res = space.int_w(w_res)
        return space.wrap(op(res, 0))

    return func_with_new_name(comparison_impl, 'comparison_%s_impl'%left.strip('_'))

def _make_inplace_impl(symbol, specialnames):
    specialname, = specialnames
    assert specialname.startswith('__i') and specialname.endswith('__')
    noninplacespacemethod = specialname[3:-2]
    if noninplacespacemethod in ['or', 'and']:
        noninplacespacemethod += '_'     # not too clean
    def inplace_impl(space, w_lhs, w_rhs):
        w_impl = space.lookup(w_lhs, specialname)
        if w_impl is not None:
            w_res = space.get_and_call_function(w_impl, w_lhs, w_rhs)
            if _check_notimplemented(space, w_res):
                return w_res
        # XXX fix the error message we get here
        return getattr(space, noninplacespacemethod)(w_lhs, w_rhs)

    return func_with_new_name(inplace_impl, 'inplace_%s_impl'%specialname.strip('_'))

def _make_unaryop_impl(symbol, specialnames):
    specialname, = specialnames
    errormsg = "unsupported operand type for unary %s: '%%s'" % symbol
    def unaryop_impl(space, w_obj):
        w_impl = space.lookup(w_obj, specialname)
        if w_impl is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_TypeError, errormsg, typename)
        return space.get_and_call_function(w_impl, w_obj)
    return func_with_new_name(unaryop_impl, 'unaryop_%s_impl'%specialname.strip('_'))

# the following seven operations are really better to generate with
# string-templating (and maybe we should consider this for
# more of the above manually-coded operations as well)

for targetname, specialname, checkerspec in [
    ('int', '__int__', ("space.w_int",)),
    ('index', '__index__', ("space.w_int",)),
    ('float', '__float__', ("space.w_float",))]:

    l = ["space.is_true(space.isinstance(w_result, %s))" % x
                for x in checkerspec]
    checker = " or ".join(l)
    source = """if 1:
        def %(targetname)s(space, w_obj):
            w_impl = space.lookup(w_obj, %(specialname)r)
            if w_impl is None:
                typename = space.type(w_obj).getname(space)
                raise operationerrfmt(space.w_TypeError,
                      "unsupported operand type for %(targetname)s(): '%%s'",
                                      typename)
            w_result = space.get_and_call_function(w_impl, w_obj)

            if %(checker)s:
                return w_result
            typename = space.type(w_result).getname(space)
            msg = "%(specialname)s returned non-%(targetname)s (type '%%s')"
            raise operationerrfmt(space.w_TypeError, msg, typename)
        assert not hasattr(DescrOperation, %(targetname)r)
        DescrOperation.%(targetname)s = %(targetname)s
        del %(targetname)s
        \n""" % locals()
    exec compile2(source)

for targetname, specialname in [
    ('str', '__str__'),
    ('repr', '__repr__')]:

    source = """if 1:
        def %(targetname)s(space, w_obj):
            w_impl = space.lookup(w_obj, %(specialname)r)
            if w_impl is None:
                typename = space.type(w_obj).getname(space)
                raise operationerrfmt(space.w_TypeError,
                      "unsupported operand type for %(targetname)s(): '%%s'",
                                      typename)
            w_result = space.get_and_call_function(w_impl, w_obj)

            if space.is_true(space.isinstance(w_result, space.w_str)):
                return w_result
            try:
                result = space.str_w(w_result)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                typename = space.type(w_result).getname(space)
                msg = "%(specialname)s returned non-%(targetname)s (type '%%s')"
                raise operationerrfmt(space.w_TypeError, msg, typename)
            else:
                # re-wrap the result as a real string
                return space.wrap(result)
        assert not hasattr(DescrOperation, %(targetname)r)
        DescrOperation.%(targetname)s = %(targetname)s
        del %(targetname)s
        \n""" % locals()
    exec compile2(source)

# add default operation implementations for all still missing ops

for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    if not hasattr(DescrOperation, _name):
        _impl_maker = None
        if _arity == 2 and _name in ['lt', 'le', 'gt', 'ge', 'ne', 'eq']:
            #print "comparison", _specialnames
            _impl_maker = _make_comparison_impl
        elif _arity == 2 and _name.startswith('inplace_'):
            #print "inplace", _specialnames
            _impl_maker = _make_inplace_impl
        elif _arity == 2 and len(_specialnames) == 2:
            #print "binop", _specialnames
            _impl_maker = _make_binop_impl
        elif _arity == 1 and len(_specialnames) == 1:
            #print "unaryop", _specialnames
            _impl_maker = _make_unaryop_impl
        if _impl_maker:
            setattr(DescrOperation,_name,_impl_maker(_symbol,_specialnames))
        elif _name not in ['is_', 'id','type','issubtype',
                           # not really to be defined in DescrOperation
                           'ord', 'unichr', 'unicode']:
            raise Exception, "missing def for operation %s" % _name
