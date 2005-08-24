import random
from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rstr import parse_fmt_string, ll_find, ll_rfind, STR
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
        res = ll_find(llstr(s1), llstr(s2), 0, n1)
        assert res == s1.find(s2)
        res = ll_rfind(llstr(s1), llstr(s2), 0, n1)
        assert res == s1.rfind(s2)

def test_simple():
    def fn(i):
        s = 'hello'
        return s[i]
    for i in range(5):
        res = interpret(fn, [i])
        assert res == 'hello'[i]

def test_implicit_index_error():
    def fn(i):
        s = 'hello'
        try:
            return s[i]
        except IndexError:
            return '*'
    for i in range(-5, 5):
        res = interpret(fn, [i])
        assert res == 'hello'[i]
    res = interpret(fn, [5])
    assert res == '*'
    res = interpret(fn, [6])
    assert res == '*'
    res = interpret(fn, [-42])
    assert res == '*'
    

def test_nonzero():
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
            res = interpret(fn, [i, j])
            assert res is fn(i, j)

def test_hash():
    def fn(i):
        if i == 0:
            s = ''
        else:
            s = "xxx"
        return hash(s)
    res = interpret(fn, [0])
    assert res == -1
    res = interpret(fn, [1])
    assert typeOf(res) == Signed

def test_concat():
    def fn(i, j):
        s1 = ['', 'a', 'ab']
        s2 = ['', 'x', 'xy']
        return s1[i] + s2[j]
    for i in range(3):
        for j in range(3):
            res = interpret(fn, [i,j])
            assert ''.join(res.chars) == fn(i, j)

def test_iter():
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
        res = interpret(fn, [i])
        assert res is True
        
def test_char_constant():
    def fn(s):
        return s + '.'
    res = interpret(fn, ['x'])
    assert len(res.chars) == 2
    assert res.chars[0] == 'x'
    assert res.chars[1] == '.'

def test_char_isspace():
    def fn(s):
        return s.isspace() 
    res = interpret(fn, ['x']) 
    assert res == False 
    res = interpret(fn, [' '])
    assert res == True 

def test_char_compare():
    res = interpret(lambda c1, c2: c1 == c2,  ['a', 'b'])
    assert res is False
    res = interpret(lambda c1, c2: c1 == c2,  ['a', 'a'])
    assert res is True
    res = interpret(lambda c1, c2: c1 <= c2,  ['z', 'a'])
    assert res is False

def test_char_mul():
    def fn(c, mul):
        s = c * mul
        res = 0
        for i in range(len(s)):
            res = res*10 + ord(s[i]) - ord('0')
        c2 = c
        c2 *= mul
        res = 10 * res + (c2 == s)
        return res
    res = interpret(fn, ['3', 5])
    assert res == 333331
    res = interpret(fn, ['5', 3])
    assert res == 5551

def test_str_compare():
    def fn(i, j):
        s1 = ['one', 'two', None]
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar', None]
        return s1[i] == s2[j]
    for i in range(3):
        for j in range(7):
            res = interpret(fn, [i,j])
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] != s2[j]
    for i in range(2):
        for j in range(6):
            res = interpret(fn, [i, j])
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] < s2[j]
    for i in range(2):
        for j in range(6):
            res = interpret(fn, [i,j])
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] <= s2[j]
    for i in range(2):
        for j in range(6):
            res = interpret(fn, [i,j])
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] >= s2[j]
    for i in range(2):
        for j in range(6):
            res = interpret(fn, [i,j])
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] > s2[j]
    for i in range(2):
        for j in range(6):
            res = interpret(fn, [i,j])
            assert res is fn(i, j)

def test_startswith():
    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
        return s1[i].startswith(s2[j])
    for i in range(2):
        for j in range(9):
            res = interpret(fn, [i,j])
            assert res is fn(i, j)

def test_endswith():
    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
        return s1[i].endswith(s2[j])
    for i in range(2):
        for j in range(9):
            res = interpret(fn, [i,j])
            assert res is fn(i, j)

def test_find():
    def fn(i, j):
        s1 = ['one two three', 'abc abcdab abcdabcdabde']
        s2 = ['one', 'two', 'abcdab', 'one tou', 'abcdefgh', 'fortytwo', '']
        return s1[i].find(s2[j])
    for i in range(2):
        for j in range(7):
            res = interpret(fn, [i,j])
            assert res == fn(i, j)

def test_find_with_start():
    def fn(i):
        assert i >= 0
        return 'ababcabc'.find('abc', i)
    for i in range(9):
        res = interpret(fn, [i])
        assert res == fn(i)

def test_find_with_start_end():
    def fn(i, j):
        assert i >= 0
        assert j >= 0
        return 'ababcabc'.find('abc', i, j)
    for (i, j) in [(1,7), (2,6), (3,7), (3,8)]:
        res = interpret(fn, [i, j])
        assert res == fn(i, j)

def test_rfind():
    def fn():
        return 'aaa'.rfind('a') + 'aaa'.rfind('a', 1) + 'aaa'.rfind('a', 1, 2)
    res = interpret(fn, [])
    assert res == 2 + 2 + 1

def test_upper():
    def fn(i):
        strings = ['', ' ', 'upper', 'UpPeR', ',uppEr,']
        return strings[i].upper()
    for i in range(5):
        res = interpret(fn, [i])
        assert ''.join(res.chars) == fn(i)

def test_lower():
    def fn(i):
        strings = ['', ' ', 'lower', 'LoWeR', ',lowEr,']
        return strings[i].lower()
    for i in range(5):
        res = interpret(fn, [i])
        assert ''.join(res.chars) == fn(i)

def test_join():
    res = interpret(lambda: ''.join([]), [])
    assert ''.join(res.chars) == ""

    res = interpret(lambda: ''.join(['a', 'b', 'c']), [])
    assert ''.join(res.chars) == "abc"

    res = interpret(lambda: ''.join(['abc', 'de', 'fghi']), [])
    assert ''.join(res.chars) == "abcdefghi"
    
    def fn(i, j):
        s1 = [ '', ',', ' and ']
        s2 = [ [], ['foo'], ['bar', 'baz', 'bazz']]
        return s1[i].join(s2[j])
    for i in range(3):
        for j in range(3):
            res = interpret(fn, [i,j])
            assert ''.join(res.chars) == fn(i, j)

def test_parse_fmt():
    assert parse_fmt_string('a') == ['a']
    assert parse_fmt_string('%s') == [('s',)]
    assert parse_fmt_string("name '%s' is not defined") == ["name '", ("s",), "' is not defined"]

def test_strformat():
    def percentS(s):
        return "before %s after" % (s,)

    res = interpret(percentS, ['1'])
    assert ''.join(res.chars) == 'before 1 after'

    def percentD(i):
        return "bing %d bang" % (i,)
    
    res = interpret(percentD, [23])
    assert ''.join(res.chars) == 'bing 23 bang'

    def percentX(i):
        return "bing %x bang" % (i,)

    res = interpret(percentX, [23])
    assert ''.join(res.chars) == 'bing 17 bang'

    res = interpret(percentX, [-123])
    assert ''.join(res.chars) == 'bing -7b bang'

    def percentO(i):
        return "bing %o bang" % (i,)
    
    res = interpret(percentO, [23])
    assert ''.join(res.chars) == 'bing 27 bang'

    res = interpret(percentO, [-123])
    assert ''.join(res.chars) == 'bing -173 bang'

    def moreThanOne(s, d, x, o):
        return "string: %s decimal: %d hex: %x oct: %o" % (s, d, x, o)

    args = 'a', 2, 3, 4
    res = interpret(moreThanOne, list(args))
    assert ''.join(res.chars) == moreThanOne(*args)

def test_strformat_nontuple():
    def percentD(i):
        return "before %d after" % i

    res = interpret(percentD, [1])
    assert ''.join(res.chars) == 'before 1 after'

    def percentS(i):
        return "before %s after" % i

    res = interpret(percentS, ['D'])
    assert ''.join(res.chars) == 'before D after'

def test_str_slice():
    def fn():
        s = 'hello'
        s1 = s[:3]
        s2 = s[3:]
        s3 = s[3:10]
        return s1+s2 == s and s2+s1 == 'lohel' and s1+s3 == s
    res = interpret(fn, ())
    assert res

def test_str_slice_minusone():
    def fn():
        s = 'hello'
        z = 'h'
        return s[:-1]+z[:-1]
    res = interpret(fn, ())
    assert ''.join(res.chars) == 'hell'


def test_strformat_instance():
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
        
    res = interpret(dummy, [1])
    assert ''.join(res.chars) == '<C object>'

    res = interpret(dummy, [0])
    assert ''.join(res.chars) == '<D object>'

def test_percentformat_instance():
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
        
    res = interpret(dummy, [1])
    assert ''.join(res.chars) == 'what a nice <C object>, much nicer than <D object>'

    res = interpret(dummy, [0])
    assert ''.join(res.chars) == 'what a nice <D object>, much nicer than <C object>'

def test_split():
    def fn(i):
        s = ['', '0.1.2.4.8', '.1.2', '1.2.', '.1.2.4.'][i]
        l = s.split('.')
        sum = 0
        for num in l:
             if len(num):
                 sum += ord(num) - ord('0')
        return sum + len(l) * 100
    for i in range(5):
        res = interpret(fn, [i])
        assert res == fn(i)

def test_contains():
    def fn(i):
        s = 'Hello world'
        return chr(i) in s
    for i in range(256):
        res = interpret(fn, [i])#, view=i==42)
        assert res == fn(i)

def test_replace():
    def fn(c1, c2):
        s = 'abbccc'
        s = s.replace(c1, c2)
        res = 0
        for c in s:
            if c == c2:
                res += 1
        return res
    res = interpret(fn, ['a', 'c'])
    assert res == 4
    res = interpret(fn, ['c', 'b'])
    assert res == 5
    def fn():
        s = 'abbccc'
        s = s.replace('a', 'baz')
    raises (TyperError, interpret, fn, ())
    def fn():
        s = 'abbccc'
        s = s.replace('abb', 'c')
    raises (TyperError, interpret, fn, ())

def test_int():
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
                interpret_raises(ValueError, fn, [i, j])
            else:
                res = interpret(fn, [i, j])
                assert res == expected


def test_char_mul_n():
    def f(c, n):
        return c*n
    res = interpret(f, ['a', 4])
    assert ''.join(res.chars) == 'a'*4
    res = interpret(f, ['a', 0])
    assert ''.join(res.chars) == ""
    
def test_n_mul_char():
    def f(c, n):
        return n*c
    res = interpret(f, ['a', 4])
    assert ''.join(res.chars) == 'a'*4
    res = interpret(f, ['a', 0])
    assert ''.join(res.chars) == ""

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
