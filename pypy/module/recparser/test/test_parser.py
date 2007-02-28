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

