import autopath
from pypy.tool import test

class TestUserObject(test.AppTestCase):

    def test_emptyclass(self):
        class empty: pass
        inst = empty()
        self.failUnless(isinstance(inst, empty))
        inst.attr=23
        self.assertEquals(inst.attr,23)

    def test_subclassing(self):
        for base in tuple, list, dict, str, int, float:
            try:
                class subclass(base): pass
                stuff = subclass()
            except:
                print 'not subclassable:', base
            else:
                self.failUnless(isinstance(stuff, base))

    def test_subclasstuple(self):
        class subclass(tuple): pass
        stuff = subclass()
        self.failUnless(isinstance(stuff, tuple))
        stuff.attr = 23
        self.assertEquals(stuff.attr,23)
        self.assertEquals(len(stuff),0)
        result = stuff + (1,2,3)
        self.assertEquals(len(result),3)

    def test_subsubclass(self):
        class base:
            baseattr = 12
        class derived(base):
            derivedattr = 34
        inst = derived()
        self.failUnless(isinstance(inst, base))
        self.assertEquals(inst.baseattr,12)
        self.assertEquals(inst.derivedattr,34)
    

if __name__ == '__main__':
    test.main()
