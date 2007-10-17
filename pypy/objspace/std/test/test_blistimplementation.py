from pypy.objspace.std.test.test_dictmultiobject import FakeSpace
from pypy.objspace.std.test.test_listmultiobject import \
     BaseAppTest_ListMultiObject

import py.test
py.test.skip('Not implemented yet')

from pypy.objspace.std.blistimplementation import BListImplementation

## Most of these tests are from the reference implementation

def _set_get_limit(limit=None):
    from pypy.conftest import option
    from pypy.objspace.std import blistimplementation
    old_value = blistimplementation.limit
    if limit:
        if not option.runappdirect:
            blistimplementation.limit=limit
            cur_value=limit
        else:
            cur_value=old_value
    else:
        cur_value=old_value

    return old_value, cur_value

class AppTest_BListObject(BaseAppTest_ListMultiObject):
    def setup_class(cls):
        BaseAppTest_ListMultiObject.setup_class(cls, 'withblist', 'BListImpl')
        cls.old_limit, cls.limit = _set_get_limit(8)
        cls.w_limit=cls.space.wrap(cls.limit)

    def teardown_class(cls):
        _set_get_limit(cls.old_limit)

    def test_very_long_list(self):
        little_list = [0]
#        big_list = little_list * 2**512 #XXX App-level OverflowError
        big_list = little_list * 2**30

    def test_very_very_long_list(self):
        big_list = [0] * 2**30
        for i in range(20):
            big_list = big_list * 2**30
        assert len(big_list) > 2**512
    
    def test_very_long_list_insert(self):
        little_list = [0]
        big_list = little_list * (2**30)
        big_list = big_list * 2
        big_list.insert((2**31)-5, 1)
        assert big_list[-10:]==[0,0,0,0,1,0,0,0,0,0]

    def test_blist_insert(self):
        l1=list([2,4,6])
        l2=[]
        l2.extend([2,4,6])
        l3=[2,4,6]
        l4=[]
        for i in (2,4,6):
            l4.append(i)
        l5=[]
        l5.extend((2,4,6))
        l1.insert(2,'x')
        l2.insert(2,'x')
        l3.insert(2,'x')
        l4.insert(2,'x')
        l5.insert(2,'x')

        assert l2==[2,4,'x',6]
        assert l5==l4==l3==l2==l1
        
        del l1[:4]
        assert l1==[]

    def test_from_reference_impl1(self):
        limit=self.limit
        n = 512

        data = range(n)
        import random
        random.shuffle(data)
        x = list(data)
        x.sort()

        assert x == sorted(data), x
        assert x[3] == 3
        assert x[100] == 100
        assert x[500] == 500

    def test_from_reference_impl2(self):
        limit=self.limit
        n = 512

        lst = []
        t = tuple(range(n))
        for i in range(n):
            lst.append(i)
            if tuple(lst) != t[:i+1]:
                print i, tuple(lst), t[:i+1]
                print lst.debug()
                break

        x = lst[4:258]
        assert tuple(x) == tuple(t[4:258])
        x.append(-1)
        assert tuple(x) == tuple(t[4:258] + (-1,))
        assert tuple(lst) == t

        lst[200] = 6
        assert tuple(x) == tuple(t[4:258] + (-1,))
        assert tuple(lst) == tuple(t[0:200] + (6,) + t[201:])

        del lst[200]
        #print lst.debug()
        assert tuple(lst) == tuple(t[0:200] + t[201:])

        lst = list(range(n))
        lst.insert(200, 0)
        assert tuple(lst) == (t[0:200] + (0,) + t[200:])
        del lst[200:]
        assert tuple(lst) == tuple(range(200))

    def test_from_reference_impl3(self):
        limit=self.limit
        n = 512

        lst2 = list(range(limit+1))
        assert tuple(lst2) == tuple(range(limit+1))
        del lst2[1]
        del lst2[-1]
        assert tuple(lst2) == (0,) + tuple(range(2,limit))
#        assert lst2.leaf
#        assert len(lst2.children) == limit-1

    def test_from_reference_impl4(self):
        limit=self.limit
        n = 512

        lst = [i for i in range(3)]
        lst*3
        assert lst*3 == range(3)*3

        a = [i for i in 'spam']
        a.extend('eggs')
        assert a == list('spameggs')

        x = [0]
        for i in range(290) + [1000, 10000, 100000, 1000000, 10000000]:
            if len(x*i) != i:
                print 'mul failure', i
                print (x*i).debug()
                break

def test_interp_blist():
    old_limit, limit = _set_get_limit(8)
    def BList(other=[]):
        return BListImplementation(FakeSpace(), other)

    n = 512

    data = range(n)
    import random
    random.shuffle(data)
    x = BList(data)
    #x.sort() # Not used...

    #assert list(x) == sorted(data), x

    lst = BList()
    t = tuple(range(n))
    for i in range(n):
        lst.append(i)
        if tuple(lst) != t[:i+1]:
            print i, tuple(lst), t[:i+1]
            print lst.debug()
            break

    x = lst[4:258]
    assert tuple(x) == tuple(t[4:258])
    x.append(-1)
    assert tuple(x) == tuple(t[4:258] + (-1,))
    assert tuple(lst) == t

    lst[200] = 6
    assert tuple(x) == tuple(t[4:258] + (-1,))
    assert tuple(lst) == tuple(t[0:200] + (6,) + t[201:])

    del lst[200]
    #print lst.debug()
    assert tuple(lst) == tuple(t[0:200] + t[201:])

    lst2 = BList(range(limit+1))
    assert tuple(lst2) == tuple(range(limit+1))
    del lst2[1]
    del lst2[-1]
    assert tuple(lst2) == (0,) + tuple(range(2,limit))
    assert lst2.leaf
    assert len(lst2.children) == limit-1

    lst = BList(range(n))
    lst.insert(200, 0)
    assert tuple(lst) == (t[0:200] + (0,) + t[200:])
    del lst[200:]
    assert tuple(lst) == tuple(range(200))

    lst = BList(range(3))
    lst*3
    assert lst*3 == range(3)*3

    a = BList('spam')
    a.extend('eggs')
    assert a == list('spameggs')

    x = BList([0])
    for i in range(290) + [1000, 10000, 100000, 1000000, 10000000]:
        if len(x*i) != i:
            print 'mul failure', i
            print (x*i).debug()
            break

    little_list = BList([0])
    #big_list = little_list * 2**512
    big_list = little_list * 2**30
