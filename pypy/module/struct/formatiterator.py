from rpython.rlib import jit
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.rstruct.error import StructError
from rpython.rlib.rstruct.formatiterator import FormatIterator

from pypy.interpreter.error import OperationError


class PackFormatIterator(FormatIterator):

    def __init__(self, space, args_w, size):
        self.space = space
        self.args_w = args_w
        self.args_index = 0
        self.result = StringBuilder(size)

    # This *should* be always unroll safe, the only way to get here is by
    # unroll the interpret function, which means the fmt is const, and thus
    # this should be const (in theory ;)
    @jit.unroll_safe
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
        pad = (-self.result.getlength()) & mask
        self.result.append_multiple_char('\x00', pad)

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
        if space.isinstance_w(w_obj, space.w_float):
            msg = "struct: integer argument expected, got float"
        else:
            msg = "integer argument expected, got non-integer"
        space.warn(space.wrap(msg), space.w_DeprecationWarning)
        return space.int(w_obj)   # wrapped float -> wrapped int or long

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

    # See above comment on operate.
    @jit.unroll_safe
    @specialize.arg(1)
    def operate(self, fmtdesc, repetitions):
        if fmtdesc.needcount:
            fmtdesc.unpack(self, repetitions)
        else:
            for i in range(repetitions):
                fmtdesc.unpack(self)
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

    @specialize.argtype(1)
    def appendobj(self, value):
        self.result_w.append(self.space.wrap(value))
