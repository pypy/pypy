import operator
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, BaseWrappable
from pypy.interpreter.function import Function
from pypy.interpreter.gateway import BuiltinCode
from pypy.interpreter.argument import Arguments
from pypy.tool.compile import compile2 

def raiseattrerror(space, w_obj, name, w_descr=None):
    w_type = space.type(w_obj)
    if w_descr is None:
        msg = "'%s' object has no attribute '%s'" %(w_type.name, name)
    else:
        msg = "'%s' object attribute '%s' is read-only" %(w_type.name, name)
    raise OperationError(space.w_AttributeError, space.wrap(msg))

class Object:
    def descr__getattribute__(space, w_obj, w_name):
        name = space.str_w(w_name)
        w_descr = space.lookup(w_obj, name)
        if w_descr is not None:
            if space.is_data_descr(w_descr):
                return space.get(w_descr, w_obj)
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
        w_dict = w_obj.getdict()
        if w_dict is not None:
            space.setitem(w_dict, w_name, w_value)
            return
        raiseattrerror(space, w_obj, name, w_descr)

    def descr__delattr__(space, w_obj, w_name):
        name = space.str_w(w_name)
        w_descr = space.lookup(w_obj, name)
        if w_descr is not None:
            if space.is_data_descr(w_descr):
                space.delete(w_descr, w_obj)
                return
        w_dict = w_obj.getdict()
        if w_dict is not None:
            try:
                space.delitem(w_dict, w_name)
                return
            except OperationError, ex:
                if not ex.match(space, space.w_KeyError):
                    raise
        raiseattrerror(space, w_obj, name, w_descr)

    def descr__init__(space, w_obj, __args__):
        pass

class DescrOperation:
    _mixin_ = True

    def setup_ec(space, ec):
        ec._compare_nesting = 0
        ec._cmp_state = {}

    def is_data_descr(space, w_obj):
        return space.lookup(w_obj, '__set__') is not None

    def get_and_call_args(space, w_descr, w_obj, args):
        descr = space.interpclass_w(w_descr)
        # a special case for performance and to avoid infinite recursion
        if type(descr) is Function:
            return descr.call_args(args.prepend(w_obj))
        else:
            w_impl = space.get(w_descr, w_obj)
            return space.call_args(w_impl, args)

    def get_and_call_function(space, w_descr, w_obj, *args_w):
        args = Arguments(space, list(args_w))
        return space.get_and_call_args(w_descr, w_obj, args)

    def call_args(space, w_obj, args):
        # a special case for performance
        if isinstance(w_obj, Function):
            return w_obj.call_args(args)
        w_descr = space.lookup(w_obj, '__call__')
        if w_descr is None:
            raise OperationError(
                space.w_TypeError, 
                space.mod(space.wrap('object %r is not callable'),
                          space.newtuple([w_obj])))
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
            raise OperationError(space.w_TypeError, 
                   space.wrap("object is not a descriptor with set"))
        return space.get_and_call_function(w_set, w_descr, w_obj, w_val)

    def delete(space, w_descr, w_obj):
        w_delete = space.lookup(w_descr, '__delete__')
        if w_delete is None:
            raise OperationError(space.w_TypeError,
                   space.wrap("object is not a descriptor with delete"))
        return space.get_and_call_function(w_delete, w_descr, w_obj)

    def getattr(space, w_obj, w_name):
        w_descr = space.lookup(w_obj, '__getattribute__')
        try:
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
            raise OperationError(space.w_AttributeError,
                   space.wrap("object is readonly"))
        return space.get_and_call_function(w_descr, w_obj, w_name, w_val)

    def delattr(space, w_obj, w_name):
        w_descr = space.lookup(w_obj, '__delattr__')
        if w_descr is None:
            raise OperationError(space.w_AttributeError,
                    space.wrap("object does not support attribute removal"))
        return space.get_and_call_function(w_descr, w_obj, w_name)

    def is_true(space, w_obj):
        if w_obj == space.w_False:
            return False
        if w_obj == space.w_True:
            return True
        if w_obj == space.w_None:
            return False
        w_descr = space.lookup(w_obj, '__nonzero__')
        if w_descr is None:
            w_descr = space.lookup(w_obj, '__len__')
            if w_descr is None:
                return True
        w_res = space.get_and_call_function(w_descr, w_obj)
        w_restype = space.type(w_res)
        if (space.is_w(w_restype, space.w_bool) or
            space.is_w(w_restype, space.w_int)):
            return space.is_true(w_res)
        else:
            raise OperationError(space.w_TypeError,
                                 space.wrap('__nonzero__ should return '
                                            'bool or int'))

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
                raise OperationError(space.w_TypeError,
                                     space.wrap("object is not iter()-able"))
            return space.newseqiter(w_obj)
        return space.get_and_call_function(w_descr, w_obj)

    def next(space, w_obj):
        w_descr = space.lookup(w_obj, 'next')
        if w_descr is None:
            raise OperationError(space.w_TypeError,
                   space.wrap("iterator has no next() method"))
        return space.get_and_call_function(w_descr, w_obj)

    def getitem(space, w_obj, w_key):
        w_descr = space.lookup(w_obj, '__getitem__')
        if w_descr is None:
            raise OperationError(space.w_TypeError,
                    space.wrap("cannot get items from object"))
        return space.get_and_call_function(w_descr, w_obj, w_key)

    def setitem(space, w_obj, w_key, w_val):
        w_descr = space.lookup(w_obj, '__setitem__')
        if w_descr is None:
            raise OperationError(space.w_TypeError,
                    space.wrap("cannot set items on object"))
        return space.get_and_call_function(w_descr, w_obj, w_key, w_val)

    def delitem(space, w_obj, w_key):
        w_descr = space.lookup(w_obj, '__delitem__')
        if w_descr is None:
            raise OperationError(space.w_TypeError,
                   space.wrap("cannot delete items from object"))
        return space.get_and_call_function(w_descr, w_obj, w_key)

    def pow(space, w_obj1, w_obj2, w_obj3):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_where(w_obj1, '__pow__')
        if space.is_true(space.is_(w_typ1, w_typ2)):
            w_right_impl = None
        else:
            w_right_src, w_right_impl = space.lookup_where(w_obj2, '__rpow__')
            if space.is_true(space.issubtype(w_typ2, w_typ1)) and not space.is_w(w_left_src, w_right_src):
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
        w_iter = space.iter(w_container)
        while 1:
            try:
                w_next = space.next(w_iter)
            except OperationError, e:
                if not e.match(space, space.w_StopIteration):
                    raise
                return space.w_False
            if space.is_true(space.eq(w_next, w_item)):
                return space.w_True
    
    def hash(space, w_obj):
        w_hash = space.lookup(w_obj, '__hash__')
        if w_hash is None:
            if space.lookup(w_obj, '__eq__') is not None or \
               space.lookup(w_obj, '__cmp__') is not None: 
                raise OperationError(space.w_TypeError, 
                                     space.wrap("unhashable type"))
            return space.id(w_obj) 
        w_result = space.get_and_call_function(w_hash, w_obj)
        if space.is_true(space.isinstance(w_result, space.w_int)): 
            return w_result 
        else: 
            raise OperationError(space.w_TypeError, 
                     space.wrap("__hash__() should return an int"))

    def userdel(space, w_obj):
        w_del = space.lookup(w_obj, '__del__')
        if w_del is not None:
            space.get_and_call_function(w_del, w_obj)

    _NESTING_LIMIT = 20

    def cmp(space, w_v, w_w):
        # Icky implementation trying to mimic python 2.3 semantics.

        if space.is_w(w_v, w_w):
            return space.wrap(0)

        w_vt = space.type(w_v)
        token = None
        _inprogress_dict = None

        ec = space.getexecutioncontext()
        ec._compare_nesting += 1
        _compare_nesting = ec._compare_nesting

        try:
            # Try to do some magic to compare cyclic constructs.
            if (_compare_nesting > space._NESTING_LIMIT and
                # dont't be subtle the corresponding condition in CPython is always true for heaptypes                
                # (space.lookup(w_v, '__getitem__') is not None) and
                not (space.is_w(w_vt, space.w_str) or
                     space.is_w(w_vt, space.w_tuple))):
                try:
                    iv = space.int_w(space.id(w_v))
                    iw = space.int_w(space.id(w_w))
                    if iv <= iw:
                        t = (iv, iw, -1)
                    else:
                        t = (iw, iv, -1)
                    _inprogress_dict = ec._cmp_state
                    if t in _inprogress_dict:
                        # If we are allready trying to compare the arguments
                        # presume they are equal
                        return space.wrap(0)
                    else:
                        token = _inprogress_dict[t] = t
                except:
                    return space.wrap(-1)
            try:
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
            finally:
                if token is not None:
                    try:
                        del _inprogress_dict[token]
                    except:
                        pass
        finally:
            ec._compare_nesting -= 1

    def coerce(space, w_obj1, w_obj2):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_where(w_obj1, '__coerce__')
        if space.is_true(space.is_(w_typ1, w_typ2)):
            w_right_impl = None
        else:
            w_right_src, w_right_impl = space.lookup_where(w_obj2, '__coerce__')
            if space.is_true(space.issubtype(w_typ2, w_typ1)) and not space.is_w(w_left_src, w_right_src):
                w_obj1, w_obj2 = w_obj2, w_obj1
                w_left_impl, w_right_impl = w_right_impl, w_left_impl

        w_res = _invoke_binop(space, w_left_impl, w_obj1, w_obj2)
        if w_res is None or space.is_w(w_res, space.w_None):
            w_res = _invoke_binop(space, w_right_impl, w_obj2, w_obj1)
            if w_res is None  or space.is_w(w_res, space.w_None):
                raise OperationError(space.w_TypeError,
                                     space.wrap("coercion failed"))
            if (not space.is_true(space.isinstance(w_res, space.w_tuple)) or
                space.int_w(space.len(w_res)) != 2):
                raise OperationError(space.w_TypeError,
                                     space.wrap("coercion should return None or 2-tuple"))
            w_res = space.newtuple([space.getitem(w_res, space.wrap(1)), space.getitem(w_res, space.wrap(0))])
        elif (not space.is_true(space.isinstance(w_res, space.w_tuple)) or
            space.int_w(space.len(w_res)) != 2):
            raise OperationError(space.w_TypeError,
                                 space.wrap("coercion should return None or 2-tuple"))
        return w_res
    


    # xxx ord



# helpers

def _check_notimplemented(space, w_obj):
    return not space.is_true(space.is_(w_obj, space.w_NotImplemented))

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

def _cmp(space, w_obj1, w_obj2):
    w_typ1 = space.type(w_obj1)
    w_typ2 = space.type(w_obj2)
    w_left_src, w_left_impl = space.lookup_where(w_obj1, '__cmp__')
    do_neg1 = False
    do_neg2 = True
    if space.is_true(space.is_(w_typ1, w_typ2)):
        w_right_impl = None
    else:
        w_right_src, w_right_impl = space.lookup_where(w_obj2, '__cmp__')
        if space.is_true(space.issubtype(w_typ2, w_typ1)) and not space.is_w(w_right_src, w_left_src):
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
    if space.is_true(space.is_(w_obj1, w_obj2)):
        return space.wrap(0)
    if space.is_true(space.is_(w_obj1, space.w_None)):
        return space.wrap(-1)
    if space.is_true(space.is_(w_obj2, space.w_None)):
        return space.wrap(1)
    if space.is_true(space.is_(w_typ1, w_typ2)):
        w_id1 = space.id(w_obj1)
        w_id2 = space.id(w_obj2)
    else:
        w_id1 = space.id(w_typ1)
        w_id2 = space.id(w_typ2)
    if space.is_true(space.lt(w_id1, w_id2)):
        return space.wrap(-1)
    else:
        return space.wrap(1)

# regular methods def helpers

from pypy.tool.hack import func_with_new_name

def _make_binop_impl(symbol, specialnames):
    left, right = specialnames
    def binop_impl(space, w_obj1, w_obj2):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_where(w_obj1, left)
        if space.is_true(space.is_(w_typ1, w_typ2)):
            w_right_impl = None
        else:
            w_right_src, w_right_impl = space.lookup_where(w_obj2, right)
            if space.is_true(space.issubtype(w_typ2, w_typ1)) and not space.is_w(w_right_src, w_left_src):
                w_obj1, w_obj2 = w_obj2, w_obj1
                w_left_impl, w_right_impl = w_right_impl, w_left_impl

        w_res = _invoke_binop(space, w_left_impl, w_obj1, w_obj2)
        if w_res is not None:
            return w_res
        w_res = _invoke_binop(space, w_right_impl, w_obj2, w_obj1)
        if w_res is not None:
            return w_res
        raise OperationError(space.w_TypeError,
                space.wrap("unsupported operand type(s) for %s" % symbol))
    return func_with_new_name(binop_impl, "binop_%s_impl"%left.strip('_'))

def _make_comparison_impl(symbol, specialnames):
    left, right = specialnames
    op = getattr(operator, left)
    def comparison_impl(space, w_obj1, w_obj2):
        w_typ1 = space.type(w_obj1)
        w_typ2 = space.type(w_obj2)
        w_left_src, w_left_impl = space.lookup_where(w_obj1, left)
        w_first = w_obj1
        w_second = w_obj2
        
        token = None
        _inprogress_dict = None

        ec = space.getexecutioncontext()
        ec._compare_nesting += 1
        _compare_nesting = ec._compare_nesting
        try:
            # Try to do some magic to compare cyclic constructs.
            if (_compare_nesting > space._NESTING_LIMIT and
                # dont't be subtle the corresponding condition in CPython is always true for heaptypes
                # (space.lookup(w_obj1, '__getitem__') is not None) and
                not (space.is_w(w_typ1, space.w_str) or
                     space.is_w(w_typ1, space.w_tuple))):
                i1 = space.int_w(space.id(w_obj1))
                i2 = space.int_w(space.id(w_obj2))
                if i1 <= i2:
                    t = (i1, i2, left)
                else:
                    t = (i2, i1, right)
                _inprogress_dict = ec._cmp_state
                if t in _inprogress_dict:
                    # If we are allready trying to compare the arguments
                    # presume they are equal
                    if symbol == '==':
                        return space.w_True
                    elif symbol == '!=':
                        return space.w_False
                    else:
                        raise OperationError(space.w_ValueError,
                                             space.wrap("can't order recursive values"))
                else:
                    token = _inprogress_dict[t] = t

            if space.is_true(space.is_(w_typ1, w_typ2)):
                w_right_impl = None
            else:
                w_right_src, w_right_impl = space.lookup_where(w_obj2, right)
                if space.is_true(space.issubtype(w_typ2, w_typ1)) and not space.is_w(w_right_src, w_left_src):
                    w_obj1, w_obj2 = w_obj2, w_obj1
                    w_left_impl, w_right_impl = w_right_impl, w_left_impl

            w_res = _invoke_binop(space, w_left_impl, w_obj1, w_obj2)
            if w_res is not None:
                return w_res
            w_res = _invoke_binop(space, w_right_impl, w_obj2, w_obj1)
            if w_res is not None:
                return w_res
            # fallback: lt(a, b) <= lt(cmp(a, b), 0) ...
            w_res = _cmp(space, w_first, w_second)
            res = space.int_w(w_res)
            return space.wrap(op(res, 0))
        finally:
            ec._compare_nesting -= 1 
            if token is not None:
                try:
                    del _inprogress_dict[token]
                except:
                    pass
                
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
    def unaryop_impl(space, w_obj):
        w_impl = space.lookup(w_obj, specialname)
        if w_impl is None:
            raise OperationError(space.w_TypeError,
                   space.wrap("operand does not support unary %s" % symbol))
        return space.get_and_call_function(w_impl, w_obj)
    return func_with_new_name(unaryop_impl, 'unaryop_%s_impl'%specialname.strip('_'))

# the following seven operations are really better to generate with
# string-templating (and maybe we should consider this for
# more of the above manually-coded operations as well) 

for targetname, specialname, checkerspec in [
    ('int', '__int__', ("space.w_int", "space.w_long")), 
    ('long', '__long__', ("space.w_int", "space.w_long")), 
    ('float', '__float__', ("space.w_float",)), 
    ('str', '__str__', ("space.w_str",)), 
    ('repr', '__repr__', ("space.w_str",)), 
    ('oct', '__oct__', ("space.w_str",)), 
    ('hex', '__hex__', ("space.w_str",))]: 

    l = ["space.is_true(space.isinstance(w_result, %s))" % x 
                for x in checkerspec]
    checker = " or ".join(l) 
    source = """if 1: 
        def %(targetname)s(space, w_obj):
            w_impl = space.lookup(w_obj, %(specialname)r) 
            if w_impl is None:
                raise OperationError(space.w_TypeError,
                       space.wrap("operand does not support unary %(targetname)s"))
            w_result = space.get_and_call_function(w_impl, w_obj)

            if %(checker)s: 
                return w_result
            typename = space.str_w(space.getattr(space.type(w_result), 
                                   space.wrap('__name__')))
            msg = '%(specialname)s returned non-%(targetname)s (type %%s)' %% (typename,) 
            raise OperationError(space.w_TypeError, space.wrap(msg)) 
        assert not hasattr(DescrOperation, %(targetname)r)
        DescrOperation.%(targetname)s = %(targetname)s
        del %(targetname)s 
        \n""" % locals() 
    exec compile2(source) 

# add default operation implementations for all still missing ops 

for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    if not hasattr(DescrOperation, _name):
        _impl_maker = None
        if _arity ==2 and _name in ['lt', 'le', 'gt', 'ge', 'ne', 'eq']:
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
                           'ord']:
            raise Exception, "missing def for operation%s" % _name
            
            

