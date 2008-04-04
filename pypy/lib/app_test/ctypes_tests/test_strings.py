
import py
from ctypes import *
from support import BaseCTypesTestChecker

class TestStringArray(BaseCTypesTestChecker):
    def test_one(self):
        BUF = c_char * 4

        buf = BUF("a", "b", "c")
        assert buf.value == "abc"
        assert buf.raw == "abc\000"

        buf.value = "ABCD"
        assert buf.value == "ABCD"
        assert buf.raw == "ABCD"

        buf.value = "x"
        assert buf.value == "x"
        assert buf.raw == "x\000CD"

        buf[1] = "Z"
        assert buf.value == "xZCD"
        assert buf.raw == "xZCD"

        py.test.raises(ValueError, setattr, buf, "value", "aaaaaaaa")
        py.test.raises(TypeError, setattr, buf, "value", 42)

    def test_c_buffer_value(self):
        buf = c_buffer(32)

        buf.value = "Hello, World"
        assert buf.value == "Hello, World"

    def test_c_buffer_raw(self):
        buf = c_buffer(32)

        buf.raw = "Hello, World"
        assert buf.value == "Hello, World"

    def test_param_1(self):
        BUF = c_char * 4
        buf = BUF()
##        print c_char_p.from_param(buf)

    def test_param_2(self):
        BUF = c_char * 4
        buf = BUF()
##        print BUF.from_param(c_char_p("python"))
##        print BUF.from_param(BUF(*"pyth"))

try:
    c_wchar
except NameError:
    pass
else:
    class TestWString(BaseCTypesTestChecker):
        def test(self):
            BUF = c_wchar * 4

            buf = BUF(u"a", u"b", u"c")
            assert buf.value == u"abc"

            buf.value = u"ABCD"
            assert buf.value == u"ABCD"

            buf.value = u"x"
            assert buf.value == u"x"

            buf[1] = u"Z"
            assert buf.value == u"xZCD"

# XXX write real tests for w_char


def run_test(rep, msg, func, arg):
    items = range(rep)
    from time import clock
    start = clock()
    for i in items:
        func(arg); func(arg); func(arg); func(arg); func(arg)
    stop = clock()
    print "%20s: %.2f us" % (msg, ((stop-start)*1e6/5/rep))

def check_perf():
    # Construct 5 objects

    REP = 200000

    run_test(REP, "c_string(None)", c_string, None)
    run_test(REP, "c_string('abc')", c_string, 'abc')

# Python 2.3 -OO, win2k, P4 700 MHz:
#
#      c_string(None): 1.75 us
#     c_string('abc'): 2.74 us

# Python 2.2 -OO, win2k, P4 700 MHz:
#
#      c_string(None): 2.95 us
#     c_string('abc'): 3.67 us


##    check_perf()
