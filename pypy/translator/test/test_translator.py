import autopath
from pypy.tool import testit
from pypy.translator.translator import Translator

from pypy.translator.test import snippet


class TranslatorTestCase(testit.IntTestCase):

    def test_set_attr(self):
        t = Translator(snippet.set_attr)
        t.annotate([])
        set_attr = t.compile()
        self.assertEquals(set_attr(), 2)

    def test_inheritance2(self):
        t = Translator(snippet.inheritance2)
        t.annotate([])
        inheritance2 = t.compile()
        self.assertEquals(inheritance2(), ((-12, -12), (3, "world")))

    def test_simple_method(self):
        t = Translator(snippet.simple_method)
        t.annotate([int]).simplify()
        simple_method = t.compile()
        self.assertEquals(simple_method(55), 55)

if __name__ == '__main__':
    testit.main()
