import re, py
from rpython.rlib.rsre import rsre_core
from rpython.rlib.rsre.test.test_match import get_code, get_code_and_re


class TestSearch:

    def test_code1(self):
        r_code1 = get_code(r'[abc][def][ghi]')
        res = rsre_core.search(r_code1, "fooahedixxx")
        assert res is None
        res = rsre_core.search(r_code1, "fooahcdixxx")
        assert res is not None
        assert res.span() == (5, 8)

    def test_code2(self):
        r_code2 = get_code(r'<item>\s*<title>(.*?)</title>')
        res = rsre_core.search(r_code2, "foo bar <item>  <title>abc</title>def")
        assert res is not None
        assert res.span() == (8, 34)

    def test_pure_literal(self):
        r_code3 = get_code(r'foobar')
        res = rsre_core.search(r_code3, "foo bar foobar baz")
        assert res is not None
        assert res.span() == (8, 14)

    def test_code3(self):
        r_code1 = get_code(r'<item>\s*<title>(.*?)</title>')
        res = rsre_core.match(r_code1, "<item>  <title>abc</title>def")
        assert res is not None

    def test_max_until_0_65535(self):
        r_code2 = get_code(r'<abc>(?:xy)*xy</abc>')
        #res = rsre_core.match(r_code2, '<abc></abc>def')
        #assert res is None
        #res = rsre_core.match(r_code2, '<abc>xy</abc>def')
        #assert res is not None
        res = rsre_core.match(r_code2, '<abc>xyxyxy</abc>def')
        assert res is not None
        res = rsre_core.match(r_code2, '<abc>' + 'xy'*1000 + '</abc>def')
        assert res is not None

    def test_max_until_3_5(self):
        r_code2, r = get_code_and_re(r'<abc>(?:xy){3,5}xy</abc>')
        for i in range(8):
            s = '<abc>' + 'xy'*i + '</abc>defdefdefdefdef'
            assert (r.match(s) is not None) is (3 <= i-1 <= 5)
            res = rsre_core.match(r_code2, s)
            assert (res is not None) is (3 <= i-1 <= 5)

    def test_min_until_0_65535(self):
        r_code2 = get_code(r'<abc>(?:xy)*?xy</abc>')
        res = rsre_core.match(r_code2, '<abc></abc>def')
        assert res is None
        res = rsre_core.match(r_code2, '<abc>xy</abc>def')
        assert res is not None
        res = rsre_core.match(r_code2, '<abc>xyxyxy</abc>def')
        assert res is not None
        res = rsre_core.match(r_code2, '<abc>' + 'xy'*1000 + '</abc>def')
        assert res is not None

    def test_min_until_3_5(self):
        r_code2, r = get_code_and_re(r'<abc>(?:xy){3,5}?xy</abc>')
        for i in range(8):
            s = '<abc>' + 'xy'*i + '</abc>defdefdefdefdef'
            assert (r.match(s) is not None) is (3 <= i-1 <= 5)
            res = rsre_core.match(r_code2, s)
            assert (res is not None) is (3 <= i-1 <= 5)

    def test_min_repeat_one(self):
        r_code3 = get_code(r'<abc>.{3,5}?y')
        for i in range(8):
            res = rsre_core.match(r_code3, '<abc>' + 'x'*i + 'y')
            assert (res is not None) is (3 <= i <= 5)

    def test_simple_group(self):
        r_code4 = get_code(r'<abc>(x.)</abc>')
        res = rsre_core.match(r_code4, '<abc>xa</abc>def')
        assert res is not None
        assert res.get_mark(0) == 5
        assert res.get_mark(1) == 7

    def test_max_until_groups(self):
        r_code4 = get_code(r'<abc>(x.)*xy</abc>')
        res = rsre_core.match(r_code4, '<abc>xaxbxy</abc>def')
        assert res is not None
        assert res.get_mark(0) == 7
        assert res.get_mark(1) == 9

    def test_group_branch(self):
        r_code5 = get_code(r'<abc>(ab|c)</abc>')
        res = rsre_core.match(r_code5, '<abc>ab</abc>def')
        assert (res.get_mark(0), res.get_mark(1)) == (5, 7)
        res = rsre_core.match(r_code5, '<abc>c</abc>def')
        assert (res.get_mark(0), res.get_mark(1)) == (5, 6)
        res = rsre_core.match(r_code5, '<abc>de</abc>def')
        assert res is None

    def test_group_branch_max_until(self):
        r_code6 = get_code(r'<abc>(ab|c)*a</abc>')
        res = rsre_core.match(r_code6, '<abc>ccabcccaba</abc>def')
        assert (res.get_mark(0), res.get_mark(1)) == (12, 14)
        r_code7 = get_code(r'<abc>((ab)|(c))*a</abc>')
        res = rsre_core.match(r_code7, '<abc>ccabcccaba</abc>def')
        assert (res.get_mark(0), res.get_mark(1)) == (12, 14)
        assert (res.get_mark(2), res.get_mark(3)) == (12, 14)
        assert (res.get_mark(4), res.get_mark(5)) == (11, 12)

    def test_group_7(self):
        r_code7, r7 = get_code_and_re(r'<abc>((a)?(b))*</abc>')
        match = r7.match('<abc>bbbabbbb</abc>')
        assert match.span(1) == (12, 13)
        assert match.span(3) == (12, 13)
        assert match.span(2) == (8, 9)
        res = rsre_core.match(r_code7, '<abc>bbbabbbb</abc>')
        assert (res.get_mark(0), res.get_mark(1)) == (12, 13)
        assert (res.get_mark(4), res.get_mark(5)) == (12, 13)
        assert (res.get_mark(2), res.get_mark(3)) == (8, 9)

    def test_group_branch_repeat_complex_case(self):
        r_code8, r8 = get_code_and_re(r'<abc>((a)|(b))*</abc>')
        match = r8.match('<abc>ab</abc>')
        assert match.span(1) == (6, 7)
        assert match.span(3) == (6, 7)
        assert match.span(2) == (5, 6)
        res = rsre_core.match(r_code8, '<abc>ab</abc>')
        assert (res.get_mark(0), res.get_mark(1)) == (6, 7)
        assert (res.get_mark(4), res.get_mark(5)) == (6, 7)
        assert (res.get_mark(2), res.get_mark(3)) == (5, 6)

    def test_minuntil_lastmark_restore(self):
        r_code9, r9 = get_code_and_re(r'(x|yz)+?(y)??c')
        match = r9.match('xyzxc')
        assert match.span(1) == (3, 4)
        assert match.span(2) == (-1, -1)
        res = rsre_core.match(r_code9, 'xyzxc')
        assert (res.get_mark(0), res.get_mark(1)) == (3, 4)
        assert (res.get_mark(2), res.get_mark(3)) == (-1, -1)

    def test_minuntil_bug(self):
        r_code9, r9 = get_code_and_re(r'((x|yz)+?(y)??c)*')
        match = r9.match('xycxyzxc')
        assert match.span(2) == (6, 7)
        #assert match.span(3) == (1, 2) --- bug of CPython
        res = rsre_core.match(r_code9, 'xycxyzxc')
        assert (res.get_mark(2), res.get_mark(3)) == (6, 7)
        assert (res.get_mark(4), res.get_mark(5)) == (1, 2)

    def test_empty_maxuntil(self):
        r_code, r = get_code_and_re(r'(a?)+y')
        assert r.match('y')
        assert r.match('aaayaaay').span() == (0, 4)
        res = rsre_core.match(r_code, 'y')
        assert res
        res = rsre_core.match(r_code, 'aaayaaay')
        assert res and res.span() == (0, 4)
        #
        r_code, r = get_code_and_re(r'(a?){4,6}y')
        assert r.match('y')
        res = rsre_core.match(r_code, 'y')
        assert res
        #
        r_code, r = get_code_and_re(r'(a?)*y')
        assert r.match('y')
        res = rsre_core.match(r_code, 'y')
        assert res

    def test_empty_maxuntil_2(self):
        try:
            r_code, r = get_code_and_re(r'X(.*?)+X')
        except re.error as e:
            py.test.skip("older version of the stdlib: %s" % (e,))
        assert r.match('XfooXbarX').span() == (0, 5)
        assert r.match('XfooXbarX').span(1) == (4, 4)
        res = rsre_core.match(r_code, 'XfooXbarX')
        assert res.span() == (0, 5)
        assert res.span(1) == (4, 4)

    def test_empty_minuntil(self):
        r_code, r = get_code_and_re(r'(a?)+?y')
        #assert not r.match('z') -- CPython bug (at least 2.5) eats all memory
        res = rsre_core.match(r_code, 'z')
        assert not res
        #
        r_code, r = get_code_and_re(r'(a?){4,6}?y')
        assert not r.match('z')
        res = rsre_core.match(r_code, 'z')
        assert not res
        #
        r_code, r = get_code_and_re(r'(a?)*?y')
        #assert not r.match('z') -- CPython bug (at least 2.5) eats all memory
        res = rsre_core.match(r_code, 'z')
        assert not res

    def test_empty_search(self):
        r_code, r = get_code_and_re(r'')
        for j in range(-2, 6):
            for i in range(-2, 6):
                match = r.search('abc', i, j)
                res = rsre_core.search(r_code, 'abc', i, j)
                jk = min(max(j, 0), 3)
                ik = min(max(i, 0), 3)
                if ik <= jk:
                    assert match is not None
                    assert match.span() == (ik, ik)
                    assert res is not None
                    assert res.match_start == ik and res.match_end == ik
                else:
                    assert match is None
                    assert res is None
