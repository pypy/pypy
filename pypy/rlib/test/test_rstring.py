
from pypy.translator.translator import TranslationContext
from pypy.rlib import rstring
from pypy.annotation import model as annmodel

class TestAnnotationStringBuilder:
    def annotate(self, func, args):
        t = TranslationContext()
        res = t.buildannotator().build_types(func, args)
        return t, res

    def test_builder(self):
        def f():
            return rstring.builder()
        
        t, res = self.annotate(f, [])
        assert isinstance(res, rstring.SomeStringBuilder)

    def test_methods(self):
        def f(x):
            b = rstring.builder()
            for i in range(x):
                b.append("abc")
            return b.build()

        t, res = self.annotate(f, [int])
        assert isinstance(res, annmodel.SomeString)
