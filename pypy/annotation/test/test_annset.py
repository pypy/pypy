
import autopath
from pypy.tool import test

from pypy.annotation.model import ANN, SomeValue, blackholevalue
from pypy.annotation.annset import AnnotationSet, QUERYARG


c1,c2,c3,c4 = SomeValue(), SomeValue(), SomeValue(), SomeValue()


def assertSameSet(testcase, annset, annotations):
    for ann in annotations:
        annset.normalizeann(ann)
    a = list(annset)
    b = annotations
    # try to reorder a to match b, without failing if the lists
    # are different -- this will be checked by assertEquals()
    for i in range(len(b)):
        try:
            j = i + a[i:].index(b[i])
        except ValueError:
            pass
        else:
            a[i], a[j] = a[j], a[i]
    testcase.assertEquals(a, b)

def assertSameCells(testcase, annset, *cells):
    cells = [annset.normalized(c) for c in cells]
    for c in cells[1:]:
        testcase.assertEquals(cells[0], c)


class TestAnnotationSet(test.IntTestCase):
    assertSameSet = assertSameSet
    assertSameCells = assertSameCells

    def test_isshared(self):
        a = AnnotationSet()
        self.assert_(a.isshared(c1, c1))
        self.failIf(a.isshared(c1, c2))
        a.setshared(c1, c2)
        self.assert_(a.isshared(c1, c2))
        self.assert_(a.isshared(c2, c1))
        self.failIf(a.isshared(c1, c3))
        a.setshared(c2, c3)
        self.assert_(a.isshared(c1, c3))
        self.assert_(a.isshared(c2, c3))
        self.assert_(a.isshared(c3, c1))

    def test_normalizeann(self):
        a = AnnotationSet()
        ann1 = ANN.add[c1,c2,c3]
        ann2 = ANN.add[c4,c2,c3]
        a.setshared(c1,c4)
        a.normalizeann(ann1)
        a.normalizeann(ann2)
        self.assertEquals(ann1, ann2)
    
    def test_query_one_annotation_arg(self):
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
        lst = [
            ANN.add[c1, c3, c2],
            ANN.type[c2, c3],
        ]
        a = AnnotationSet(lst)
        clist = a.query(ANN.add[c1, c3, QUERYARG],
                        ANN.type[QUERYARG, c3])
        self.assertEquals(clist, [c2])

    def test_constant(self):
        lst = [
            ANN.constant(42)[c1],
        ]
        a = AnnotationSet(lst)
        clist = a.query(ANN.constant(42)[QUERYARG])
        self.assertEquals(clist, [c1])

    def test_simplify(self):
        lst = [ANN.add[c1, c3, c2],
               ANN.add[c1, c2, c2],
               ANN.neg[c2, c3]]
        a = AnnotationSet(lst)
        a.simplify()
        self.assertSameSet(a, lst)
        
        a.setshared(c2, c3)
        a.simplify()
        self.assertSameSet(a, lst[1:])

    def test_kill(self):
        ann1 = ANN.add[c1, c3, c2]
        lst = [ann1,
               ANN.add[c1, c2, c2],
               ANN.neg[c2, c3]]
        a = AnnotationSet(lst)
        a.kill(ann1)
        self.assertSameSet(a, lst[1:])

    def test_adddependency(self):
        ann1 = ANN.add[c1, c3, c2]
        ann2 = ANN.add[c1, c2, c2]
        ann3 = ANN.add[c1, c1, c2]
        lst = [ann1, ann2, ann3,
               ANN.neg[c2, c3]]
        a = AnnotationSet(lst)
        a.adddependency(ann1, ann2)
        a.adddependency(ann2, ann3)
        a.kill(ann1)
        self.assertSameSet(a, lst[3:])

    def test_merge_blackholevalue(self):
        lst = [ANN.add[c1, c3, c2],
               ANN.neg[c2, c3]]
        a = AnnotationSet(lst)
        # (c3) inter (all annotations) == (c3)
        c = a.merge(c3, blackholevalue)
        self.assertEquals(c, c3)
        self.assertSameSet(a, lst)

    def test_merge_mutable1(self):
        lst = [ANN.type[c1, c3],
               ANN.type[c2, c3],
               ANN.add[c2, c3, c3]]
        a = AnnotationSet(lst)
        # (c1) inter (c2) == (c1 shared with c2)
        c = a.merge(c1, c2)
        self.assertSameCells(a, c, c1, c2)
        self.assertSameSet(a, [ANN.type[c, c3]])

    def test_merge_mutable2(self):
        lst = [ANN.type[c1, c3],
               ANN.type[c2, c3],
               ANN.add[c1, c3, c3]]
        a = AnnotationSet(lst)
        # (c1) inter (c2) == (c1 shared with c2)
        c = a.merge(c1, c2)
        self.assertSameCells(a, c, c1, c2)
        self.assertSameSet(a, [ANN.type[c, c3]])

    def test_merge_immutable1(self):
        lst = [ANN.type[c1, c3],
               ANN.type[c2, c3],
               ANN.immutable[c1],
               ANN.immutable[c2],
               ANN.add[c2, c3, c3]]
        a = AnnotationSet(lst)
        # (c1) inter (c2) == (c1)
        c = a.merge(c1, c2)
        self.assertSameCells(a, c, c1)
        self.failIf(a.isshared(c1, c2))
        self.assertSameSet(a, lst)

    def test_merge_immutable2(self):
        lst = [ANN.type[c1, c3],
               ANN.type[c2, c3],
               ANN.immutable[c1],
               ANN.immutable[c2],
               ANN.add[c1, c3, c3]]
        a = AnnotationSet(lst)
        # (c1) inter (c2) == (some new c)
        c = a.merge(c1, c2)
        self.failIf(a.isshared(c, c1))
        self.failIf(a.isshared(c, c2))  # maybe not needed, but we check that
        self.failIf(a.isshared(c1, c2))
        lst += [ANN.type[c, c3],
                ANN.immutable[c]]
        self.assertSameSet(a, lst)

    def test_merge_mutable_ex(self):
        lst = [ANN.add[c1, c2, c2],
               ANN.neg[c2, c1],
               ANN.add[c3, c2, c2],
               ANN.immutable[c2]]
        a = AnnotationSet(lst)
        # (c1) inter (c3) == (c1 shared with c3)
        c = a.merge(c1, c3)
        self.assertSameCells(a, c, c1, c3)
        self.assertSameSet(a, [lst[0], lst[3]])
        self.assertSameSet(a, [lst[2], lst[3]])

    def test_merge_immutable_ex(self):
        lst = [ANN.add[c1, c2, c2],
               ANN.neg[c2, c1],
               ANN.add[c3, c2, c2],
               ANN.immutable[c1],
               ANN.immutable[c2],
               ANN.immutable[c3]]
        a = AnnotationSet(lst)
        # (c1) inter (c3) == (some new c)
        c = a.merge(c1, c3)
        self.failIf(a.isshared(c, c1))
        self.failIf(a.isshared(c, c3))
        self.failIf(a.isshared(c1, c3))
        lst += [ANN.add[c, c2, c2],
                ANN.immutable[c]]
        self.assertSameSet(a, lst)

##    def dont_test_merge_mutable_ex(self):
##        # This test is expected to fail at this point because the algorithms
##        # are not 100% theoretically correct, but probably quite good and
##        # clear enough right now.  In theory in the intersection below
##        # 'add' should be kept.  In practice the extra 'c3' messes things
##        # up.  I can only think about much-more-obscure algos to fix that.
##        lst = [ANN.add', [c1, c3], c2),
##               ANN.neg', [c2], c1),
##               ANN.add', [c3, c3], c2),
##               ANN.immutable', [], c2)]
##        a = AnnotationHeap(lst)
##        # (c1) inter (c3) == (c1 shared with c3)
##        c = a.merge(c1, c3)
##        self.assertEquals(c, c1)
##        self.assertEquals(c, c3)
##        self.assertEquals(c1, c3)
##        self.assertSameSet(a, [lst[0], lst[3]])
##        self.assertSameSet(a, [lst[2], lst[3]])

##    def dont_test_merge_immutable_ex(self):
##        # Disabled -- same as above.
##        lst = [ANN.add', [c1, c3], c2),
##               ANN.neg', [c2], c1),
##               ANN.add', [c3, c3], c2),
##               ANN.immutable', [], c1),
##               ANN.immutable', [], c2),
##               ANN.immutable', [], c3)]
##        a = AnnotationHeap(lst)
##        # (c1) inter (c3) == (some new c4)
##        c = a.merge(c1, c3)
##        self.failIfEqual(c, c1)
##        self.failIfEqual(c, c3)
##        lst += [ANN.add', [c, c3], c2),
##                ANN.immutable', [], c)]
##        self.assertSameSet(a, lst)


class TestRecording(test.IntTestCase):
    assertSameSet = assertSameSet
    assertSameCells = assertSameCells

    def setUp(self):
        self.lst = [
            ANN.add[c1, c3, c2],
            ANN.type[c1, c4],
            ANN.constant(int)[c4],
        ]
        self.annset = AnnotationSet(self.lst)

    def test_simple(self):
        a = self.annset
        def f(rec):
            if rec.query(ANN.add[c1, c3, QUERYARG]):
                rec.set(ANN.type[c1, c3]) 
        a.record(f)
        self.assertSameSet(a, self.lst + [ANN.type[c1, c3]])

        a.kill(self.lst[0])
        self.assertSameSet(a, self.lst[1:])

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
