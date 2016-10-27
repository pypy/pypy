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
            if space.lookup(w_obj, '__index__'):
                try:
                    w_index = space.index(w_obj)
                except OperationError as e:
                    if not e.match(space, space.w_TypeError):
                        raise
                    pass
            if w_index is None and space.lookup(w_obj, '__int__'):
                if space.isinstance_w(w_obj, space.w_float):
                    msg = "integer argument expected, got float"
                else:
                    msg = "integer argument expected, got non-integer" \
                          " (implicit conversion using __int__ is deprecated)"
                space.warn(space.wrap(msg), space.w_DeprecationWarning)
                w_index = space.int(w_obj)   # wrapped float -> wrapped int or long
            if w_index is None:
                raise StructError("cannot convert argument to integer")
        method = getattr(space, meth)
        try:
            return method(w_index)
        except OperationError as e:
            if e.match(self.space, self.space.w_OverflowError):
                raise StructError("argument out of range")
            raise

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
        try:
            return self.space.float_w(w_obj)
        except OperationError as e:
            if e.match(self.space, self.space.w_TypeError):
                raise StructError("required argument is not a float")
            raise


class UnpackFormatIterator(FormatIterator):
    def __init__(self, space, buf):
        self.space = space
        self.buf = buf
        self.length = buf.getlength()
        self.pos = 0
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
        self.pos = (self.pos + mask) & ~mask

    def finished(self):
        if self.pos != self.length:
            raise StructError("unpack str size too long for format")

    def read(self, count):
        end = self.pos + count
        if end > self.length:
            raise StructError("unpack str size too short for format")
        s = self.buf.getslice(self.pos, end, 1, count)
        self.pos = end
        return s

    @specialize.argtype(1)
    def appendobj(self, value):
        from rpython.rlib.rarithmetic import r_uint, maxint, intmask
        if isinstance(value, r_uint):
            # native-size uint: try to wrap it inside a native int if it fits,
            # as CPython does
            if value <= maxint:
                w_value = self.space.wrap(intmask(value))
            else:
                w_value = self.space.wrap(value)
        else:
            w_value = self.space.wrap(value)
        #
        self.result_w.append(w_value)

    def get_pos(self):
        return self.pos

    def get_buffer_as_string_maybe(self):
        string, pos = self.buf.as_str_and_offset_maybe()
        return string, pos+self.pos

    def skip(self, size):
        self.read(size) # XXX, could avoid taking the slice
