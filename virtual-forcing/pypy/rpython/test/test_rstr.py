import random
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.rstr import AbstractLLHelpers
from pypy.rpython.lltypesystem.rstr import LLHelpers, STR
from pypy.rpython.ootypesystem.ootype import make_string
from pypy.rpython.rtyper import RPythonTyper, TyperError
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rpython.llinterp import LLException
from pypy.objspace.flow.model import summary

def test_parse_fmt():
    parse = AbstractLLHelpers.parse_fmt_string
    assert parse('a') == ['a']
    assert parse('%s') == [('s',)]
    assert parse("name '%s' is not defined") == ["name '", ("s",), "' is not defined"]

class AbstractTestRstr(BaseRtypingTest):
    def test_simple(self):
        const = self.const
        def fn(i):
            s = const('hello')
            return s[i]
        for i in range(5):
            res = self.interpret(fn, [i])
            expected = fn(i)
            assert res == expected
            assert res.__class__ is expected.__class__

    def test_implicit_index_error(self):
        const = self.const
        def fn(i):
            s = const('hello')
            try:
                return s[i]
            except IndexError:
                return const('*')
        for i in range(-5, 5):
            res = self.interpret(fn, [i])
            expected = fn(i)
            assert res == expected
            assert res.__class__ is expected.__class__
        res = self.interpret(fn, [5])
        assert res == '*'
        res = self.interpret(fn, [6])
        assert res == '*'
        res = self.interpret(fn, [-42])
        assert res == '*'

    def test_nonzero(self):
        const = self.const
        def fn(i, j):
            s = [const(''), const('xx')][j]
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
        const = self.const
        def fn(i, j):
            s1 = [const(''), const('a'), const('ab')]
            s2 = [const(''), const('x'), const('xy')]
            return s1[i] + s2[j]
        for i in range(3):
            for j in range(3):
                res = self.interpret(fn, [i,j])
                assert self.ll_to_string(res) == fn(i, j)

    def test_iter(self):
        const = self.const
        def fn(i):
            s = [const(''), const('a'), const('hello')][i]
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
        const = self.const
        def fn(s):
            return s + const('.')
        res = self.interpret(fn, [const('x')])
        res = self.ll_to_string(res)
        assert len(res) == 2
        assert res[0] == const('x')
        assert res[1] == const('.')

    def test_char_isxxx(self):
        constchar = self.constchar
        def fn(s):
            return (s.isspace()      |
                    s.isdigit() << 1 |
                    s.isalpha() << 2 |
                    s.isalnum() << 3 |
                    s.isupper() << 4 |
                    s.islower() << 5)
        for i in range(128):
            ch = constchar(i)
            res = self.interpret(fn, [ch])
            assert res == fn(ch)

    def test_char_compare(self):
        const = self.const
        res = self.interpret(lambda c1, c2: c1 == c2,  [const('a'),
                                                        const('b')])
        assert res is False
        res = self.interpret(lambda c1, c2: c1 == c2,  [const('a'),
                                                        const('a')])
        assert res is True
        res = self.interpret(lambda c1, c2: c1 <= c2,  [const('z'),
                                                        const('a')])
        assert res is False

    def test_char_mul(self):
        const = self.const
        def fn(c, mul):
            s = c * mul
            res = 0
            for i in range(len(s)):
                res = res*10 + ord(const(s[i])) - ord(const('0'))
            c2 = c
            c2 *= mul
            res = 10 * res + (c2 == s)
            return res
        res = self.interpret(fn, [const('3'), 5])
        assert res == 333331
        res = self.interpret(fn, [const('5'), 3])
        assert res == 5551

    def test_is_none(self):
        const = self.const
        def fn(i):
            s1 = [const('foo'), None][i]
            return s1 is None
        assert self.interpret(fn, [0]) == False
        assert self.interpret(fn, [1]) == True

    def test_str_compare(self):
        const = self.const
        def fn(i, j):
            s1 = [const('one'), const('two'), None]
            s2 = [const('one'), const('two'), const('o'),
                  const('on'), const('twos'), const('foobar'), None]
            return s1[i] == s2[j]
        for i in range(3):
            for j in range(7):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = [const('one'), const('two')]
            s2 = [const('one'), const('two'), const('o'), const('on'), const('twos'), const('foobar')]
            return s1[i] != s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i, j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = [const('one'), const('two')]
            s2 = [const('one'), const('two'), const('o'), const('on'), const('twos'), const('foobar')]
            return s1[i] < s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = [const('one'), const('two')]
            s2 = [const('one'), const('two'), const('o'), const('on'), const('twos'), const('foobar')]
            return s1[i] <= s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = [const('one'), const('two')]
            s2 = [const('one'), const('two'), const('o'), const('on'), const('twos'), const('foobar')]
            return s1[i] >= s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

        def fn(i, j):
            s1 = [const('one'), const('two')]
            s2 = [const('one'), const('two'), const('o'), const('on'), const('twos'), const('foobar')]
            return s1[i] > s2[j]
        for i in range(2):
            for j in range(6):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

    def test_startswith(self):
        const = self.const
        def fn(i, j):
            s1 = [const(''), const('one'), const('two')]
            s2 = [const(''), const('one'), const('two'), const('o'), const('on'), const('ne'), const('e'), const('twos'), const('foobar'), const('fortytwo')]
            return s1[i].startswith(s2[j])
        for i in range(3):
            for j in range(10):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

    def test_endswith(self):
        const = self.const
        def fn(i, j):
            s1 = [const(''), const('one'), const('two')]
            s2 = [const(''), const('one'), const('two'), const('o'), const('on'), const('ne'), const('e'), const('twos'), const('foobar'), const('fortytwo')]
            return s1[i].endswith(s2[j])
        for i in range(3):
            for j in range(10):
                res = self.interpret(fn, [i,j])
                assert res is fn(i, j)

    def test_find(self):
        const = self.const
        def fn(i, j):
            s1 = [const('one two three'), const('abc abcdab abcdabcdabde')]
            s2 = [const('one'), const('two'), const('abcdab'), const('one tou'), const('abcdefgh'), const('fortytwo'), const('')]
            return s1[i].find(s2[j])
        for i in range(2):
            for j in range(7):
                res = self.interpret(fn, [i,j])
                assert res == fn(i, j)


    def test_contains_str(self):
        const = self.const
        def fn(i, j):
            s1 = [const('one two three'), const('abc abcdab abcdabcdabde')]
            s2 = [const('one'), const('two'), const('abcdab'), const('one tou'), const('abcdefgh'), const('fortytwo'), const('')]
            return s2[j] in s1[i]
        for i in range(2):
            for j in range(7):
                res = self.interpret(fn, [i,j])
                assert res == fn(i, j)

    def test_find_with_start(self):
        const = self.const
        def fn(i):
            assert i >= 0
            return const('ababcabc').find(const('abc'), i)
        for i in range(9):
            res = self.interpret(fn, [i])
            assert res == fn(i)

    def test_find_with_start_end(self):
        const = self.const
        def fn(i, j):
            assert i >= 0
            assert j >= 0
            return (const('ababcabc').find(const('abc'), i, j) +
                    const('ababcabc').find(const('b'), i, j) * 100)
        for (i, j) in [(1,7), (2,6), (3,7), (3,8), (4,99), (7, 99)]:
            res = self.interpret(fn, [i, j])
            assert res == fn(i, j)

    def test_find_TyperError(self):
        const = self.const
        def f():
            s = const('abc')
            s.find(s, 0, -10)
        raises(TyperError, self.interpret, f, ())
        def f():
            s = const('abc')
            s.find(s, -10)
        raises(TyperError, self.interpret, f, ())

    def test_find_empty_string(self):
        const = self.const
        def f(i):
            assert i >= 0
            s = const("abc")
            x = s.find(const(''))
            x+= s.find(const(''), i)*10
            x+= s.find(const(''), i, i)*100
            x+= s.find(const(''), i, i+1)*1000
            return x
        for i, expected in enumerate([0, 1110, 2220, 3330, -1110, -1110]):
            res = self.interpret(f, [i])
            assert res == expected
            
    def test_rfind(self):
        const = self.const
        def fn():
            # string-searching versions
            return (const('aaa').rfind(const('aa')) +
                    const('aaa').rfind(const('aa'), 1) * 10 +
                    const('aaa').rfind(const('aa'), 1, 2) * 100 +
                    const('aaa').rfind(const('aa'), 3, 42) * 1000 +
            # char-searching versions
                    const('aaa').rfind(const('a')) * 10000 +
                    const('aaa').rfind(const('a'), 1) * 100000 +
                    const('aaa').rfind(const('a'), 1, 2) * 1000000 +
                    const('aaa').rfind(const('a'), 3, 42) * 10000000)
        res = self.interpret(fn, [])
        assert res == fn()

    def test_rfind_empty_string(self):
        const = self.const
        def f(i):
            assert i >= 0
            s = const("abc")
            x = s.rfind(const(''))
            x+= s.rfind(const(''), i)*10
            x+= s.rfind(const(''), i, i)*100
            x+= s.rfind(const(''), i, i+1)*1000
            return x
        for i, expected in enumerate([1033, 2133, 3233, 3333, 3-1110, 3-1110]):
            res = self.interpret(f, [i])
            assert res == expected

    def test_find_char(self):
        const = self.const
        def fn(ch):
            pos1 = const('aiuwraz 483').find(ch)
            pos2 = const('aiuwraz 483').rfind(ch)
            return pos1 + (pos2*100)
        for ch in const('a ?3'):
            res = self.interpret(fn, [ch])
            assert res == fn(ch)

    def test_strip(self):
        const = self.const
        def both():
            return const('!ab!').strip(const('!'))
        def left():
            return const('!ab!').lstrip(const('!'))
        def right():
            return const('!ab!').rstrip(const('!'))
        res = self.interpret(both, [])
        assert self.ll_to_string(res) == const('ab')
        res = self.interpret(left, [])
        assert self.ll_to_string(res) == const('ab!')
        res = self.interpret(right, [])
        assert self.ll_to_string(res) == const('!ab')

    def test_upper(self):
        const = self.const
        constchar = self.constchar
        strings = [const(''), const(' '), const('upper'), const('UpPeR'), const(',uppEr,')]
        for i in range(256): strings.append(constchar(i))
        def fn(i):
            return strings[i].upper()
        for i in range(len(strings)):
            res = self.interpret(fn, [i])
            assert self.ll_to_string(res) == fn(i)

    def test_lower(self):
        const = self.const
        strings = [const(''), const(' '), const('lower'), const('LoWeR'), const(',lowEr,')]
        for i in range(256): strings.append(chr(i))
        def fn(i):
            return strings[i].lower()
        for i in range(len(strings)):
            res = self.interpret(fn, [i])
            assert self.ll_to_string(res) == fn(i)

    def test_join(self):
        const = self.const
        res = self.interpret(lambda: const('').join([]), [])
        assert self.ll_to_string(res) == ""

        res = self.interpret(lambda: const('').join([const('a'), const('b'), const('c')]), [])
        assert self.ll_to_string(res) == "abc"

        res = self.interpret(lambda: const('').join([const('abc'), const('de'), const('fghi')]), [])
        assert self.ll_to_string(res) == "abcdefghi"

        res = self.interpret(lambda: const('.').join([const('abc'), const('def')]), [])
        assert self.ll_to_string(res) == const('abc.def')

        def fn(i, j):
            s1 = [ const(''), const(','), const(' and ')]
            s2 = [ [], [const('foo')], [const('bar'), const('baz'), const('bazz')]]
            return s1[i].join(s2[j])
        for i in range(3):
            for j in range(3):
                res = self.interpret(fn, [i,j])
                assert self.ll_to_string(res) == fn(i, j)

        def fn(i, j):
            s1 = [ const(''), const(','), const(' and ')]
            s2 = [ [], [const('foo')], [const('bar'), const('baz'), const('bazz')]]
            s2[1].extend([const('x')])
            return s1[i].join(s2[j])
        for i in range(3):
            for j in range(3):
                res = self.interpret(fn, [i,j])
                assert self.ll_to_string(res) == fn(i, j)

    def test_str_slice(self):
        const = self.const
        def fn(n):
            s = [const('hello'), const('world')][n]   # non-constant
            s1 = s[:3]
            s2 = s[3:]
            s3 = s[3:10]
            return s1+s2 == s and s2+s1 == const('lohel') and s1+s3 == s
        res = self.interpret(fn, [0])
        assert res

    def test_str_slice_minusone(self):
        const = self.const
        def fn(n):
            s = const('hello')
            z = const('h')
            lst = [s, z]     # uncontantify s and z
            s = lst[n]
            z = lst[n+1]
            return s[:-1]+z[:-1]
        res = self.interpret(fn, [0])
        assert self.ll_to_string(res) == const('hell')

    def test_strformat(self):
        const = self.const
        def percentS(s):
            return const("before %s after") % (s,)

        res = self.interpret(percentS, [const('1')])
        assert self.ll_to_string(res) == const('before 1 after')

        def percentD(i):
            return "bing %d bang" % (i,)

        res = self.interpret(percentD, [23])
        assert self.ll_to_string(res) == const('bing 23 bang')

        def percentX(i):
            return const("bing %x bang") % (i,)

        res = self.interpret(percentX, [23])
        assert self.ll_to_string(res) == const('bing 17 bang')

        res = self.interpret(percentX, [-123])
        assert self.ll_to_string(res) == const('bing -7b bang')

        def percentO(i):
            return const("bing %o bang") % (i,)

        res = self.interpret(percentO, [23])
        assert self.ll_to_string(res) == const('bing 27 bang')

        res = self.interpret(percentO, [-123])
        assert self.ll_to_string(res) == const('bing -173 bang')

        def moreThanOne(s, d, x, o):
            return const("string: %s decimal: %d hex: %x oct: %o") % (s, d, x, o)

        args = const('a'), 2, 3, 4
        res = self.interpret(moreThanOne, list(args))
        assert self.ll_to_string(res) == moreThanOne(*args)

    def test_strformat_nontuple(self):
        const = self.const
        def percentD(i):
            return const("before %d after") % i

        res = self.interpret(percentD, [1])
        assert self.ll_to_string(res) == const('before 1 after')

        def percentS(i):
            return const("before %s after") % i

        res = self.interpret(percentS, [const('D')])
        assert self.ll_to_string(res) == const('before D after')

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
        assert res.find('C object') != -1
        assert res.endswith('>')

        res = self.ll_to_string(self.interpret(dummy, [0]))
        assert res.startswith('<')
        assert res.find('D object') != -1
        assert res.endswith('>')

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
        assert res.find('what a nice <C object') != -1
        assert res.find('>, much nicer than <D object') != -1

        res = self.ll_to_string(self.interpret(dummy, [0]))
        res = res.replace('pypy.rpython.test.test_rstr.', '')        
        assert res.find('what a nice <D object') != -1
        assert res.find('>, much nicer than <C object') != -1

    def test_percentformat_tuple(self):
        for t, expected in [((),        "<<<()>>>"),
                            ((5,),      "<<<(5,)>>>"),
                            ((5, 6),    "<<<(5, 6)>>>"),
                            ((5, 6, 7), "<<<(5, 6, 7)>>>")]:
            def getter():
                return t
            def dummy():
                return "<<<%s>>>" % (getter(),)

            res = self.ll_to_string(self.interpret(dummy, []))
            assert res == expected

    def test_percentformat_list(self):
        for t, expected in [([],        "<<<[]>>>"),
                            ([5],       "<<<[5]>>>"),
                            ([5, 6],    "<<<[5, 6]>>>"),
                            ([5, 6, 7], "<<<[5, 6, 7]>>>")]:
            def getter():
                return t
            def dummy():
                return "<<<%s>>>" % (getter(),)

            res = self.ll_to_string(self.interpret(dummy, []))
            assert res == expected

    def test_splitlines(self):
        const = self.const
        def f(i, newlines):
            s = [const(''), const("\n"), const("\n\n"), const("hi\n"),
                 const("random data\r\n"), const("\r\n"), const("\rdata")]
            test_string = s[i]
            if newlines:
                return len(test_string.splitlines(True))
            else:
                return len(test_string.splitlines())
        for newlines in (True, False):
            for i in xrange(5):
                res = self.interpret(f, [i, newlines])
                assert res == f(i, newlines)

    def test_split(self):
        const = self.const
        def fn(i):
            s = [const(''), const('0.1.2.4.8'), const('.1.2'), const('1.2.'), const('.1.2.4.')][i]
            l = s.split(const('.'))
            sum = 0
            for num in l:
                 if len(num):
                     sum += ord(num) - ord(const('0'))
            return sum + len(l) * 100
        for i in range(5):
            res = self.interpret(fn, [i])
            assert res == fn(i)

    def test_contains(self):
        const = self.const
        constchar = self.constchar
        def fn(i):
            s = const('Hello world')
            return constchar(i) in s
        for i in range(256):
            res = self.interpret(fn, [i])#, view=i==42)
            assert res == fn(i)

    def test_replace(self):
        const = self.const
        def fn(c1, c2):
            s = const('abbccc')
            s = s.replace(c1, c2)
            res = 0
            for c in s:
                if c == c2:
                    res += 1
            return res
        res = self.interpret(fn, [const('a'), const('c')])
        assert res == 4
        res = self.interpret(fn, [const('c'), const('b')])
        assert res == 5

    def test_replace_TyperError(self):
        const = self.const
        def fn():
            s = const('abbccc')
            s = s.replace(const('a'), const('baz'))
        raises(TyperError, self.interpret, fn, ())
        def fn():
            s = const('abbccc')
            s = s.replace(const('abb'), const('c'))
        raises(TyperError, self.interpret, fn, ())

    def test_int(self):
        const = self.const
        s1 = [ const('42'), const('01001'), const('abc'), const('ABC'), const('4aBc'), const(' 12ef '), const('+42'), const('foo'), const('42foo'), const('42.1'), const(''), const('+ 42')]
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
        const = self.const
        s1 = [const('42g'), const('?'), const('+'), const('+ ')]
        def fn(i):
            try:
                return int(s1[i])
            except ValueError:
                return -654
        res = self.interpret(fn, [0])
        assert res == -654
        res = self.interpret(fn, [1])
        assert res == -654
        res = self.interpret(fn, [2])
        assert res == -654

    def test_float(self):
        const = self.const
        f = [const(''), const('    '), const('0'), const('1'), const('-1.5'), const('1.5E2'), const('2.5e-1'), const(' 0 '), const('?')]
        def fn(i):
            s = f[i]
            return float(s)

        for i in range(len(f)):
            try:
                expected = fn(i)
            except ValueError:
                self.interpret_raises(ValueError, fn, [i])
            else:
                res = self.interpret(fn, [i])
                assert res == expected

    def test_char_mul_n(self):
        const = self.const
        def f(c, n):
            return c*n
        res = self.interpret(f, [const('a'), 4])
        assert self.ll_to_string(res) == 'a'*4
        res = self.interpret(f, [const('a'), 0])
        assert self.ll_to_string(res) == ""

    def test_char_mul_negative(self):
        const = self.const
        def f(c):
            return c * -3

        res = self.interpret(f, [const('a')])
        assert self.ll_to_string(res) == ''

    def test_n_mul_char(self):
        const = self.const
        def f(c, n):
            return n*c
        res = self.interpret(f, [const('a'), 4])
        assert self.ll_to_string(res) == 'a'*4
        res = self.interpret(f, [const('a'), 0])
        assert self.ll_to_string(res) == ""

    EMPTY_STRING_HASH = -1     # unless overridden

    def test_hash(self):
        from pypy.rlib.objectmodel import compute_hash
        const = self.const
        def fn(i):
            if i == 0:
                s = const('')
            else:
                s = const("xxx")
            return compute_hash(s)
        res = self.interpret(fn, [0])
        assert res == self.EMPTY_STRING_HASH
        res = self.interpret(fn, [1])
        assert typeOf(res) == Signed

    def test_call_str_on_string(self):
        const = self.const
        def fn(i):
            s = const("x") * i
            return const(s)
        res = self.interpret(fn, [3])
        assert self.ll_to_string(res) == 'xxx'

    def test_count_char(self):
        const = self.const
        def fn(i):
            s = const("").join([const("abcasd")] * i)
            return s.count(const("a")) + s.count(const("a"), 2) + \
                   s.count(const("b"), 1, 6) + s.count(const("a"), 5, 99)
        res = self.interpret(fn, [4])
        assert res == 8 + 7 + 1 + 6

    def test_count(self):
        const = self.const
        def fn(i):
            s = const("").join([const("abcabsd")] * i)
            one = i / i # confuse the annotator
            return (s.count(const("abc")) + const("abcde").count(const("")) +
                    const("abcda").count(const("a") * one) +
                    s.count(const("ab"), 0, 999))
        res = self.interpret(fn, [4])
        assert res == 4 + 6 + 2 + 8

    def test_count_overlapping_occurences(self):
        const = self.const
        def fn():
            return const('ababa').count(const('aba'))
        res = self.interpret(fn, [])
        assert res == 1
       
    def test_count_TyperError(self):
        const = self.const
        def f():
            s = const('abc')
            s.count(s, 0, -10)
        raises(TyperError, self.interpret, f, ())
        def f():
            s = const('abc')
            s.count(s, -10)
        raises(TyperError, self.interpret, f, ())
    
    def test_getitem_exc(self):
        const = self.const
        def f(x):
            s = const("z")
            return s[x]

        res = self.interpret(f, [0])
        assert res == 'z'
        try:
            self.interpret_raises(IndexError, f, [1])
        except (AssertionError,), e:
            pass
        else:
            assert False
    
        def f(x):
            s = const("z")
            try:
                return s[x]
            except IndexError:
                return const('X')
            except Exception:
                return const(' ')

        res = self.interpret(f, [0])
        assert res == 'z'
        res = self.interpret(f, [1])
        assert res == 'X'        

        def f(x):
            s = const("z")
            try:
                return s[x]
            except Exception:
                return const(' ')

        res = self.interpret(f, [0])
        assert res == 'z'
        res = self.interpret(f, [1])
        assert res == ' '

        def f(x):
            s = const("z")
            try:
                return s[x]
            except ValueError:
                return const(' ')

        res = self.interpret(f, [0])
        assert res == 'z'
        try:
            self.interpret_raises(IndexError, f, [1])
        except (AssertionError,), e:
            pass
        else:
            assert False

    def test_fold_concat(self):
        const = self.const
        def g(tail):
            return const("head")+tail
        def f():
            return g(const("tail"))
        from pypy import conftest

        t, typer, fgraph = self.gengraph(f, [], backendopt=True)
        if conftest.option.view:
            t.view()
        assert summary(fgraph) == {}

    def test_inplace_add(self):
        from pypy.rpython.annlowlevel import hlstr
        const = self.const
        def f(x, y):
            y = const(hlstr(y))
            if x > 0:
                l = [const('a'), const('b')]
            else:
                l = [const('a')]
            l += y
            return const('').join(l)

        assert self.ll_to_string(self.interpret(f, [1,
                                       self.string_to_ll('abc')])) == 'ababc'
        
    def test_hlstr(self):
        const = self.const
        from pypy.rpython.annlowlevel import hlstr
        def f(s):
            return const("*")+const(hlstr(s))+const("*") == const("*abba*")

        res = self.interpret(f, [self.string_to_ll(const("abba"))])
        assert res

    def test_prebuilt_ll_strings(self):
        llstr0 = self.string_to_ll(None)
        assert not llstr0
        llstr1 = self.string_to_ll("hello")
        def f(i):
            if i == 0:
                return llstr0
            else:
                return llstr1
        res = self.interpret(f, [0])
        assert self.ll_to_string(res) is None
        res = self.interpret(f, [1])
        assert self.ll_to_string(res) == "hello"

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

class BaseTestRstr(AbstractTestRstr):
    const = str
    constchar = chr

class TestLLtype(BaseTestRstr, LLRtypeMixin):

    def test_ll_find_rfind(self):
        llstr = self.string_to_ll
        
        for i in range(50):
            n1 = random.randint(0, 10)
            s1 = ''.join([random.choice("ab") for i in range(n1)])
            n2 = random.randint(0, 5)
            s2 = ''.join([random.choice("ab") for i in range(n2)])
            res = LLHelpers.ll_find(llstr(s1), llstr(s2), 0, n1)
            assert res == s1.find(s2)
            res = LLHelpers.ll_rfind(llstr(s1), llstr(s2), 0, n1)
            assert res == s1.rfind(s2)

    def test_hash_via_type(self):
        from pypy.rlib.objectmodel import compute_hash

        def f(n):
            s = malloc(STR, n)
            s.hash = 0
            for i in range(n):
                s.chars[i] = chr(i)
            return s.gethash() - compute_hash('\x00\x01\x02\x03\x04')

        res = self.interpret(f, [5])
        assert res == 0


class TestOOtype(BaseTestRstr, OORtypeMixin):
    pass
