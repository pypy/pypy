from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.rstr import parse_fmt_string
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.test.test_llinterp import interpret, make_interpreter


def test_simple():
    def fn(i):
        s = 'hello'
        return s[i]
    ev_fn = make_interpreter(fn, [0])
    for i in range(5):
        res = ev_fn(i)
        assert res == 'hello'[i]


def test_nonzero():
    def fn(i, j):
        s = ['', 'xx'][j]
        if i < 0:
            s = None
        if i > -2:
            return bool(s)
        else:
            return False
    ev_fn = make_interpreter(fn, [0, 0])
    for i in [-2, -1, 0]:
        for j in range(2):
            res = ev_fn(i, j)
            assert res is fn(i, j)

def test_hash():
    def fn(i):
        if i == 0:
            s = ''
        else:
            s = "xxx"
        return hash(s)
    ev_fn = make_interpreter(fn, [0])
    res = ev_fn(0)
    assert res == -1
    res = ev_fn(1)
    assert typeOf(res) == Signed

def test_concat():
    def fn(i, j):
        s1 = ['', 'a', 'ab']
        s2 = ['', 'x', 'xy']
        return s1[i] + s2[j]
    ev_fn = make_interpreter(fn, [0,0])    
    for i in range(3):
        for j in range(3):
            res = ev_fn(i, j)
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

    ev_fn = make_interpreter(fn, [0])    
    for i in range(3):
        res = ev_fn(i)
        assert res is True
        
def test_char_constant():
    def fn(s):
        return s + '.'
    res = interpret(fn, ['x'])
    assert len(res.chars) == 2
    assert res.chars[0] == 'x'
    assert res.chars[1] == '.'

def test_char_compare():
    res = interpret(lambda c1, c2: c1 == c2,  ['a', 'b'])
    assert res is False
    res = interpret(lambda c1, c2: c1 == c2,  ['a', 'a'])
    assert res is True
    res = interpret(lambda c1, c2: c1 <= c2,  ['z', 'a'])
    assert res is False

def test_str_compare():
    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] == s2[j]
    ev_fn = make_interpreter(fn, [0,0])    
    for i in range(2):
        for j in range(6):
            res = ev_fn(i, j)            
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] != s2[j]
    ev_fn = make_interpreter(fn, [0,0])    
    for i in range(2):
        for j in range(6):
            res = ev_fn(i, j)
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] < s2[j]
    ev_fn = make_interpreter(fn, [0,0])    
    for i in range(2):
        for j in range(6):
            res = ev_fn(i, j)
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] <= s2[j]
    ev_fn = make_interpreter(fn, [0,0])    
    for i in range(2):
        for j in range(6):
            res = ev_fn(i, j)
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] >= s2[j]
    ev_fn = make_interpreter(fn, [0,0])    
    for i in range(2):
        for j in range(6):
            res = ev_fn(i, j)
            assert res is fn(i, j)

    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'twos', 'foobar']
        return s1[i] > s2[j]
    ev_fn = make_interpreter(fn, [0,0])    
    for i in range(2):
        for j in range(6):
            res = ev_fn(i, j)
            assert res is fn(i, j)


def test_startswith():
    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
        return s1[i].startswith(s2[j])
    ev_fn = make_interpreter(fn, [0,0])    
    for i in range(2):
        for j in range(9):
            res = ev_fn(i, j)
            assert res is fn(i, j)

def test_endswith():
    def fn(i, j):
        s1 = ['one', 'two']
        s2 = ['one', 'two', 'o', 'on', 'ne', 'e', 'twos', 'foobar', 'fortytwo']
        return s1[i].endswith(s2[j])
    ev_fn = make_interpreter(fn, [0,0])
    for i in range(2):
        for j in range(9):
            res = ev_fn(i, j)
            assert res is fn(i, j)

def test_join():
    res = interpret(lambda: ''.join([]), [])
    assert ''.join(res.chars) == ""
    
    def fn(i, j):
        s1 = [ '', ',', ' and ']
        s2 = [ [], ['foo'], ['bar', 'baz', 'bazz']]
        return s1[i].join(s2[j])
    ev_fn = make_interpreter(fn, [0,0])
    for i in range(3):
        for j in range(3):
            res = ev_fn(i, j)
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
