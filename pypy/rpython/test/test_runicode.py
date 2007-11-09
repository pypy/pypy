

from pypy.rpython.test.tool import LLRtypeMixin, OORtypeMixin
from pypy.rpython.test.test_rstr import AbstractTestRstr
import py

# ====> test_rstr.py

class BaseTestRUnicode(AbstractTestRstr):
    const = unicode
    constchar = unichr

    def test_unicode_explicit_conv(self):
        def f(x):
            return unicode(x)

        for v in ['x', u'x']:
            res = self.interpret(f, [v])
            assert self.ll_to_unicode(res) == v

        def f(x):
            if x > 1:
                y = const('yxx')
            else:
                y = const('xx')
            return unicode(y)
        
        const = str
        assert self.ll_to_unicode(self.interpret(f, [1])) == f(1)

        def f(x):
            if x > 1:
                y = const('yxx')
            else:
                y = const('xx')
            return unicode(y)

        # a copy, because llinterp caches functions

        const = unicode
        assert self.ll_to_unicode(self.interpret(f, [1])) == f(1)

    def test_str_unicode_const(self):
        def f():
            return str(u'xxx')

        assert self.ll_to_string(self.interpret(f, [])) == 'xxx'

    def test_conversion_errors(self):
        py.test.skip("do we want this test to pass?")
        def f(x):
            if x:
                string = '\x80\x81'
                uni = u'\x80\x81'
            else:
                string = '\x82\x83'
                uni = u'\x83\x84\x84'
            try:
                str(uni)
            except UnicodeEncodeError:
                pass
            else:
                return -1
            try:
                unicode(string)
            except UnicodeDecodeError:
                return len(string) + len(uni)
            else:
                return -2
        assert f(True) == 4
        assert f(False) == 5
        res = self.interpret(f, [True])
        assert res == 4


    def test_str_unicode_nonconst(self):
        def f(x):
            y = u'xxx' + unichr(x)
            return str(y)

        assert self.ll_to_string(self.interpret(f, [38])) == f(38)
        self.interpret_raises(UnicodeEncodeError, f, [1234])

    def test_unicode_encode(self):
        def f(x):
            y = u'xxx'
            return (y + unichr(x)).encode('ascii')

        assert self.ll_to_string(self.interpret(f, [38])) == f(38)

    def test_unicode_encode_error(self):
        def f(x):
            y = u'xxx'
            try:
                x = (y + unichr(x)).encode('ascii')
                return len(x)
            except UnicodeEncodeError:
                return -1

        assert self.interpret(f, [38]) == f(38)
        assert self.interpret(f, [138]) == f(138)

    def test_unicode_decode(self):
        def f(x):
            y = 'xxx'
            return (y + chr(x)).decode('ascii')

        assert self.ll_to_string(self.interpret(f, [38])) == f(38)

    def test_unicode_decode_error(self):
        def f(x):
            y = 'xxx'
            try:
                x = (y + chr(x)).decode('ascii')
                return len(x)
            except UnicodeDecodeError:
                return -1

        assert self.interpret(f, [38]) == f(38)
        assert self.interpret(f, [138]) == f(138)


    def test_unichar_const(self):
        def fn(c):
            return c
        assert self.interpret(fn, [u'\u03b1']) == u'\u03b1'

    def test_unichar_eq(self):
        def fn(c1, c2):
            return c1 == c2
        assert self.interpret(fn, [u'\u03b1', u'\u03b1']) == True
        assert self.interpret(fn, [u'\u03b1', u'\u03b2']) == False

    def test_unichar_ord(self):
        def fn(c):
            return ord(c)
        assert self.interpret(fn, [u'\u03b1']) == ord(u'\u03b1')

    def test_unichar_hash(self):
        def fn(c):
            d = {c: 42}
            return d[c]
        assert self.interpret(fn, [u'\u03b1']) == 42

    def test_convert_char_to_unichar(self):
        def g(c):
            return ord(c)
        def fn(n):
            if n < 0:
                c = unichr(-n)
            else:
                c = chr(n)
            return g(c)
        assert self.interpret(fn, [65]) == 65
        assert self.interpret(fn, [-5555]) == 5555

    def test_char_unichar_eq(self):
        def fn(c1, c2):
            return c1 == c2
        assert self.interpret(fn, [u'(', '(']) == True
        assert self.interpret(fn, [u'\u1028', '(']) == False
        assert self.interpret(fn, ['(', u'(']) == True
        assert self.interpret(fn, ['(', u'\u1028']) == False

    def test_char_unichar_eq_2(self):
        def fn(c1):
            return c1 == 'X'
        assert self.interpret(fn, [u'(']) == False
        assert self.interpret(fn, [u'\u1058']) == False
        assert self.interpret(fn, [u'X']) == True
    
    def unsupported(self):
        py.test.skip("not supported")

    test_char_isxxx = unsupported
    test_upper = unsupported
    test_lower = unsupported
    test_strformat = unsupported
    test_strformat_instance = unsupported
    test_strformat_nontuple = unsupported
    test_percentformat_instance = unsupported
    test_percentformat_tuple = unsupported
    test_percentformat_list = unsupported
    test_int = unsupported
    test_int_valueerror = unsupported
    test_float = unsupported
    test_hlstr = unsupported

class TestLLtype(BaseTestRUnicode, LLRtypeMixin):
    EMPTY_STRING_HASH = -1

class TestOOtype(BaseTestRUnicode, OORtypeMixin):
    EMPTY_STRING_HASH = 0
