
import autopath
from pypy.tool import test

from pypy.annotation.model import ANN, SomeValue
from pypy.annotation.annset import AnnotationSet, QUERYARG


class TestAnnotationSet(test.IntTestCase):
            
    def test_shared_values(self):
        c1,c2,c3 = SomeValue(), SomeValue(), SomeValue()
        a = AnnotationSet()
        self.assert_(a.isshared(c1, c1))
        self.failIf(a.isshared(c1, c2))
        a.setshared(c1, c2)
        self.assert_(a.isshared(c1, c2))
        self.assert_(a.isshared(c2, c1))
        self.assertEquals(a.tempid(c1), a.tempid(c2))
        self.failIfEqual(a.tempid(c1), a.tempid(c3))
        self.failIf(a.isshared(c1, c3))
        a.setshared(c2, c3)
        self.assert_(a.isshared(c1, c3))
        self.assert_(a.isshared(c2, c3))
        self.assert_(a.isshared(c3, c1))
        self.assertEquals(a.tempid(c1), a.tempid(c3))

    def test_shared_values_nomatch(self):
        c1,c2 = SomeValue(), SomeValue()
        a = AnnotationSet()
        id1 = a.tempid(c1)
        id2 = a.tempid(c2)
        self.assertNotEquals(id1, id2)

    def test_annequal(self):
        c1,c2,c3,c4 = SomeValue(), SomeValue(), SomeValue(), SomeValue()
        a = AnnotationSet()
        a.setshared(c1,c4)
        self.assert_(a.annequal(ANN.add[c1,c2,c3],
                                ANN.add[c4,c2,c3]))
    
    def test_query_one_annotation_arg(self):
        c1,c2,c3 = SomeValue(), SomeValue(), SomeValue()
        lst = [ANN.add[c1, c3, c2]]
        a = AnnotationSet(lst)
        clist = a.query(ANN.add[c1, c3, QUERYARG])
        self.assertEquals(clist, [c2])
        clist = a.query(ANN.add[c1, QUERYARG, c2])
        self.assertEquals(clist, [c3])
        clist = a.query(ANN.add[QUERYARG, c3, c2])
        self.assertEquals(clist, [c1])

        clist = a.query(ANN.add[QUERYARG, c1, c2])
        self.assertEquals(clist, [])

    def test_query_multiple_annotations(self):
        c1,c2,c3 = SomeValue(), SomeValue(), SomeValue()
        lst = [
            ANN.add[c1, c3, c2],
            ANN.type[c2, c3],
        ]
        a = AnnotationSet(lst)
        clist = a.query(ANN.add[c1, c3, QUERYARG],
                        ANN.type[QUERYARG, c3])
        self.assertEquals(clist, [c2])

    def test_constant(self):
        c1,c2,c3 = SomeValue(), SomeValue(), SomeValue()
        lst = [
            ANN.constant(42)[c1],
        ]
        a = AnnotationSet(lst)
        clist = a.query(ANN.constant(42)[QUERYARG])
        self.assertEquals(clist, [c1])

c1,c2,c3,c4 = SomeValue(), SomeValue(), SomeValue(), SomeValue()

class TestRecording(test.IntTestCase):

    def setUp(self):
        self.lst = [
            ANN.add[c1, c3, c2],
            ANN.type[c1, c4],
            ANN.constant(int)[c4],
        ]
        self.annset = AnnotationSet(self.lst)

    def assertSameSet(self, annset, a, b):
        a = [annset.temporarykey(a1) for a1 in a]
        b = [annset.temporarykey(b1) for b1 in b]
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

    def test_simple(self):
        a = self.annset
        def f(rec):
            if rec.query(ANN.add[c1, c3, QUERYARG]):
                rec.set(ANN.type[c1, c3]) 
        a.record(f)
        self.assertSameSet(a, a, self.lst + [ANN.type[c1, c3]])

        a.kill(self.lst[0])
        self.assertSameSet(a, a, self.lst[1:])

    def test_type(self):
        a = self.annset
        def f(rec):
            if rec.check_type(c1, int):
                rec.set_type(c2, str)
        a.record(f)
        self.assert_(a.query(ANN.type[c2, QUERYARG],
                             ANN.constant(str)[QUERYARG]))

if __name__ == '__main__':
    test.main()
