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

class Test_DictObject(test.AppTestCase):
    
        
    def test_clear(self):
        self.d = {1:2, 3:4}
        self.d.clear()
        self.assertEqual(len(self.d), 0)
                         
    def test_copy(self):
        self.d = {1:2, 3:4}
        dd = self.d.copy()
        self.assertEqual(self.d, dd)
        self.failIf(self.d is dd)
        
    def test_get(self):
        self.d = {1:2, 3:4}
        self.assertEqual(self.d.get(1), 2)
        self.assertEqual(self.d.get(1,44), 2)
        self.assertEqual(self.d.get(33), None)
        self.assertEqual(self.d.get(33,44), 44)

    def test_pop(self):
        self.d = {1:2, 3:4}
        dd = self.d.copy()
        result = dd.pop(1)
        self.assertEqual(result, 2)
        self.assertEqual(len(dd), 1)
        dd = self.d.copy()
        result = dd.pop(1, 44)
        self.assertEqual(result, 2)
        self.assertEqual(len(dd), 1)
        result = dd.pop(1, 44)
        self.assertEqual(result, 44)
        self.assertEqual(len(dd), 1)
        self.assertRaises(KeyError, dd.pop, 33)
    
    def test_has_key(self):
        self.d = {1:2, 3:4}
        self.failUnless(self.d.has_key(1))
        self.failIf(self.d.has_key(33))
    
    def test_items(self):
        self.d = {1:2, 3:4}
        its = self.d.items()
        its.sort()
        self.assertEqual(its, [(1,2),(3,4)])
    
    def notyet_test_iteritems(self):
        pass
    
    def notyet_test_iterkeys(self):
        pass
    
    def notyet_test_itervalues(self):
        pass
    
    def test_keys(self):
        self.d = {1:2, 3:4}
        kys = self.d.keys()
        kys.sort()
        self.assertEqual(kys, [1,3])
    
    def test_popitem(self):
        self.d = {1:2, 3:4}
        it = self.d.popitem()
        self.assertEqual(len(self.d), 1)
        self.failUnless(it==(1,2) or it==(3,4))
        it1 = self.d.popitem()
        self.assertEqual(len(self.d), 0)
        self.failUnless((it!=it1) and (it1==(1,2) or it1==(3,4)))
    
    def test_setdefault(self):
        self.d = {1:2, 3:4}
        dd = self.d.copy()
        x = dd.setdefault(1, 99)
        self.assertEqual(self.d, dd)
        self.assertEqual(x, 2)
        x = dd.setdefault(33, 99)
        self.d[33] = 99
        self.assertEqual(self.d, dd)
        self.assertEqual(x, 99)
    
    def test_update(self):
        self.d = {1:2, 3:4}
        dd = self.d.copy()
        self.d.update({})
        self.assertEqual(self.d, dd)
        self.d.update({3:5, 6:7})
        self.assertEqual(self.d, {1:2, 3:5, 6:7})
    
    def test_values(self):
        self.d = {1:2, 3:4}
        vals = self.d.values()
        vals.sort()
        self.assertEqual(vals, [2,4])

    

        
                                 
if __name__ == '__main__':
    test.main()
