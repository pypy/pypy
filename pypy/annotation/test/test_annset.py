
import autopath
from pypy.tool import test

from pypy.annotation.model import ann, SomeValue
from pypy.annotation.annset import AnnotationSet


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
    
    def test_query_one_annotation_arg(self):
        c1,c2,c3 = SomeValue(), SomeValue(), SomeValue()
        lst = [ann.add[c1, c3, c2]]
        a = AnnotationSet(lst)
        c = a.query(ann.add[c1, c3, ...])
        self.assertEquals(c, [c2])
        c = a.query(ann.add[c1, ..., c2])
        self.assertEquals(c, [c3])
        c = a.query(ann.add[..., c3, c2])
        self.assertEquals(c, [c1])

        c = a.query(ann.add[..., c1, c2])
        self.assertEquals(c, [])

    def test_query_multiple_annotations(self):
        c1,c2,c3 = SomeValue(), SomeValue(), SomeValue()
        lst = [
            ann.add[c1, c3, c2],
            ann.snuff[c2, c3],
        ]
        a = AnnotationSet(lst)
        c = a.query(ann.add[c1, c3, ...],
                    ann.snuff[..., c3])
        self.assertEquals(c, [c2])

if __name__ == '__main__':
    test.main()
