from pypy.objspace.std import StdObjSpace 

def setup_module(mod): 
    mod.space = StdObjSpace(usemodules=['recparser'])


class AppTestRecparser: 
    def setup_class(cls):
        cls.space = space

    def test_simple(self):
        import parser
        parser.suite("great()")

    def test_enc_minimal(self):
        import parser
        parser.suite("# -*- coding: koi8-u -*-*\ngreat()")
