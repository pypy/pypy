
import autopath
from pypy.tool import test

from pypy.translator.annotation import XCell, XConstant, nothingyet, Annotation


class TestAnnotation(test.IntTestCase):

    def test_is_shared(self):
        c1 = XCell()
        c2 = XCell()
        c3 = XCell()
        c4 = XCell()
        for a in (c1,c2,c3,c4):
            for b in (c1,c2,c3,c4):
                if a is not b:
                    self.failIfEqual(a, b)
        c1.share(c2)
        c4.share(c2)
        c1.share(c3)
        for a in (c1,c2,c3,c4):
            for b in (c1,c2,c3,c4):
                self.assert_(a.is_shared(b))
                self.assertEquals(a, b)

    def test_constant(self):
        self.assertEquals(XConstant(5), XConstant(5))
        self.failIfEqual(XConstant(5), XConstant(6))
        self.failIfEqual(XConstant(5), XCell())

    def test_annotation(self):
        c1 = XCell()
        c2 = XCell()
        c3 = XCell()
        a1 = Annotation('hello', [c1], c2)
        a2 = Annotation('hello', [c1], c3)

        self.assertEquals(a1, a1)
        self.failIfEqual (a1, a2)
        c2.share(c3)
        self.assertEquals(a1, a2)


if __name__ == '__main__':
    test.main()
