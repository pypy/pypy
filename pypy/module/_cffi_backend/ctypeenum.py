"""
Enums.
"""

from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rpython.lltypesystem import rffi
from pypy.rlib.rarithmetic import intmask, r_ulonglong
from pypy.rlib.objectmodel import keepalive_until_here

from pypy.module._cffi_backend.ctypeprim import W_CTypePrimitiveSigned
from pypy.module._cffi_backend import misc


class W_CTypeEnum(W_CTypePrimitiveSigned):
    _attrs_            = ['enumerators2values', 'enumvalues2erators']
    _immutable_fields_ = ['enumerators2values', 'enumvalues2erators']
    kind = "enum"

    def __init__(self, space, name, enumerators, enumvalues):
        from pypy.module._cffi_backend.newtype import alignment
        name = "enum " + name
        size = rffi.sizeof(rffi.INT)
        align = alignment(rffi.INT)
        W_CTypePrimitiveSigned.__init__(self, space, size,
                                        name, len(name), align)
        self.enumerators2values = {}   # str -> int
        self.enumvalues2erators = {}   # int -> str
        for i in range(len(enumerators)-1, -1, -1):
            self.enumerators2values[enumerators[i]] = enumvalues[i]
            self.enumvalues2erators[enumvalues[i]] = enumerators[i]

    def _fget(self, attrchar):
        if attrchar == 'e':     # elements
            space = self.space
            w_dct = space.newdict()
            for enumvalue, enumerator in self.enumvalues2erators.iteritems():
                space.setitem(w_dct, space.wrap(enumvalue),
                                     space.wrap(enumerator))
            return w_dct
        if attrchar == 'R':     # relements
            space = self.space
            w_dct = space.newdict()
            for enumerator, enumvalue in self.enumerators2values.iteritems():
                space.setitem(w_dct, space.wrap(enumerator),
                                     space.wrap(enumvalue))
            return w_dct
        return W_CTypePrimitiveSigned._fget(self, attrchar)

    def string(self, cdataobj, maxlen):
        w_result = self.convert_to_object(cdataobj._cdata)
        keepalive_until_here(cdataobj)
        return w_result

    def convert_to_object(self, cdata):
        value = misc.read_raw_long_data(cdata, self.size)
        try:
            enumerator = self.enumvalues2erators[value]
        except KeyError:
            enumerator = '#%d' % (value,)
        return self.space.wrap(enumerator)

    def convert_from_object(self, cdata, w_ob):
        space = self.space
        try:
            return W_CTypePrimitiveSigned.convert_from_object(self, cdata,
                                                              w_ob)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
        if space.isinstance_w(w_ob, space.w_basestring):
            value = self.convert_enum_string_to_int(space.str_w(w_ob))
            value = r_ulonglong(value)
            misc.write_raw_integer_data(cdata, value, self.size)
        else:
            raise self._convert_error("str or int", w_ob)

    def cast_str(self, w_ob):
        space = self.space
        return self.convert_enum_string_to_int(space.str_w(w_ob))

    def cast_unicode(self, w_ob):
        return self.cast_str(w_ob)

    def convert_enum_string_to_int(self, s):
        space = self.space
        if s.startswith('#'):
            try:
                return int(s[1:])
            except ValueError:
                raise OperationError(space.w_ValueError,
                                     space.wrap("invalid literal after '#'"))
        else:
            try:
                return self.enumerators2values[s]
            except KeyError:
                raise operationerrfmt(space.w_ValueError,
                                      "'%s' is not an enumerator for %s",
                                      s, self.name)
