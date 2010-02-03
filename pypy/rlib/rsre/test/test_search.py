import re, _sre
from pypy.rlib.rsre import rsre


class TestSearch:

    def get_code(self, regexp):
        class GotIt(Exception):
            pass
        def my_compile(pattern, flags, code, *args):
            raise GotIt(code)
        saved = _sre.compile
        try:
            _sre.compile = my_compile
            try:
                re.compile(regexp)
            except GotIt, e:
                return e.args[0]
        finally:
            _sre.compile = saved
        assert 0, "did not reach my_compile()?"

    def test_code1(self):
        r_code1 = self.get_code(r'<item>\s*<title>(.*?)</title>')
        state = rsre.SimpleStringState("foo<item>  <title>abc</title>def")
        res = state.search(r_code1)
        assert res is True
        groups = state.create_regs(1)
        assert groups[0] == (3, 29)
        assert groups[1] == (18, 21)

    def test_code2_fail(self):
        r_code2 = self.get_code(r'x((a)|(b)|(c)|(d)|(e)|(f)|(g)|(h)|(i))|(j)')
        state = rsre.SimpleStringState("i")
        res = state.match(r_code2)
        assert res is False

    def test_code2_success(self):
        r_code2 = self.get_code(r'x((a)|(b)|(c)|(d)|(e)|(f)|(g)|(h)|(i))|(j)')
        state = rsre.SimpleStringState("j")
        res = state.match(r_code2)
        assert res is True
        groups = state.create_regs(11)
        assert groups[0] == (0, 1)
        for i in range(1, 12):
            if i == 11:
                assert groups[i] == (0, 1)
            else:
                assert groups[i] == (-1, -1)
