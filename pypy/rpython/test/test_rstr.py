import random
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.rstr import AbstractLLHelpers
from pypy.rpython.lltypesystem.rstr import LLHelpers, STR
from pypy.rpython.rtyper import RPythonTyper, TyperError
from pypy.rpython.test.test_llinterp import interpret, interpret_raises
from pypy.rpython.llinterp import LLException

def llstr(s):
    p = malloc(STR, len(s))
    for i in range(len(s)):
        p.chars[i] = s[i]
    return p

def test_ll_find_rfind():
    for i in range(50):
        n1 = random.randint(0, 10)
        s1 = ''.join([random.choice("ab") for i in range(n1)])
        n2 = random.randint(0, 5)
        s2 = ''.join([random.choice("ab") for i in range(n2)])
        res = LLHelpers.ll_find(llstr(s1), llstr(s2), 0, n1)
        assert res == s1.find(s2)
        res = LLHelpers.ll_rfind(llstr(s1), llstr(s2), 0, n1)
        assert res == s1.rfind(s2)

def test_parse_fmt():
    assert AbstractLLHelpers.parse_fmt_string('a') == ['a']
    assert AbstractLLHelpers.parse_fmt_string('%s') == [('s',)]
    assert AbstractLLHelpers.parse_fmt_string("name '%s' is not defined") == ["name '", ("s",), "' is not defined"]


class AbstractTestRstr:

    def interpret(self, fn, args):
        return interpret(fn, args, type_system=self.ts)

    def interpret_raises(self, exc, fn, args):
        return interpret_raises(exc, fn, args, type_system=self.ts)

    def _skip_oo(self, reason):
        if self.ts == 'ootype':
            py.test.skip("ootypesystem doesn't support %s, yet" % reason)

    def test_simple(self):
        def fn(i):
            s = 'hello'
            return s[i]
        for i in range(5):
            res = self.interpret(fn, [i])
            assert res == 'hello'[i]

    def test_implicit_index_error(self):
        def fn(i):
            s = 'hello'
            try:
                return s[i]
            except IndexError:
                return '*'
        for i in range(-5, 5):
            res = self.interpret(fn, [i])
            assert res == 'hello'[i]
        res = self.interpret(fn, [5])
        assert res == '*'
        res = self.interpret(fn, [6])
        assert res == '*'
        res = self.interpret(fn, [-42])
        assert res == '*'

    def test_nonzero(self):
        def fn(i, j):
            s = ['', 'xx'][j]
            if i < 0:
                s = None
            if i > -2:
                return bool(s)
            else:
                return False
        for i in [-2, -1, 0]:
            for j in range(2):
                res = self.interpret(fn, [i, j])
                assert res is fn(i, j)

    def test_concat(self):
        def fn(i, j):
            s1 = ['', 'a', 'ab']
            s2 = ['', 'x', 'xy']
            return s1[i] + s2[j]
        for i in range(3):
            for j in range(3):
                res = self.interpret(fn, [i,j])
                assert self.ll_to_string(res) == fn(i, j)

    def test_iter(self):
        def fn(i):
            s = ['', 'a', 'hello'][i]
            i = 0
            for c in s:
                if c != s[i]:
                    return False
                i += 1
            if i == len(s):
                return True
            return False

        for i in range(3):
            res = self.interpret(fn, [i])
            assert res is True
        
    def test_char_constant(self):
        def fn(s):
            return s + '.'
        res = self.interpret(fn, ['x'])
        res = self.ll_to_string(res)
        assert len(res) == 2
        assert res[0] == 'x'
        assert res[1] == '.'

    def test_char_isxxx(self):
        def fn(s):
            return (s.isspace()      |
                    s.isdigit() << 1 |
                    s.isalpha() << 2 |
                    s.isalnum() << 3 |
                    s.isupper() << 4 |
                    s.islower() << 5)
        for i in range(128):
            ch = chr(i)
            res = self.interpret(fn, [ch])
            assert res == fn(ch)

    def test_char_compare(self):
        res = self.interpret(lambda c1, c2: c1 == c2,  ['a', 'b'])
        assert res is False
        res = self.interpret(lambda c1, c2: c1 == c2,  ['a', 'a'])
        assert res is True
        res = self.interpret(lambda c1, c2: c1 <= c2,  ['z', 'a'])
        assert res is False

    def test_char_mul(self):
        def fn(c, mul):
            s = c * mul
            res = 0
            for i in range(len(s)):
                res = res*10 + ord(s[i]) - ord('0')
            c2 = c
            c2 *= mul
            res = 10 * res + (c2 == s)
            return res
        res = self.interpret(fn, ['3', 5])
        assert res == 333331
        res = self.interpret(fn, ['5', 3])
        assert res == 5551

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

    def test_is_none(self):
        def fn(i):
            s1 = ['foo', None][i]
            return s1 is None
        assert self.interpret(fn, [0]) == False
        assert self.interpret(fn, [1]) == True

    def test_str_compare(self):
        def fn(i, j):
            s1 = ['one', 'two', None]
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar', None]
            return s1[i] == s2[j]
        for i in range(3):
            for j in range(7):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] != s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i, j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] < s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] <= s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] >= s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
            return s1[i] > s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

    def test_startswith(self):
        def fn(i, j):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
            return s1[i].startswith(s2[j])
        for i in range(2):
            for j in range(9):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

    def test_endswith(self):
        def fn(i, j):
            s1 = ['one', 'two']
            s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
            return s1[i].endswith(s2[j])
        for i in range(2):
            for j in range(9):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

    def test_find(self):
        def fn(i, j):
            s1 = ['one two three', 'abc abcdab abcdabcdabde']
            s2 = ['one', 'two', 'abcdab', 'one tou', 'abcdefgh', 'fortytwo', '']
            return s1[i].find(s2[j])
        for i in range(2):
            for j in range(7):
                res = self.interpret(fn, [i,j])
                assert res == fn(i, j)

    def test_find_with_start(self):
        self._skip_oo('assert')
        def fn(i):
            assert i >= 0
            return 'ababcabc'.find('abc', i)
        for i in range(9):
            res = self.interpret(fn, [i])
            assert res == fn(i)

    def test_find_with_start_end(self):
        self._skip_oo('assert')
        def fn(i, j):
            assert i >= 0
            assert j >= 0
            return 'ababcabc'.find('abc', i, j)
        for (i, j) in [(1,7), (2,6), (3,7), (3,8)]:
            res = self.interpret(fn, [i, j])
            assert res == fn(i, j)

    def test_rfind(self):
        def fn():
            return 'aaa'.rfind('a') + 'aaa'.rfind('a', 1) + 'aaa'.rfind('a', 1, 2)
        res = self.interpret(fn, [])
        assert res == 2 + 2 + 1

    def test_find_char(self):
        def fn(ch):
            pos1 = 'aiuwraz 483'.find(ch)
            pos2 = 'aiuwraz 483'.rfind(ch)
            return pos1 + (pos2*100)
        for ch in 'a ?3':
            res = self.interpret(fn, [ch])
            assert res == fn(ch)

    def test_strip(self):
        def both():
            return '!ab!'.strip('!')
        def left():
            return '!ab!'.lstrip('!')
        def right():
            return '!ab!'.rstrip('!')
        res = self.interpret(both, [])
        assert self.ll_to_string(res) == 'ab'
        res = self.interpret(left, [])
        assert self.ll_to_string(res) == 'ab!'
        res = self.interpret(right, [])
        assert self.ll_to_string(res) == '!ab'

    def test_upper(self):
        strings = ['', ' ', 'upper', 'UpPeR', ',uppEr,']
        for i in range(256): strings.append(chr(i))
        def fn(i):
            return strings[i].upper()
        for i in range(len(strings)):
            res = self.interpret(fn, [i])
            assert self.ll_to_string(res) == fn(i)

    def test_lower(self):
        strings = ['', ' ', 'lower', 'LoWeR', ',lowEr,']
        for i in range(256): strings.append(chr(i))
        def fn(i):
            return strings[i].lower()
        for i in range(len(strings)):
            res = self.interpret(fn, [i])
            assert self.ll_to_string(res) == fn(i)

    def test_join(self):
        res = self.interpret(lambda: ''.join([]), [])
        assert self.ll_to_string(res) == ""

        res = self.interpret(lambda: ''.join(['a', 'b', 'c']), [])
        assert self.ll_to_string(res) == "abc"

        res = self.interpret(lambda: ''.join(['abc', 'de', 'fghi']), [])
        assert self.ll_to_string(res) == "abcdefghi"

        res = self.interpret(lambda: '.'.join(['abc', 'def']), [])
        assert self.ll_to_string(res) == 'abc.def'

        def fn(i, j):
            s1 = [ '', ',', ' and ']
            s2 = [ [], ['foo'], ['bar', 'baz', 'bazz']]
            return s1[i].join(s2[j])
        for i in range(3):
            for j in range(3):
                res = self.interpret(fn, [i,j])
                assert self.ll_to_string(res) == fn(i, j)

        def fn(i, j):
            s1 = [ '', ',', ' and ']
            s2 = [ [], ['foo'], ['bar', 'baz', 'bazz']]
            s2[1].extend(['x'])
            return s1[i].join(s2[j])
        for i in range(3):
            for j in range(3):
                res = self.interpret(fn, [i,j])
                assert self.ll_to_string(res) == fn(i, j)

    def test_str_slice(self):
        def fn():
            s = 'hello'
            s1 = s[:3]
            s2 = s[3:]
            s3 = s[3:10]
            return s1+s2 == s and s2+s1 == 'lohel' and s1+s3 == s
        res = self.interpret(fn, ())
        assert res

    def test_str_slice_minusone(self):
        def fn():
            s = 'hello'
            z = 'h'
            return s[:-1]+z[:-1]
        res = self.interpret(fn, ())
        assert self.ll_to_string(res) == 'hell'


    def test_strformat(self):
        def percentS(s):
            return "before %s after" % (s,)

        res = self.interpret(percentS, ['1'])
        assert self.ll_to_string(res) == 'before 1 after'

        def percentD(i):
            return "bing %d bang" % (i,)

        res = self.interpret(percentD, [23])
        assert self.ll_to_string(res) == 'bing 23 bang'

        def percentX(i):
            return "bing %x bang" % (i,)

        res = self.interpret(percentX, [23])
        assert self.ll_to_string(res) == 'bing 17 bang'

        res = self.interpret(percentX, [-123])
        assert self.ll_to_string(res) == 'bing -7b bang'

        def percentO(i):
            return "bing %o bang" % (i,)

        res = self.interpret(percentO, [23])
        assert self.ll_to_string(res) == 'bing 27 bang'

        res = self.interpret(percentO, [-123])
        assert self.ll_to_string(res) == 'bing -173 bang'

        def moreThanOne(s, d, x, o):
            return "string: %s decimal: %d hex: %x oct: %o" % (s, d, x, o)

        args = 'a', 2, 3, 4
        res = self.interpret(moreThanOne, list(args))
        assert self.ll_to_string(res) == moreThanOne(*args)

    def test_strformat_nontuple(self):
        def percentD(i):
            return "before %d after" % i

        res = self.interpret(percentD, [1])
        assert self.ll_to_string(res) == 'before 1 after'

        def percentS(i):
            return "before %s after" % i

        res = self.interpret(percentS, ['D'])
        assert self.ll_to_string(res) == 'before D after'

    def test_strformat_instance(self):
        class C:
            pass
        class D(C):
            pass
        def dummy(i):
            if i:
                x = C()
            else:
                x = D()
            return str(x)

        res = self.ll_to_string(self.interpret(dummy, [1]))
        assert res.startswith('<')
        assert res.endswith('C object>')

        res = self.ll_to_string(self.interpret(dummy, [0]))
        assert res.startswith('<')
        assert res.endswith('D object>')

    def test_percentformat_instance(self):
        class C:
            pass
        class D(C):
            pass

        def dummy(i):
            if i:
                x = C()
                y = D()
            else:
                x = D()
                y = C()
            return "what a nice %s, much nicer than %r"%(x, y)

        res = self.ll_to_string(self.interpret(dummy, [1]))
        res = res.replace('pypy.rpython.test.test_rstr.', '')
        assert res == 'what a nice <C object>, much nicer than <D object>'

        res = self.ll_to_string(self.interpret(dummy, [0]))
        res = res.replace('pypy.rpython.test.test_rstr.', '')        
        assert res == 'what a nice <D object>, much nicer than <C object>'

    def test_split(self):
        def fn(i):
            s = ['', '0.1.2.4.8', '.1.2', '1.2.', '.1.2.4.'][i]
            l = s.split('.')
            sum = 0
            for num in l:
                 if len(num):
                     sum += ord(num) - ord('0')
            return sum + len(l) * 100
        for i in range(5):
            res = self.interpret(fn, [i])
            assert res == fn(i)

    def test_contains(self):
        def fn(i):
            s = 'Hello world'
            return chr(i) in s
        for i in range(256):
            res = self.interpret(fn, [i])#, view=i==42)
            assert res == fn(i)

    def test_replace(self):
        def fn(c1, c2):
            s = 'abbccc'
            s = s.replace(c1, c2)
            res = 0
            for c in s:
                if c == c2:
                    res += 1
            return res
        res = self.interpret(fn, ['a', 'c'])
        assert res == 4
        res = self.interpret(fn, ['c', 'b'])
        assert res == 5
        def fn():
            s = 'abbccc'
            s = s.replace('a', 'baz')
        raises (TyperError, interpret, fn, ())
        def fn():
            s = 'abbccc'
            s = s.replace('abb', 'c')
        raises (TyperError, interpret, fn, ())

    def test_int(self):
        s1 = [ '42', '01001', 'abc', 'ABC', '4aBc', ' 12ef ', '+42', 'foo', '42foo', '42.1', '']
        def fn(i, base):
            s = s1[i]
            res = int(s, base)
            return res
        for j in (10, 16, 2, 1, 36, 42, -3):
            for i in range(len(s1)):
                try:
                    expected = fn(i, j)
                except ValueError:
                    self.interpret_raises(ValueError, fn, [i, j])
                else:
                    res = self.interpret(fn, [i, j])
                    assert res == expected

    def test_int_valueerror(self):
        s1 = ['42g', '?']
        def fn(i):
            try:
                return int(s1[i])
            except ValueError:
                return -654
        res = self.interpret(fn, [0])
        assert res == -654
        res = self.interpret(fn, [1])
        assert res == -654

    def test_char_mul_n(self):
        def f(c, n):
            return c*n
        res = self.interpret(f, ['a', 4])
        assert self.ll_to_string(res) == 'a'*4
        res = self.interpret(f, ['a', 0])
        assert self.ll_to_string(res) == ""

    def test_n_mul_char(self):
        def f(c, n):
            return n*c
        res = self.interpret(f, ['a', 4])
        assert self.ll_to_string(res) == 'a'*4
        res = self.interpret(f, ['a', 0])
        assert self.ll_to_string(res) == ""

def FIXME_test_str_to_pystringobj():
    def f(n):
        if n >= 0:
            return "hello"[n:]
        else:
            return None
    def g(n):
        if n == -2:
            return 42
        return f(n)
    res = interpret(g, [-1])
    assert res._obj.value == None
    res = interpret(g, [1])
    assert res._obj.value == "ello"
    res = interpret(g, [-2])
    assert res._obj.value == 42

class TestLltype(AbstractTestRstr):
    ts = "lltype"

    def ll_to_string(self, s):
        return ''.join(s.chars)

    def test_hash(self):
        def fn(i):
            if i == 0:
                s = ''
            else:
                s = "xxx"
            return hash(s)
        res = self.interpret(fn, [0])
        assert res == -1
        res = self.interpret(fn, [1])
        assert typeOf(res) == Signed


class TestOotype(AbstractTestRstr):
    ts = "ootype"

    def ll_to_string(self, s):
        return s._str
