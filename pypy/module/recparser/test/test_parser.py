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

