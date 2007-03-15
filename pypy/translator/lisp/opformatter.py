from pypy.rpython.ootypesystem.ootype import List, Dict, Record, Instance
from pypy.rpython.ootypesystem.ootype import DictItemsIterator
from pypy.translator.lisp.clrepr import clrepr

class OpFormatter:

    def __init__(self, gen, op):
        self.gen = gen
        self.op = op
        self.opname = op.opname
        self.args = op.args
        self.result = op.result

    def __iter__(self):
        method = getattr(self, "op_" + self.opname)
        result = clrepr(self.result)
        args = map(self.gen.check_declaration, self.args)
        for line in method(result, *args):
            yield line

    def nop(self, result, arg):
        yield "(setf %s %s)" % (result, arg)


    def op_debug_assert(self, result, *args):
        return []

    op_same_as = nop
    op_ooupcast = nop
    op_oodowncast = nop

    def make_unary_op(cl_op):
        def unary_op(self, result, arg):
            yield "(setf %s (%s %s))" % (result, cl_op, arg)
        return unary_op

    op_bool_not = make_unary_op("not")
    op_cast_char_to_int = make_unary_op("char-code")
    op_cast_int_to_char = make_unary_op("code-char")
    op_cast_float_to_int = make_unary_op("truncate")
    op_cast_int_to_float = make_unary_op("float")
    op_int_neg = make_unary_op("not")

    def make_binary_op(cl_op):
        def binary_op(self, result, arg1, arg2):
            yield "(setf %s (%s %s %s))" % (result, cl_op, arg1, arg2)
        return binary_op

    op_int_add = make_binary_op("+")
    op_int_sub = make_binary_op("-")
    op_int_mul = make_binary_op("*")
    op_int_floordiv = make_binary_op("truncate")
    op_int_eq = make_binary_op("=")
    op_int_gt = make_binary_op(">")
    op_int_ge = make_binary_op(">=")
    op_int_ne = make_binary_op("/=")
    op_int_lt = make_binary_op("<")
    op_int_le = make_binary_op("<=")
    op_int_and = make_binary_op("logand")
    op_int_mod = make_binary_op("mod")
    op_float_sub = make_binary_op("-")
    op_float_truediv = make_binary_op("/")
    op_char_eq = make_binary_op("char=")
    op_char_le = make_binary_op("char<=")
    op_char_ne = make_binary_op("char/=")

    def op_int_is_true(self, result, arg):
        yield "(setf %s (not (zerop %s)))" % (clrepr(result, True),
                                              clrepr(arg, True))

    def op_direct_call(self, result, _, *args):
        funobj = self.args[0].value
        self.gen.pendinggraphs.append(funobj)
        fun = clrepr(funobj._name, symbol=True)
        funcall = " ".join((fun,) + args)
        yield "(setf %s (%s))" % (result, funcall)

    def op_indirect_call(self, result, fun, *args):
        graphs = self.args[-1].value
        self.gen.pendinggraphs.extend(graphs)
        args = args[:-1]
        funcall = " ".join((fun,) + args)
        yield "(setf %s (funcall %s))" % (result, funcall)

    def op_new(self, result, _):
        cls = self.args[0].value
        if isinstance(cls, List):
            yield "(setf %s (make-array 0 :adjustable t))" % (result,)
        elif isinstance(cls, Dict):
            yield "(setf %s (make-hash-table))" % (result,)
        elif isinstance(cls, Record):
            clsname = self.gen.declare_struct(cls)
            yield "(setf %s (make-%s))" % (result, clsname)
        elif isinstance(cls, Instance):
            if self.gen.is_exception_instance(cls):
                clsname = self.gen.declare_exception(cls)
                yield "(setf %s (make-condition '%s))" % (result, clsname)
            else:
                clsname = self.gen.declare_class(cls)
                yield "(setf %s (make-instance '%s))" % (result, clsname)
        else:
            raise NotImplementedError("op_new on %s" % (cls,))

    def op_runtimenew(self, result, arg):
        yield "(setf %s (make-instance %s))" % (clrepr(result, True),
                                                clrepr(arg, True))

    def op_instanceof(self, result, arg, clsname):
        clsname = clrepr(self.args[1].value)
        yield "(setf %s (typep %s %s))" % (clrepr(result, True),
                                           clrepr(arg, True),
                                           clrepr(clsname, True))

    def op_oosend(self, result, _, selfvar, *args):
        method = self.args[0].value
        cls = self.args[1].concretetype
        if isinstance(cls, List):
            impl = ListImpl(selfvar)
            code = getattr(impl, method)(*args)
            yield "(setf %s %s)" % (result, code)
        elif isinstance(cls, Dict):
            impl = DictImpl(selfvar, self.gen)
            code = getattr(impl, method)(*args)
            yield "(setf %s %s)" % (result, code)
        elif isinstance(cls, DictItemsIterator):
            impl = DictItemsIteratorImpl(selfvar)
            code = getattr(impl, method)(*args)
            yield "(setf %s %s)" % (result, code)
        elif isinstance(cls, Instance):
            name = clrepr(method, symbol=True)
            funcall = " ".join((name, selfvar) + args)
            yield "(setf %s (%s))" % (result, funcall)
        else:
            raise NotImplementedError("op_oosend on %s" % (cls,))

    def op_oogetfield(self, result, obj, _):
        fieldname = self.args[1].value
        if isinstance(self.args[0].concretetype, Record):   
            yield "(setf %s (slot-value %s '%s))" % (clrepr(result, True),
                                                   clrepr(obj, True),
                                                   clrepr(fieldname, True))
        else:
            yield "(setf %s (%s %s))" % (clrepr(result, True),
                                         clrepr(fieldname, True),
                                         clrepr(obj, True))

    def op_oosetfield(self, result, obj, _, value):
        fieldname = self.args[1].value
        if isinstance(self.args[0].concretetype, Record):
            yield "(setf (slot-value %s '%s) %s)" % (clrepr(obj, True),
                                                     clrepr(fieldname, True),
                                                     clrepr(value, True))
        else:
            yield "(setf (%s %s) %s)" % (clrepr(fieldname, True),
                                         clrepr(obj, True),
                                         clrepr(value, True))

    def op_ooidentityhash(self, result, arg):
        yield "(setf %s (sxhash %s))" % (clrepr(result, True),
                                         clrepr(arg, True))

    def op_oononnull(self, result, arg):
        yield "(setf %s (not (null %s)))" % (clrepr(result, True),
                                             clrepr(arg, True))

class ListImpl:

    def __init__(self, obj):
        self.obj = obj

    def ll_length(self):
        return "(length %s)" % (self.obj,)

    def ll_getitem_fast(self, index):
        return "(aref %s %s)" % (self.obj, index)

    def ll_setitem_fast(self, index, value):
        return "(setf (aref %s %s) %s)" % (self.obj, index, value)
    
    def _ll_resize_le(self, size):
        return "(adjust-array %s %s)" % (self.obj, size)
    
    def _ll_resize_ge(self, size):
        return "(adjust-array %s %s)" % (self.obj, size)

    def _ll_resize(self, size):
        return "(adjust-array %s %s)" % (self.obj, size)

class DictImpl:

    def __init__(self, obj, gen):
        self.obj = obj
        self.gen = gen

    def ll_length(self):
        return "(hash-table-count %s)" % (self.obj,)

    def ll_contains(self, key):
        return "(nth-value 1 (gethash %s %s))" % (key, self.obj)

    def ll_get(self, key):
        return "(gethash %s %s)" % (key, self.obj)

    def ll_set(self, key, value):
        return "(setf (gethash %s %s) %s)" % (key, self.obj, value)

    def ll_get_items_iterator(self):
        # This is explicitly unspecified by the specification.
        # Should think of a better way to do this.
        name = self.gen.declare_dict_iter()
        return "(%s %s)" % (name, self.obj)

class DictItemsIteratorImpl:

    def __init__(self, obj):
        self.obj = obj

    def ll_go_next(self):
        return """\
(multiple-value-bind (more key value)
    (funcall (first %s))
  more)""" % (self.obj,)

    def ll_current_key(self):
        return "(funcall (second %s))" % (self.obj,)

    def ll_current_value(self):
        return "(funcall (third %s))" % (self.obj,)

