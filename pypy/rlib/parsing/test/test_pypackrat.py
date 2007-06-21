import py
from pypy.rlib.parsing import regex
from pypy.rlib.parsing.pypackrat import *
import operator

class TestPackrat(object):
    def test_simple(self):
        class parser(PackratParser):
            """
            a: 'a'*;
            b: 'a'+;
            c: ('a' | 'b')+;
            """
        print parser._code
        p = parser("ababababa")
        assert p.c() == list("ababababa")
        p = parser("aaaaaaaa")
        assert p.a() == list("aaaaaaaa")
        p = parser("")
        assert p.a() == []
        p = parser("")
        py.test.raises(BacktrackException, p.b)

    def test_questionmark(self):
        class parser(PackratParser):
            """
            a: 'a'? 'b';
            """
        print parser._code
        p = parser("ab")
        assert p.a() == 'b'
        p = parser("b")
        assert p.a() == 'b'

    def test_call(self):
        class parser(PackratParser):
            """
            a: 'a'? 'b';
            b: a 'c';
            """
        print parser._code
        p = parser("abc")
        res = p.b()
        assert res == 'c'
        p = parser("bc")
        res = p.b()
        assert res == 'c'

    def test_memoize(self):
        class parser(PackratParser):
            """
            x: a 'end';
            a: b c | b;
            b: 'b';
            c: 'c';
            """
        print parser._code
        p = parser("bend")
        res = p.x()
        assert res == 'end'

    def test_enclose(self):
        class parser(PackratParser):
            """
            a: 'a' <'b'> 'c'+;
            """
        print parser._code
        p = parser("abcccccc")
        p.a() == 'b'

    def test_not(self):
        class parser(PackratParser):
            """
            a: 'bh' !'a';
            """
        print parser._code
        p = parser('bhc')
        assert p.a() == 'bh'
        p.__chars__('c') == 'c'
        p = parser('bh')
        p.a() == 'bh'
        py.test.raises(BacktrackException, p.__any__)

    def test_lookahead(self):
        class parser(PackratParser):
            """
            a: 'b' !!'a';
            """
        print parser._code
        p = parser('ba')
        res = p.a()
        assert res == 'b'
        assert p.__any__() == 'a'

    def test_regex1(self):
        class parser(PackratParser):
            """
            a: 'b' `a|b`;
            """
        print parser._code
        p = parser('ba')
        res = p.a()
        assert res == 'a'
        py.test.raises(BacktrackException, p.__any__)
        p = parser('bb')
        res = p.a()
        assert res == 'b'
        py.test.raises(BacktrackException, p.__any__)


    def test_regex2(self):
        class parser(PackratParser):
            """
            a: 'b' `[^\n]*`;
            """
        print parser._code
        p = parser('ba#$@@$%\nbc')
        res = p.a()
        assert res == 'a#$@@$%'
        assert p.__any__() == '\n'

    def test_name(self):
        class parser(PackratParser):
            """
            a: c = 'b'
               r = `[^\n]*`
               return {c + r};
            """
        print parser._code
        p = parser('ba#$@@$%\nbc')
        res = p.a()
        assert res == 'ba#$@@$%'
        assert p.__any__() == '\n'

    def test_name2(self):
        class parser(PackratParser):
            """
            a: c = 'b'*
               r = `[^\n]*`
               return {(len(c), r)};
            """
        print parser._code
        p = parser('bbbbbba#$@@$%\nbc')
        res = p.a()
        assert res == (6, "a#$@@$%")
        assert p.__any__() == '\n'

    def test_name3(self):
        class parser(PackratParser):
            """
            a: c = 'd'+
               r = 'f'+
               return {"".join(c) + "".join(r)}
             | c = 'b'*
               r = `[^\n]*`
               return {(len(c), r)};
            """
        print parser._code
        p = parser('bbbbbba#$@@$%\nbc')
        res = p.a()
        assert res == (6, "a#$@@$%")
        assert p.__any__() == '\n'
        p = parser('dddffffx')
        res = p.a()
        assert res == "dddffff"
        assert p.__any__() == 'x'

    def test_nested_repetition(self):
        class parser(PackratParser):
            """
            a: ('a' 'b'*)+;
            """
        print parser._code
        p = parser('aaabbbab')
        res = p.a()
        assert res == [[], [], ['b', 'b', 'b'], ['b']]


    def test_ignore(self):
        class parser(PackratParser):
            """
            a: ('a' ['b'])+;
            """
        print parser._code
        p = parser('abababababab')
        res = p.a()
        assert res == list('aaaaaa')


    def test_regex(self):
        class parser(PackratParser):
            r"""
            a: `\"`;
            """
        print parser._code
        p = parser('"')
        res = p.a()
        assert res == '"'


    def test_memoize_exceptions(self):
        class parser(PackratParser):
            """
            b: 'a';
            """
        print parser._code
        p = parser("c")
        excinfo = py.test.raises(BacktrackException, p.b)
        excinfo = py.test.raises(BacktrackException, p.b)
        excinfo = py.test.raises(BacktrackException, p.b)

    def test_error_character(self):
        class parser(PackratParser):
            """
            b: 'a';
            """
        print parser._code
        p = parser("c")
        excinfo = py.test.raises(BacktrackException, p.b)
        assert excinfo.value.error.pos == 0
        assert excinfo.value.error.expected == ['a']

    def test_error_or(self):
        class parser(PackratParser):
            """
            b: 'a' | 'b';
            """
        print parser._code
        p = parser("c")
        excinfo = py.test.raises(BacktrackException, p.b)
        assert excinfo.value.error.pos == 0
        assert excinfo.value.error.expected == ['a', 'b']

    def test_error_not(self):
        class parser(PackratParser):
            """
            b: 
                'b' !'a';
            """
        p = parser("ba")
        excinfo = py.test.raises(BacktrackException, p.b)
        assert excinfo.value.error.pos == 1
        assert excinfo.value.error.expected == ['NOT a']
        print parser._code

    def test_error_lookahead(self):
        class parser(PackratParser):
            """
            b: 
                'b' !!'a';
            """
        p = parser("bc")
        print parser._code
        excinfo = py.test.raises(BacktrackException, p.b)
        assert excinfo.value.error.pos == 1
        assert excinfo.value.error.expected == ['a']

    def test_error_star(self):
        class parser(PackratParser):
            """
            b: 
                'b'* !__any__;
            """
        print parser._code
        p = parser("bbc")
        print parser._code
        excinfo = py.test.raises(BacktrackException, p.b)
        assert excinfo.value.error.pos == 2
        assert excinfo.value.error.expected == ['b']

    def test_leftrecursion(self):
        class parser(PackratParser):
            """
            b: b 'a' | 'b';
            """
        print parser._code
        p = parser("b")
        res = p.b()
        assert res == "b"
        p = parser("bac")
        res = p.b()
        assert p._pos == 2
        assert res == "a"
        p = parser("baaaaaaaaaaaaaac")
        res = p.b()
        assert p._pos == 15
        assert res == "a"

    def test_leftrecursion_arithmetic(self):
        class parser(PackratParser):
            """
            additive:
                a = additive
                '-'
                b = multitive
                return {a - b}
              | multitive;
            multitive:
                a = multitive
                '*'
                b = simple
                return {a * b}
              | simple;
            simple:
                x = `0|([1-9][0-9]*)`
                return {int(x)};
            """
        print parser._code
        p = parser("5")
        res = p.multitive()
        assert res == 5
        p._pos = 0
        res = p.multitive()
        assert res == 5
        p = parser("5-5-5")
        res = p.additive()
        assert res == -5
        assert p._pos == 5

    def test_leftrecursion_more_choices(self):
        class parser(PackratParser):
            """
            b:
                b 'a'
              | b 'c'
              | 'b';
            """
        print parser._code
        p = parser("b")
        res = p.b()
        assert res == "b"
        p = parser("bcx")
        res = p.b()
        assert p._pos == 2
        assert res == "c"

    def test_if(self):
        class parser(PackratParser):
            """
            INT:
                c = `[1-9][0-9]*`
                return {int(c)};
            b:
                do
                    c = INT
                if {c > 42};
            """
        print parser._code
        p = parser("54")
        res = p.b()
        assert res == 54
        p = parser("12")
        excinfo = py.test.raises(BacktrackException, p.b)
        assert excinfo.value.error.pos == 0
        assert excinfo.value.error.expected == ['condition not met']

