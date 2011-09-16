from pypy.rlib import jit
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rstruct.error import StructError
from pypy.rlib.rstruct.formatiterator import FormatIterator
from pypy.rlib.rstruct.standardfmttable import PACK_ACCEPTS_BROKEN_INPUT
from pypy.interpreter.error import OperationError


class PackFormatIterator(FormatIterator):

    def __init__(self, space, args_w):
        self.space = space
        self.args_w = args_w
        self.args_index = 0
        self.result = []      # list of characters

    @jit.look_inside_iff(lambda self, fmtdesc, repetitions: jit.isconstant(repetitions))
    @specialize.arg(1)
    def operate(self, fmtdesc, repetitions):
        if fmtdesc.needcount:
            fmtdesc.pack(self, repetitions)
        else:
            for i in range(repetitions):
                fmtdesc.pack(self)
    _operate_is_specialized_ = True

    @jit.unroll_safe
    def align(self, mask):
        pad = (-len(self.result)) & mask
        for i in range(pad):
            self.result.append('\x00')

    def finished(self):
        if self.args_index != len(self.args_w):
            raise StructError("too many arguments for struct format")

    def accept_obj_arg(self):
        try:
            w_obj = self.args_w[self.args_index]
        except IndexError:
            raise StructError("struct format requires more arguments")
        self.args_index += 1
        return w_obj

    if PACK_ACCEPTS_BROKEN_INPUT:
        # permissive version - accepts float arguments too

        def accept_int_arg(self):
            return self._accept_integral("int_w")

        def accept_uint_arg(self):
            return self._accept_integral("uint_w")

        def accept_longlong_arg(self):
            return self._accept_integral("r_longlong_w")

        def accept_ulonglong_arg(self):
            return self._accept_integral("r_ulonglong_w")

        @specialize.arg(1)
        def _accept_integral(self, meth):
            space = self.space
            w_obj = self.accept_obj_arg()
            if (space.isinstance_w(w_obj, space.w_int) or
                space.isinstance_w(w_obj, space.w_long)):
                w_index = w_obj
            else:
                w_index = None
                w_index_method = space.lookup(w_obj, "__index__")
                if w_index_method is not None:
                    try:
                        w_index = space.index(w_obj)
                    except OperationError, e:
                        if not e.match(space, space.w_TypeError):
                            raise
                        pass
                if w_index is None:
                    w_index = self._maybe_float(w_obj)
            return getattr(space, meth)(w_index)

        def _maybe_float(self, w_obj):
            space = self.space
            if space.is_true(space.isinstance(w_obj, space.w_float)):
                space.warn("struct: integer argument expected, got float",
                           space.w_DeprecationWarning)
            else:
                space.warn("integer argument expected, got non-integer",
                           space.w_DeprecationWarning)
            return space.int(w_obj)   # wrapped float -> wrapped int or long

    else:
        # strict version

        def accept_int_arg(self):
            w_obj = self.accept_obj_arg()
            return self.space.int_w(w_obj)

        def accept_uint_arg(self):
            w_obj = self.accept_obj_arg()
            return self.space.uint_w(w_obj)

        def accept_longlong_arg(self):
            w_obj = self.accept_obj_arg()
            return self.space.r_longlong_w(w_obj)

        def accept_ulonglong_arg(self):
            w_obj = self.accept_obj_arg()
            return self.space.r_ulonglong_w(w_obj)

    def accept_bool_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.is_true(w_obj)

    def accept_str_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.str_w(w_obj)

    def accept_unicode_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.unicode_w(w_obj)

    def accept_float_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.float_w(w_obj)


class UnpackFormatIterator(FormatIterator):

    def __init__(self, space, input):
        self.space = space
        self.input = input
        self.inputpos = 0
        self.result_w = []     # list of wrapped objects

    def operate(self, fmtdesc, repetitions):
        if fmtdesc.needcount:
            fmtdesc.unpack(self, repetitions)
        else:
            for i in range(repetitions):
                fmtdesc.unpack(self)
    operate._annspecialcase_ = 'specialize:arg(1)'
    _operate_is_specialized_ = True

    def align(self, mask):
        self.inputpos = (self.inputpos + mask) & ~mask

    def finished(self):
        if self.inputpos != len(self.input):
            raise StructError("unpack str size too long for format")

    def read(self, count):
        end = self.inputpos + count
        if end > len(self.input):
            raise StructError("unpack str size too short for format")
        s = self.input[self.inputpos : end]
        self.inputpos = end
        return s

    def appendobj(self, value):
        self.result_w.append(self.space.wrap(value))
    appendobj._annspecialcase_ = 'specialize:argtype(1)'

