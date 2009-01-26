from pypy.conftest import gettestobjspace

def setup_module(mod): 
    mod.space = gettestobjspace(usemodules=['recparser'])


class AppTestRecparser: 
    def setup_class(cls):
        cls.space = space

    def test_simple(self):
        import parser
        parser.suite("great()")

    def test_enc_minimal(self):
        import parser
        parser.suite("# -*- coding: koi8-u -*-*\ngreat()")
        
    def test_simple_ass_totuple(self):
        import parser
        parser.suite("a = 3").totuple()

    def test_futures(self):
        import parser
        src = """
from __future__ import with_statement
def f():
    with foo:
        return 1
        """.strip()
        parser.suite(src)

    def test_compilest(self):
        import parser
        code = parser.compilest(parser.suite('x = 2 + 3'))
        d = {}
        exec code in d
        assert d['x'] == 5

class AppTestRecparserErrors: 
    def setup_class(cls):
        cls.space = space

    def test_sequence2st_bug1(self):
        import parser
        raises(parser.ParserError, parser.sequence2st, ())

    def test_sequence2st_bug1(self):
        import parser
        raises(parser.ParserError, parser.sequence2st, (True,))

    def test_source2ast_bug1(self):
        import parser
        raises(SyntaxError, parser.source2ast, "\xDE\xDA")

    def test_later_error(self):
        import parser
        x = """if:
        def f(x):
            x
             y
        """
        raises(SyntaxError, parser.suite, x)
