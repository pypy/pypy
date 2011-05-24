import operator
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.function import Function, Method, FunctionWithFixedCode
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import default_identity_hash
from pypy.tool.sourcetools import compile2, func_with_new_name
from pypy.module.__builtin__.interp_classobj import W_InstanceObject

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

# Helpers for old-style and mix-style mixup

def _same_class_w(space, w_obj1, w_obj2, w_typ1, w_typ2):
    if (space.is_oldstyle_instance(w_obj1) and
        space.is_oldstyle_instance(w_obj2)):
        assert isinstance(w_obj1, W_InstanceObject)
        assert isinstance(w_obj2, W_InstanceObject)
        return space.is_w(w_obj1.w_class, w_obj2.w_class)
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
        if w_obj.deldictvalue(space, w_name):
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
        w_descr = space.lookup(w_obj, '__nonzero__')
        if w_descr is None:
            w_descr = space.lookup(w_obj, '__len__')
            if w_descr is None:
                return True
        w_res = space.get_and_call_function(w_descr, w_obj)
        # more shortcuts for common cases
        if w_res is space.w_False:
            return False
        if w_res is space.w_True:
            return True
        w_restype = space.type(w_res)
        if (space.is_w(w_restype, space.w_bool) or
            space.is_w(w_restype, space.w_int) or
            space.is_w(w_restype, space.w_long)):
            return space.int_w(w_res) != 0
        else:
            raise OperationError(space.w_TypeError,
                                 space.wrap('__nonzero__ should return '
                                            'bool or integer'))

    def nonzero(self, w_obj):
        if self.is_true(w_obj):
            return self.w_True
        else:
            return self.w_False

##    def len(self, w_obj):
##        XXX needs to check that the result is an int (or long?) >= 0

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
        w_next = space.lookup(w_iter, 'next')
        if w_next is None:
            raise OperationError(space.w_TypeError,
                                 space.wrap("iter() returned non-iterator"))
        return w_iter

    def next(space, w_obj):
        w_descr = space.lookup(w_obj, 'next')
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
        w_descr = space.lookup(w_obj, '__getslice__')
        if w_descr is None:
            w_slice = space.newslice(w_start, w_stop, space.w_None)
            return space.getitem(w_obj, w_slice)
        w_start, w_stop = old_slice_range(space, w_obj, w_start, w_stop)
        return space.get_and_call_function(w_descr, w_obj, w_start, w_stop)

    def setslice(space, w_obj, w_start, w_stop, w_sequence):
        w_descr = space.lookup(w_obj, '__setslice__')
        if w_descr is None:
            w_slice = space.newslice(w_start, w_stop, space.w_None)
            return space.setitem(w_obj, w_slice, w_sequence)
        w_start, w_stop = old_slice_range(space, w_obj, w_start, w_stop)
        return space.get_and_call_function(w_descr, w_obj, w_start, w_stop, w_sequence)

    def delslice(space, w_obj, w_start, w_stop):
        w_descr = space.lookup(w_obj, '__delslice__')
        if w_descr is None:
            w_slice = space.newslice(w_start, w_stop, space.w_None)
            return space.delitem(w_obj, w_slice)
        w_start, w_stop = old_slice_range(space, w_obj, w_start, w_stop)
        return space.get_and_call_function(w_descr, w_obj, w_start, w_stop)

    def format(space, w_obj, w_format_spec):
        w_descr = space.lookup(w_obj, '__format__')
        if w_descr is None:
            typename = space.type(w_obj).getname(space)
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' object does not define __format__",
                                  typename)
        w_res = space.get_and_call_function(w_descr, w_obj, w_format_spec)
        if not space.is_true(space.isinstance(w_res, space.w_basestring)):
            typename = space.type(w_obj).getname(space)
            restypename = space.type(w_res).getname(space)
            raise operationerrfmt(space.w_TypeError,
                "%s.__format__ must return string or unicode, not %s",
                                  typename, restypename)
        return w_res

    def pow(space, w_obj1, w_obj2, w_obj3):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_in_type_where(w_typ1, '__pow__')
        if _same_class_w(space, w_obj1, w_obj2, w_typ1, w_typ2):
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
        return space._contains(w_container, w_item)

    def _contains(space, w_container, w_item):
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

    def hash(space, w_obj):
        w_hash = space.lookup(w_obj, '__hash__')
        if w_hash is None:
            # xxx there used to be logic about "do we have __eq__ or __cmp__"
            # here, but it does not really make sense, as 'object' has a
            # default __hash__.  This path should only be taken under very
            # obscure circumstances.
            return default_identity_hash(space, w_obj)
        if space.is_w(w_hash, space.w_None):
            typename = space.type(w_obj).getname(space, '?')
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' objects are unhashable", typename)
        w_result = space.get_and_call_function(w_hash, w_obj)
        w_resulttype = space.type(w_result)
        if space.is_w(w_resulttype, space.w_int):
            return w_result
        elif space.is_w(w_resulttype, space.w_long):
            return space.hash(w_result)
        elif space.is_true(space.isinstance(w_result, space.w_int)):
            # be careful about subclasses of 'int'...
            return space.wrap(space.int_w(w_result))
        elif space.is_true(space.isinstance(w_result, space.w_long)):
            # be careful about subclasses of 'long'...
            bigint = space.bigint_w(w_result)
            return space.wrap(bigint.hash())
        else:
            raise OperationError(space.w_TypeError,
                    space.wrap("__hash__() should return an int or long"))

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

    def coerce(space, w_obj1, w_obj2):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_in_type_where(w_typ1, '__coerce__')
        if space.is_w(w_typ1, w_typ2):
            w_right_impl = None
        else:
            w_right_src, w_right_impl = space.lookup_in_type_where(w_typ2, '__coerce__')
            if (w_left_src is not w_right_src
                and space.is_true(space.issubtype(w_typ2, w_typ1))):
                w_obj1, w_obj2 = w_obj2, w_obj1
                w_left_impl, w_right_impl = w_right_impl, w_left_impl

        w_res = _invoke_binop(space, w_left_impl, w_obj1, w_obj2)
        if w_res is None or space.is_w(w_res, space.w_None):
            w_res = _invoke_binop(space, w_right_impl, w_obj2, w_obj1)
            if w_res is None  or space.is_w(w_res, space.w_None):
                raise OperationError(space.w_TypeError,
                                     space.wrap("coercion failed"))
            if (not space.is_true(space.isinstance(w_res, space.w_tuple)) or
                space.len_w(w_res) != 2):
                raise OperationError(space.w_TypeError,
                                     space.wrap("coercion should return None or 2-tuple"))
            w_res = space.newtuple([space.getitem(w_res, space.wrap(1)), space.getitem(w_res, space.wrap(0))])
        elif (not space.is_true(space.isinstance(w_res, space.w_tuple)) or
            space.len_w(w_res) != 2):
            raise OperationError(space.w_TypeError,
                                 space.wrap("coercion should return None or 2-tuple"))
        return w_res

    def issubtype(space, w_sub, w_type, allow_override=False):
        if allow_override:
            w_check = space.lookup(w_type, "__subclasscheck__")
            if w_check is None:
                raise OperationError(space.w_TypeError,
                                     space.wrap("issubclass not supported here"))
            return space.get_and_call_function(w_check, w_type, w_sub)
        return space._type_issubtype(w_sub, w_type)

    def isinstance(space, w_inst, w_type, allow_override=False):
        if allow_override:
            w_check = space.lookup(w_type, "__instancecheck__")
            if w_check is not None:
                return space.get_and_call_function(w_check, w_type, w_inst)
        return space.issubtype(space.type(w_inst), w_type, allow_override)



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
    if space.is_w(w_obj1, space.w_None):
        return space.wrap(-1)
    if space.is_w(w_obj2, space.w_None):
        return space.wrap(1)
    if space.is_w(w_typ1, w_typ2):
        #print "WARNING, comparison by address!"
        lt = _id_cmpr(space, w_obj1, w_obj2, symbol)
    else:
        #print "WARNING, comparison by type name!"

        # the CPython rule is to compare type names; numbers are
        # smaller.  So we compare the types by the following key:
        #   (not_a_number_flag, type_name, type_id)
        num1 = number_check(space, w_obj1)
        num2 = number_check(space, w_obj2)
        if num1 != num2:
            lt = num1      # if obj1 is a number, it is Lower Than obj2
        else:
            name1 = w_typ1.getname(space, "")
            name2 = w_typ2.getname(space, "")
            if name1 != name2:
                lt = name1 < name2
            else:
                lt = _id_cmpr(space, w_typ1, w_typ2, symbol)
    if lt:
        return space.wrap(-1)
    else:
        return space.wrap(1)

def _id_cmpr(space, w_obj1, w_obj2, symbol):
    if symbol == "==":
        return not space.is_w(w_obj1, w_obj2)
    elif symbol == "!=":
        return space.is_w(w_obj1, w_obj2)
    w_id1 = space.id(w_obj1)
    w_id2 = space.id(w_obj2)
    return space.is_true(space.lt(w_id1, w_id2))


def number_check(space, w_obj):
    # avoid this as much as possible.  It checks if w_obj "looks like"
    # it might be a number-ish thing.
    return (space.lookup(w_obj, '__int__') is not None or
            space.lookup(w_obj, '__float__') is not None)



# what is the maximum value slices can get on CPython?
# we need to stick to that value, because fake.py etc.
class Temp(object):
    def __getslice__(self, i, j):
        return j
slice_max = Temp()[:]
del Temp

def old_slice_range_getlength(space, w_obj):
    # NB. the language ref is inconsistent with the new-style class
    # behavior when w_obj doesn't implement __len__(), so we just
    # follow cpython. Also note that CPython slots make it easier
    # to check for object implementing it or not. We just catch errors
    # so this behavior is slightly different
    try:
        return space.len(w_obj)
    except OperationError, e:
        if not ((e.match(space, space.w_AttributeError) or
                 e.match(space, space.w_TypeError))):
            raise
    return None

def old_slice_range(space, w_obj, w_start, w_stop):
    """Only for backward compatibility for __getslice__()&co methods."""
    w_length = None
    if space.is_w(w_start, space.w_None):
        w_start = space.wrap(0)
    else:
        start = space.getindex_w(w_start, None)
        w_start = space.wrap(start)
        if start < 0:
            w_length = old_slice_range_getlength(space, w_obj)
            if w_length is not None:
                w_start = space.add(w_start, w_length)
    if space.is_w(w_stop, space.w_None):
        w_stop = space.wrap(slice_max)
    else:
        stop = space.getindex_w(w_stop, None)
        w_stop = space.wrap(stop)
        if stop < 0:
            if w_length is None:
                w_length = old_slice_range_getlength(space, w_obj)
            if w_length is not None:
                w_stop = space.add(w_stop, w_length)
    return w_start, w_stop

# regular methods def helpers

def _make_binop_impl(symbol, specialnames):
    left, right = specialnames
    errormsg = "unsupported operand type(s) for %s: '%%s' and '%%s'" % (
        symbol.replace('%', '%%'),)

    def binop_impl(space, w_obj1, w_obj2):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_in_type_where(w_typ1, left)
        if _same_class_w(space, w_obj1, w_obj2, w_typ1, w_typ2):
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
                # -- cpython bug compatibility: see objspace/std/test/
                # -- test_unicodeobject.test_str_unicode_concat_overrides.
                # -- The following handles "unicode + string subclass" by
                # -- pretending that the unicode is a superclass of the
                # -- string, thus giving priority to the string subclass'
                # -- __radd__() method.  The case "string + unicode subclass"
                # -- is handled directly by add__String_Unicode().
                if symbol == '+' and space.is_w(w_typ1, space.w_unicode):
                    w_typ1 = space.w_basestring
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

        if _same_class_w(space, w_obj1, w_obj2, w_typ1, w_typ2):
            w_right_impl = None
        else:
            w_right_src, w_right_impl = space.lookup_in_type_where(w_typ2, right)
            # XXX see binop_impl
            if space.is_true(space.issubtype(w_typ2, w_typ1)):
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
    ('int', '__int__', ("space.w_int", "space.w_long")),
    ('index', '__index__', ("space.w_int", "space.w_long")),
    ('long', '__long__', ("space.w_int", "space.w_long")),
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
    ('repr', '__repr__'),
    ('oct', '__oct__'),
    ('hex', '__hex__')]:

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
