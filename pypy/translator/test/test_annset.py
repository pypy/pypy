
import autopath
from pypy.tool import test

from pypy.translator.annset import Cell, AnnotationSet
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation


class TestCell(test.IntTestCase):

    def test_set(self):
        c1 = Cell()
        v1 = Variable('v1')
        c1.set(v1)
        self.assertEquals(c1.content, v1)
        c2 = Cell()
        k2 = Constant(123)
        c2.set(k2)
        self.assertEquals(c2.content, k2)
        self.assertRaises(ValueError, c1.set, k2)
        self.assertRaises(ValueError, c2.set, v1)
        self.assertRaises(ValueError, c1.set, c2)
        self.assertRaises(ValueError, c2.set, c1)

    def test_share1(self):
        k1 = Constant(-123)
        c1 = Cell()
        c2 = Cell()
        c1.share(c2)
        c2.set(k1)
        self.assertEquals(c1.content, k1)
        self.assertEquals(c2.content, k1)

    def test_share2(self):
        k1 = Constant(-123)
        c1 = Cell()
        c2 = Cell()
        c2.set(k1)
        c1.share(c2)
        self.assertEquals(c1.content, k1)
        self.assertEquals(c2.content, k1)

    def test_share3(self):
        k1 = Constant(-123)
        c1 = Cell()
        c2 = Cell()
        c1.share(c2)
        c1.set(k1)
        self.assertEquals(c1.content, k1)
        self.assertEquals(c2.content, k1)

    def test_share3(self):
        k1 = Constant(-123)
        c1 = Cell()
        c2 = Cell()
        c1.set(k1)
        c1.share(c2)
        self.assertEquals(c1.content, k1)
        self.assertEquals(c2.content, k1)

    def test_is_shared(self):
        c1 = Cell()
        c2 = Cell()
        c3 = Cell()
        c4 = Cell()
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


class TestAnnotationSet(test.IntTestCase):

    def setUp(self):
        self.v1 = Variable('v1')
        self.v2 = Variable('v2')
        self.v3 = Variable('v3')
        self.k1 = Constant(102938)
        self.k2 = Constant('foobar')
        self.k3 = Constant(-2)
        self.k4 = Constant(102938)

    def assertSameSet(self, a, b):
        a = list(a)
        b = list(b)
        # try to reorder a to match b, without failing if the lists
        # are different -- this will be checked by assertEquals()
        for i in range(len(b)):
            try:
                j = i + a[i:].index(b[i])
            except ValueError:
                pass
            else:
                a[i], a[j] = a[j], a[i]
        self.assertEquals(a, b)

    def test_init(self):
        lst = [SpaceOperation('add', [self.v1, self.k1], self.v2),
               SpaceOperation('neg', [self.v2], self.v3)]
        a = AnnotationSet(lst)
        self.assertSameSet(a, lst)

    def test_add(self):
        lst = [SpaceOperation('add', [self.v1, self.k1], self.v2),
               SpaceOperation('neg', [self.v2], self.v3)]
        a = AnnotationSet()
        a.add(lst[1])
        a.add(lst[0])
        self.assertSameSet(a, lst)
        a.add(lst[0])
        self.assertSameSet(a, lst)
        a.add(lst[1])
        self.assertSameSet(a, lst)

    def test_add2(self):
        c1 = Cell()
        c2 = Cell()
        c3 = Cell()
        c4 = Cell()
        c5 = Cell()
        c6 = Cell()
        c7 = Cell()
        c8 = Cell()
        c9 = Cell()
        a = AnnotationSet()
        op = SpaceOperation('add', [c1, c2], c3)
        a.add(op)
        self.assertSameSet(a, [op])
        op = SpaceOperation('add', [c4, self.k1], c5)
        a.add(op)
        self.assertSameSet(a, [op])
        op = SpaceOperation('add', [c6, self.k4], self.v3)
        a.add(op)
        self.assertSameSet(a, [op])
        op = SpaceOperation('add', [self.v1, self.k1], self.v3)
        a.add(op)
        self.assertSameSet(a, [op])
        
        a.add(SpaceOperation('add', [self.v1, c7], self.v3))
        self.assertSameSet(a, [op])
        a.add(SpaceOperation('add', [self.v1, c9], c8))
        self.assertSameSet(a, [op])

    def test_match1(self):
        lst = [SpaceOperation('add', [self.v1, self.k1], self.v2),
               SpaceOperation('neg', [self.v1], self.k2),
               SpaceOperation('neg', [self.v2], self.v3)]
        a = AnnotationSet(lst)
        for ann in lst:
            self.assert_(a.match(ann))
        c = Cell()
        self.assert_(a.match(SpaceOperation('add', [self.v1, self.k4], c)))
        self.assertEquals(c.content, self.v2)
        c = Cell()
        c2 = Cell()
        self.assert_(a.match(SpaceOperation('add', [self.v1, c], c2)))
        self.assertEquals(c.content, self.k1)
        self.assertEquals(c2.content, self.v2)
        c = Cell()
        self.assert_(a.match(SpaceOperation('neg', [c], self.v3)))
        self.assertEquals(c.content, self.v2)
        c = Cell()
        self.failIf(a.match(SpaceOperation('add', [self.v2, self.k1], self.v2)))
        self.failIf(a.match(SpaceOperation('add', [self.v2, self.k1], c)))

    def test_match2(self):
        c1 = Cell()
        c2 = Cell()
        c3 = Cell()
        c4 = Cell()
        c4.share(c3)
        c1.set(self.k4)
        lst = [SpaceOperation('add', [self.v1, c1], self.v2),
               SpaceOperation('neg', [self.v1], c2),
               SpaceOperation('neg', [self.v2], c4)]
        a = AnnotationSet(lst)
        self.assert_(a.match(SpaceOperation('add', [self.v1, self.k1], self.v2)))
        c = Cell()
        self.assert_(a.match(SpaceOperation('add', [self.v1, self.k1], c)))
        self.assertEquals(c.content, self.v2)
        c = Cell()
        self.assert_(a.match(SpaceOperation('neg', [self.v2], c)))
        self.assert_(c.is_shared(c4))
        self.assert_(c.is_shared(c3))
        self.assert_(not c.is_shared(c2))
        self.assert_(not c.is_shared(c1))
        
        self.assertEquals(c1.content, self.k1)
        self.assertEquals(c2.content, None)
        self.assertEquals(c3.content, None)
        self.assertEquals(c4.content, None)

    def test_enumerate(self):
        lst = [SpaceOperation('add', [self.v1, self.k1], self.v2),
               SpaceOperation('neg', [self.v1], self.k2),
               SpaceOperation('neg', [self.v2], self.v3)]
        a = AnnotationSet(lst)
        self.assertSameSet(list(a.enumerate()), lst)

    def test_renaming(self):
        lst = [SpaceOperation('add', [self.v1, self.k1], self.v2),
               SpaceOperation('neg', [self.v1], self.k2),
               SpaceOperation('neg', [self.v2], self.v3)]
        renaming = {self.v1: [self.v3],
                    self.v2: [self.v2, self.v1]}
        lst2 = [SpaceOperation('add', [self.v3, self.k1], self.v2),
                SpaceOperation('add', [self.v3, self.k1], self.v1),
                SpaceOperation('neg', [self.v3], self.k2)]
        a = AnnotationSet(lst)
        self.assertSameSet(list(a.enumerate(renaming)), lst2)

    def test_intersect(self):
        lst = [SpaceOperation('type', [self.v2], self.k1),
               SpaceOperation('type', [self.v1], self.k1),
               SpaceOperation('type', [self.v3], self.k1),
               ]
        lst2 = [SpaceOperation('type', [self.v2], self.k4),
                SpaceOperation('type', [self.v1], self.k4),
                SpaceOperation('add', [self.v1, self.v2], self.v3),
                ]
        lst3 = [SpaceOperation('type', [self.v2], self.k1),
                SpaceOperation('type', [self.v1], self.k1),
                ]
        a = AnnotationSet(lst)
        a.intersect(AnnotationSet(lst2))
        self.assertSameSet(a, lst3)


if __name__ == '__main__':
    test.main()
