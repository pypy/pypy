import autopath
from pypy.tool import test
from pypy.objspace.std.dictobject import W_DictObject


class TestW_DictObject(test.TestCase):

    def setUp(self):
        self.space = test.objspace('std')

    def tearDown(self):
        pass

    def test_empty(self):
        space = self.space
        d = W_DictObject(space, [])
        self.failIf_w(d)

    def test_nonempty(self):
        space = self.space
        wNone = space.w_None
        d = W_DictObject(space, [(wNone, wNone)])
        self.failUnless(space.is_true(d))
        i = space.getitem(d, wNone)
        equal = space.eq(i, wNone)
        self.failUnless(space.is_true(equal))

    def test_setitem(self):
        space = self.space
        wk1 = space.wrap('key')
        wone = space.wrap(1)
        d = W_DictObject(space, [(space.wrap('zero'),space.wrap(0))])
        space.setitem(d,wk1,wone)
        wback = space.getitem(d,wk1)
        self.assertEqual_w(wback,wone)

    def test_delitem(self):
        space = self.space
        wk1 = space.wrap('key')
        d = W_DictObject(space,
                              [(space.wrap('zero'),space.wrap(0)),
                               (space.wrap('one'),space.wrap(1)),
                               (space.wrap('two'),space.wrap(2))])
        space.delitem(d,space.wrap('one'))
        self.assertEqual_w(space.getitem(d,space.wrap('zero')),space.wrap(0))
        self.assertEqual_w(space.getitem(d,space.wrap('two')),space.wrap(2))
        self.assertRaises_w(self.space.w_KeyError,
                            space.getitem,d,space.wrap('one'))

    def test_cell(self):
       space = self.space
       wk1 = space.wrap('key')
       d = W_DictObject(space, [])
       w_cell = d.cell(space,wk1)
       cell = space.unwrap(w_cell)
       self.failUnless(cell.is_empty())
       cell.set(space.wrap(1))
       self.assertEqual_w(space.getitem(d,wk1),space.wrap(1))
       wk2 = space.wrap('key2')
       space.setitem(d,wk2,space.wrap(2))
       cell = space.unwrap(d.cell(space,wk2))
       self.assertEqual_w(cell.get(),space.wrap(2))


    def test_wrap_dict(self):
        self.assert_(isinstance(self.space.wrap({}), W_DictObject))


    def test_dict_compare(self):
        w = self.space.wrap
        w0, w1, w2, w3 = map(w, range(4))
        wd1 = self.space.newdict([(w0, w1), (w2, w3)])
        wd2 = self.space.newdict([(w2, w3), (w0, w1)])
        self.assertEqual_w(wd1, wd2)
        wd3 = self.space.newdict([(w2, w2), (w0, w1)])
        self.assertNotEqual_w(wd1, wd3)
        wd4 = self.space.newdict([(w3, w3), (w0, w1)])
        self.assertNotEqual_w(wd1, wd4)
        wd5 = self.space.newdict([(w3, w3)])
        self.assertNotEqual_w(wd1, wd4)
        
                                 
if __name__ == '__main__':
    test.main()
