from pypy.conftest import gettestobjspace

def setup_module(mod):
    mod.space = gettestobjspace(usemodules=["parser"])

class ParserModuleTest:

    def setup_class(cls):
        cls.space = space
        cls.w_m = space.appexec([], """():
    import parser
    return parser""")


class AppTestParser(ParserModuleTest):

    def test_suite(self):
        s = self.m.suite("x = 4")
        assert isinstance(s, self.m.STType)
        assert self.m.issuite(s)
        assert s.issuite()
        assert not self.m.isexpr(s)
        assert not s.isexpr()

    def test_expr(self):
        s = self.m.expr("x")
        assert isinstance(s, self.m.STType)
        assert self.m.isexpr(s)
        assert s.isexpr()
        assert not self.m.issuite(s)
        assert not s.issuite()

    def test_totuple_and_tolist(self):
        for meth, tp in (("totuple", tuple), ("tolist", list)):
            s = self.m.suite("x = 4")
            seq = getattr(s, meth)()
            assert isinstance(seq, tp)
            assert len(seq) == 4
            assert seq[0] == 286
            assert len(seq[2]) == 2
            assert len(seq[3]) == 2
            assert seq[2][0] == 4
            assert seq[3][0] == 0
            seq = getattr(s, meth)(True)
            assert len(seq[2]) == 3
            assert seq[2][2] == 1
            seq = getattr(s, meth)(True, True)
            assert len(seq[2]) == 4
            assert seq[2][2] == 1
            assert seq[2][3] == 0

    def test_compile(self):
        import types
        for code in (self.m.suite("x = 4").compile(),
                     self.m.compilest(self.m.suite("x = 4"))):
            assert isinstance(code, types.CodeType)
            assert code.co_filename == "<syntax-tree>"
