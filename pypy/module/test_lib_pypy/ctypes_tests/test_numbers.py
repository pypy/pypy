import py
from ctypes import *
from support import BaseCTypesTestChecker
import sys, struct

def valid_ranges(*types):
    # given a sequence of numeric types, collect their _type_
    # attribute, which is a single format character compatible with
    # the struct module, use the struct module to calculate the
    # minimum and maximum value allowed for this format.
    # Returns a list of (min, max) values.
    result = []
    for t in types:
        fmt = t._type_
        size = struct.calcsize(fmt)
        a = struct.unpack(fmt, ("\x00"*32)[:size])[0]
        b = struct.unpack(fmt, ("\xFF"*32)[:size])[0]
        c = struct.unpack(fmt, ("\x7F"+"\x00"*32)[:size])[0]
        d = struct.unpack(fmt, ("\x80"+"\xFF"*32)[:size])[0]
        result.append((min(a, b, c, d), max(a, b, c, d)))
    return result

ArgType = type(byref(c_int(0)))

unsigned_types = [c_ubyte, c_ushort, c_uint, c_ulong]
signed_types = [c_byte, c_short, c_int, c_long, c_longlong]

float_types = [c_double, c_float, c_longdouble]

try:
    c_ulonglong
    c_longlong
except NameError:
    pass
else:
    unsigned_types.append(c_ulonglong)
    signed_types.append(c_longlong)

unsigned_ranges = valid_ranges(*unsigned_types)
signed_ranges = valid_ranges(*signed_types)

################################################################

class TestNumber(BaseCTypesTestChecker):

    def test_default_init(self):
        # default values are set to zero
        for t in signed_types + unsigned_types + float_types:
            assert t().value == 0

    def test_unsigned_values(self):
        # the value given to the constructor is available
        # as the 'value' attribute
        for t, (l, h) in zip(unsigned_types, unsigned_ranges):
            assert t(l).value == l
            assert t(h).value == h

    def test_signed_values(self):
        # see above
        for t, (l, h) in zip(signed_types, signed_ranges):
            assert t(l).value == l
            assert t(h).value == h

    def test_typeerror(self):
        # Only numbers are allowed in the contructor,
        # otherwise TypeError is raised
        for t in signed_types + unsigned_types + float_types:
            raises(TypeError, t, "")
            raises(TypeError, t, None)

##    def test_valid_ranges(self):
##        # invalid values of the correct type
##        # raise ValueError (not OverflowError)
##        for t, (l, h) in zip(unsigned_types, unsigned_ranges):
##            self.assertRaises(ValueError, t, l-1)
##            self.assertRaises(ValueError, t, h+1)

    def test_from_param(self):
        # the from_param class method attribute always
        # returns PyCArgObject instances
        py.test.skip("testing implementation internals")
        for t in signed_types + unsigned_types + float_types:
            assert ArgType == type(t.from_param(0))

    def test_byref(self):
        # calling byref returns also a PyCArgObject instance
        py.test.skip("testing implementation internals")
        for t in signed_types + unsigned_types + float_types:
            parm = byref(t())
            assert ArgType == type(parm)

    def test_init_again(self):
        for t in signed_types + unsigned_types + float_types:
            parm = t()
            addr1 = addressof(parm)
            parm.__init__(0)
            addr2 = addressof(parm)
            assert addr1 == addr2

    def test_floats(self):
        # c_float and c_double can be created from
        # Python int, long and float
        for t in float_types:
            assert t(2.0).value == 2.0
            assert t(2).value == 2.0
            assert t(2L).value == 2.0

    def test_integers(self):
        # integers cannot be constructed from floats
        for t in signed_types + unsigned_types:
            raises(TypeError, t, 3.14)

    def test_sizes(self):
        for t in signed_types + unsigned_types + float_types:
            if t is c_longdouble:   # no support for 'g' in the struct module
                continue
            size = struct.calcsize(t._type_)
            # sizeof of the type...
            assert sizeof(t) == size
            # and sizeof of an instance
            assert sizeof(t()) == size

    def test_alignments(self):
        for t in signed_types + unsigned_types + float_types:
            if t is c_longdouble:   # no support for 'g' in the struct module
                continue
            code = t._type_ # the typecode
            align = struct.calcsize("c%c" % code) - struct.calcsize(code)

            # alignment of the type...
            assert (code, alignment(t)) == (code, align)
            # and alignment of an instance
            assert (code, alignment(t())) == (code, align)

    def test_int_from_address(self):
        from array import array
        for t in signed_types + unsigned_types:
            # the array module doesn't suppport all format codes
            # (no 'q' or 'Q')
            try:
                array(t._type_)
            except ValueError:
                continue
            a = array(t._type_, [100])

            # v now is an integer at an 'external' memory location
            v = t.from_address(a.buffer_info()[0])
            assert v.value == a[0]
            assert type(v) == t

            # changing the value at the memory location changes v's value also
            a[0] = 42
            assert v.value == a[0]


    def test_float_from_address(self):
        from array import array
        for t in float_types:
            if t is c_longdouble:   # no support for 'g' in the array module
                continue
            a = array(t._type_, [3.14])
            v = t.from_address(a.buffer_info()[0])
            assert v.value == a[0]
            assert type(v) is t
            a[0] = 2.3456e17
            assert v.value == a[0]
            assert type(v) is t

    def test_char_from_address(self):
        from ctypes import c_char
        from array import array

        a = array('c', 'x')
        v = c_char.from_address(a.buffer_info()[0])
        assert v.value == a[0]
        assert type(v) is c_char

        a[0] = '?'
        assert v.value == a[0]

    def test_init(self):
        # c_int() can be initialized from Python's int, and c_int.
        # Not from c_long or so, which seems strange, abd should
        # probably be changed:
        raises(TypeError, c_int, c_long(42))

##    def test_perf(self):
##        check_perf()

#from ctypes import _SimpleCData
#class c_int_S(_SimpleCData):
#    _type_ = "i"
#    __slots__ = []
