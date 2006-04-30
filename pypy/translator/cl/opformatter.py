from pypy.rpython.ootypesystem.ootype import List, Record, Instance
from pypy.translator.cl.clrepr import clrepr

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

    def make_binary_op(cl_op):
        def binary_op(self, result, arg1, arg2):
            yield "(setf %s (%s %s %s))" % (result, cl_op, arg1, arg2)
        return binary_op

    op_int_add = make_binary_op("+")
    op_int_sub = make_binary_op("-")
    op_int_mul = make_binary_op("*")
    op_int_floordiv = make_binary_op("floor")
    op_int_eq = make_binary_op("=")
    op_int_gt = make_binary_op(">")
    op_int_ge = make_binary_op(">=")
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

    def op_direct_call(self, result, fun, *args):
        funobj = self.args[0].value
        self.gen.pendinggraphs.append(funobj)
        args = " ".join(args)
        yield "(setf %s (%s %s))" % (clrepr(result, True),
                                     clrepr(fun, True),
                                     clrepr(args, True))

    def op_new(self, result, _):
        cls = self.args[0].value
        if isinstance(cls, List):
            yield "(setf %s (make-array 0 :adjustable t))" % (result,)
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

    def op_oosend(self, result, *ignore):
        method = self.args[0].value
        receiver = self.args[1]
        cls = receiver.concretetype
        args = self.args[2:]
        if isinstance(cls, List):
            impl = ListImpl(receiver)
            code = getattr(impl, method)(*args)
            yield "(setf %s %s)" % (clrepr(result, True), clrepr(code, True))
        elif isinstance(cls, Instance):
            name = clrepr(method, symbol=True)
            selfvar = clrepr(receiver)
            args = map(self.gen.check_declaration, args)
            args = " ".join(args)
            if args:
                yield "(setf %s (%s %s %s))" % (clrepr(result, True),
                                                clrepr(name, True),
                                                clrepr(selfvar, True),
                                                clrepr(args, True))
            else:
                yield "(setf %s (%s %s))" % (clrepr(result, True),
                                             clrepr(name, True),
                                             clrepr(selfvar, True))

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

    def __init__(self, receiver):
        self.obj = clrepr(receiver)

    def ll_length(self):
        return "(length %s)" % (self.obj,)

    def ll_getitem_fast(self, index):
        index = clrepr(index)
        return "(aref %s %s)" % (self.obj, index)

    def ll_setitem_fast(self, index, value):
        index = clrepr(index)
        value = clrepr(value)
        return "(setf (aref %s %s) %s)" % (self.obj, index, value)

    def _ll_resize(self, size):
        size = clrepr(size)
        return "(adjust-array %s %s)" % (self.obj, size)
