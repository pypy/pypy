
import autopath
from pypy.tool import test

from pypy.annotation.model import SomeValue, ANN, Predicate
from pypy.annotation.annset import AnnotationSet, mostgeneralvalue


c1,c2,c3,c4 = SomeValue(), SomeValue(), SomeValue(), SomeValue()
c5,c6,c7,c8 = SomeValue(), SomeValue(), SomeValue(), SomeValue()

def annset(*args, **kwds):
    "This constructor is just a convenient hack for the tests."
    annset = AnnotationSet()
    groups = []
    for a in args:
        if isinstance(a, Predicate):
            groups.append([a])
        else:
            groups[-1].append(a)    # hack hack hack
    for args in groups:
        annset.set(*args)
    if 'links' in kwds:
        links = kwds['links']
        for i in range(0, len(links), 2):
            if annset.about.get(links[i]) != annset.about.get(links[i+1]):
                assert links[i] not in annset.about
                about = annset.about[links[i]] = annset.about[links[i+1]]
                about.subjects[links[i]] = True
    return annset


class TestAnnotationSet(test.IntTestCase):

    def assertSameSet(self, annset1, annset2):
        self.assertEquals(repr(annset1), repr(annset2))
    
    def assertSameCells(self, annset, firstcell, *cells):
        for cell in cells:
            self.assert_(annset.isshared(firstcell, cell))

    def test_trivial(self):
        a1 = annset(ANN.len, c1, c2,
                    ANN.type, c2, int)
        a2 = annset(ANN.len, c1, c2,
                    ANN.type, c2, int)
        self.assertSameSet(a1, a2)

    def test_get(self):
        a1 = annset(ANN.len, c1, c2,
                    ANN.type, c2, int)
        self.assertEquals(a1.get(ANN.len, c1), c2)
        self.assertEquals(a1.get(ANN.len, c2), mostgeneralvalue)

    def test_set(self):
        a1 = annset(ANN.len, c1, c2,
                    ANN.type, c2, int)
        a1.set(ANN.len, c2, c3)
        self.assertSameSet(a1,
             annset(ANN.len, c1, c2,
                    ANN.type, c2, int,
                    ANN.len, c2, c3))

    def test_kill(self):
        a1 = annset(ANN.len, c1, c2,
                    ANN.type, c2, int)
        for i in range(2):
            a1.kill(ANN.len, c1)
            self.assertSameSet(a1,
                 annset(ANN.type, c2, int))

    def test_merge_mostgeneralvalue(self):
        a1 = annset(ANN.len, c1, c2,
                    ANN.type, c2, int)
        a2 = annset(ANN.len, c1, c2,
                    ANN.type, c2, int)
        # (c3) inter (mostgeneralvalue) == (mostgeneralvalue)
        c = a1.merge(c3, mostgeneralvalue)
        self.assertEquals(c, mostgeneralvalue)
        self.assertSameSet(a1, a2)

    def test_merge_mutable1(self):
        a1 = annset(ANN.len, c1, c2,
                    ANN.len, c3, c2)
        a2 = annset(ANN.len, c1, c2, links=[c3,c1])
        # (c1) inter (c3) == (c1 shared with c3)
        c = a1.merge(c1, c3)
        self.assertSameCells(a1, c, c1, c3)
        self.assertSameSet(a1, a2)

    def test_merge_mutable2(self):
        a1 = annset(ANN.len, c1, c2,
                    ANN.len, c3, c2,
                    ANN.type, c1, list,
                    ANN.type, c2, str)
        a2 = annset(ANN.len, c1, c2,
                    ANN.type, c2, str,
                    links=[c3,c1])
        # (c1) inter (c3) == (c1 shared with c3)
        c = a1.merge(c1, c3)
        self.assertSameCells(a1, c, c1, c3)
        self.assertSameSet(a1, a2)

    def test_merge_immutable1(self):
        a1 = annset(ANN.len, c1, c2,
                    ANN.immutable, c1,
                    ANN.len, c3, c2,
                    ANN.immutable, c3)
        # (c1) inter (c3) == (some new c)
        c = a1.merge(c1, c3)
        a2 = annset(ANN.len, c1, c2,
                    ANN.immutable, c1,
                    ANN.len, c3, c2,
                    ANN.immutable, c3,
                    ANN.len, c, c2,
                    ANN.immutable, c)
        self.assertSameSet(a1, a2)

    def test_merge_immutable2(self):
        a1 = annset(ANN.len, c1, c2,
                    ANN.immutable, c1,
                    ANN.len, c3, c2,
                    ANN.immutable, c3,
                    ANN.type, c1, list,
                    ANN.type, c2, str)
        # (c1) inter (c3) == (some new c)
        c = a1.merge(c1, c3)
        a2 = annset(ANN.len, c1, c2,
                    ANN.immutable, c1,
                    ANN.len, c3, c2,
                    ANN.immutable, c3,
                    ANN.type, c1, list,
                    ANN.type, c2, str,
                    ANN.len, c, c2,
                    ANN.immutable, c)
        self.assertSameSet(a1, a2)

    def test_recursive_merge(self):
        a1 = annset(ANN.tupleitem[2], c1, c2,
                    ANN.immutable, c1,
                    ANN.type, c2, list,
                    ANN.listitems, c2, c3,
                    ANN.type, c3, int,
                    ANN.immutable, c3,
                    ANN.tupleitem[2], c5, c6,
                    ANN.immutable, c5,
                    ANN.type, c6, list,
                    ANN.listitems, c6, c7,
                    ANN.type, c7, float,
                    ANN.immutable, c7)
        c9  = a1.merge(c1, c5)
        c10 = a1.get(ANN.tupleitem[2], c9)
        c11 = a1.get(ANN.listitems, c10)
        self.assertSameCells(a1, c2, c6, c10)
        
        a2 = annset(ANN.tupleitem[2], c1, c2,
                    ANN.immutable, c1,
                    ANN.type, c3, int,
                    ANN.immutable, c3,
                    ANN.tupleitem[2], c5, c6,
                    ANN.immutable, c5,
                    ANN.type, c7, float,
                    ANN.immutable, c7,

                    ANN.tupleitem[2], c9, c10,
                    ANN.immutable, c9,
                    ANN.type, c10, list,
                    ANN.listitems, c10, c11,
                    ANN.immutable, c11,
                    links=[c2,c10,c6,c10])
        self.assertSameSet(a1, a2)

    def test_settype(self):
        a = annset()
        a.settype(c1, int)
        a.settype(c2, list)
        self.assertSameSet(a,
            annset(ANN.type, c1, int,
                   ANN.immutable, c1,
                   ANN.type, c2, list))

    def test_copytype(self):
        a = annset(ANN.type, c1, int,
                   ANN.immutable, c1,
                   ANN.type, c2, list)
        a.copytype(c1, c3)
        a.copytype(c2, c4)
        self.assertSameSet(a,
            annset(ANN.type, c1, int,
                   ANN.immutable, c1,
                   ANN.type, c2, list,
                   ANN.type, c3, int,
                   ANN.immutable, c3,
                   ANN.type, c4, list))


if __name__ == '__main__':
    test.main()
