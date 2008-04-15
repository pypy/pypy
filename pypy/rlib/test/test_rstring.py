
from pypy.translator.translator import TranslationContext
from pypy.rlib import rstring

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
