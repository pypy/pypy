from pypy.tool.udir import udir
from pypy.translator.test import snippet
from pypy.translator.squeak.gensqueak import GenSqueak
from pypy.translator.translator import Translator


def looping(i = (int), j = (int)):
    while i > 0:
	i -= 1
	while j > 0:
	    j -= 1

class TestSqueakTrans:

    def build_sqfunc(self, func):
        try: func = func.im_func
        except AttributeError: pass
        t = Translator(func)
        t.simplify()
        self.gen = GenSqueak(udir, t)

    def test_simple_func(self):
        self.build_sqfunc(snippet.simple_func)

    def test_if_then_else(self):
        self.build_sqfunc(snippet.if_then_else)

    def test_two_plus_two(self):
        self.build_sqfunc(snippet.two_plus_two)

    def test_my_gcd(self):
        self.build_sqfunc(snippet.my_gcd)

    def test_looping(self):
        self.build_sqfunc(looping)
