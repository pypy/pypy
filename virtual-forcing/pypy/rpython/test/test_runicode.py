
from pypy.rpython.lltypesystem.lltype import malloc
from pypy.rpython.lltypesystem.rstr import LLHelpers, UNICODE
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

    def test_unicode_of_unicode(self):
        def f(x):
            return len(unicode(unichr(x) * 3))
        assert self.interpret(f, [ord('a')]) == 3
        assert self.interpret(f, [128]) == 3
        assert self.interpret(f, [1000]) == 3

    def test_unicode_of_unichar(self):
        def f(x):
            return len(unicode(unichr(x)))
        assert self.interpret(f, [ord('a')]) == 1
        assert self.interpret(f, [128]) == 1
        assert self.interpret(f, [1000]) == 1

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
            return (y + unichr(x)).encode('ascii') + y.encode('latin-1')

        assert self.ll_to_string(self.interpret(f, [38])) == f(38)

    def test_unicode_encode_error(self):
        def f(x, which):
            if which:
                y = u'xxx'
                try:
                    x = (y + unichr(x)).encode('ascii')
                    return len(x)
                except UnicodeEncodeError:
                    return -1
            else:
                y = u'xxx'
                try:
                    x = (y + unichr(x)).encode('latin-1')
                    return len(x)
                except UnicodeEncodeError:
                    return -1

        assert self.interpret(f, [38, True]) == f(38, True)
        assert self.interpret(f, [138, True]) == f(138, True)
        assert self.interpret(f, [38, False]) == f(38, False)
        assert self.interpret(f, [138, False]) == f(138, False)
        assert self.interpret(f, [300, False]) == f(300, False)

    def test_unicode_decode(self):
        def f(x):
            y = 'xxx'
            return (y + chr(x)).decode('ascii') + chr(x).decode("latin-1") 

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
    test_splitlines = unsupported
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

    def test_hash_via_type(self):
        from pypy.rlib.objectmodel import compute_hash

        def f(n):
            s = malloc(UNICODE, n)
            s.hash = 0
            for i in range(n):
                s.chars[i] = unichr(ord('A') + i)
            return s.gethash() - compute_hash(u'ABCDE')

        res = self.interpret(f, [5])
        assert res == 0

class TestOOtype(BaseTestRUnicode, OORtypeMixin):
    pass
