import autopath
from pypy.objspace.std.dictobject import W_DictObject


objspacename = 'std'

class TestW_DictObject:

    def test_empty(self):
        space = self.space
        d = W_DictObject(space, [])
        assert not self.space.is_true(d)

    def test_nonempty(self):
        space = self.space
        wNone = space.w_None
        d = W_DictObject(space, [(wNone, wNone)])
        assert space.is_true(d)
        i = space.getitem(d, wNone)
        equal = space.eq(i, wNone)
        assert space.is_true(equal)

    def test_setitem(self):
        space = self.space
        wk1 = space.wrap('key')
        wone = space.wrap(1)
        d = W_DictObject(space, [(space.wrap('zero'),space.wrap(0))])
        space.setitem(d,wk1,wone)
        wback = space.getitem(d,wk1)
        assert self.space.eq_w(wback,wone)

    def test_delitem(self):
        space = self.space
        wk1 = space.wrap('key')
        d = W_DictObject(space,
                              [(space.wrap('zero'),space.wrap(0)),
                               (space.wrap('one'),space.wrap(1)),
                               (space.wrap('two'),space.wrap(2))])
        space.delitem(d,space.wrap('one'))
        assert self.space.eq_w(space.getitem(d,space.wrap('zero')),space.wrap(0))
        assert self.space.eq_w(space.getitem(d,space.wrap('two')),space.wrap(2))
        self.space.raises_w(self.space.w_KeyError,
                            space.getitem,d,space.wrap('one'))

    def test_wrap_dict(self):
        assert isinstance(self.space.wrap({}), W_DictObject)


    def test_dict_compare(self):
        w = self.space.wrap
        w0, w1, w2, w3 = map(w, range(4))
        wd1 = self.space.newdict([(w0, w1), (w2, w3)])
        wd2 = self.space.newdict([(w2, w3), (w0, w1)])
        assert self.space.eq_w(wd1, wd2)
        wd3 = self.space.newdict([(w2, w2), (w0, w1)])
        assert not self.space.eq_w(wd1, wd3)
        wd4 = self.space.newdict([(w3, w3), (w0, w1)])
        assert not self.space.eq_w(wd1, wd4)
        wd5 = self.space.newdict([(w3, w3)])
        assert not self.space.eq_w(wd1, wd4)

    def test_dict_call(self):
        space = self.space
        w = space.wrap
        wd = space.newdict
        def mydict(w_args=w(()), w_kwds=w({})):
            return space.call(space.w_dict, w_args, w_kwds)
        def deepwrap(lp):
            return [[w(a),w(b)] for a,b in lp]
        d = mydict()
        assert self.space.eq_w(d, w({}))
        args = w(([['a',2],[23,45]],))
        d = mydict(args)
        assert self.space.eq_w(d, wd(deepwrap([['a',2],[23,45]])))
        d = mydict(args, w({'a':33, 'b':44}))
        assert self.space.eq_w(d, wd(deepwrap([['a',33],['b',44],[23,45]])))
        d = mydict(w_kwds=w({'a':33, 'b':44}))
        assert self.space.eq_w(d, wd(deepwrap([['a',33],['b',44]])))
        self.space.raises_w(space.w_TypeError, mydict, w((23,)))
        self.space.raises_w(space.w_ValueError, mydict, w(([[1,2,3]],)))

    def test_dict_pop(self):
        space = self.space
        w = space.wrap
        wd = space.newdict
        def mydict(w_args=w(()), w_kwds=w({})):
            return space.call(space.w_dict, w_args, w_kwds)
        d = mydict(w_kwds=w({"1":2, "3":4}))
        dd = mydict(w_kwds=w({"1":2, "3":4})) # means d.copy()
        pop = space.getattr(dd, w("pop"))
        result = space.call_function(pop, w("1"))
        assert self.space.eq_w(result, w(2))
        assert self.space.eq_w(space.len(dd), w(1))

        dd = mydict(w_kwds=w({"1":2, "3":4})) # means d.copy()
        pop = space.getattr(dd, w("pop"))
        result = space.call_function(pop, w("1"), w(44))
        assert self.space.eq_w(result, w(2))
        assert self.space.eq_w(space.len(dd), w(1))
        result = space.call_function(pop, w("1"), w(44))
        assert self.space.eq_w(result, w(44))
        assert self.space.eq_w(space.len(dd), w(1))

        self.space.raises_w(space.w_KeyError, space.call_function, pop, w(33))

    def test_get(self):
        space = self.space
        w = space.wrap
        def mydict(w_args=w(()), w_kwds=w({})):
            return space.call(space.w_dict, w_args, w_kwds)
        d = mydict(w_kwds=w({"1":2, "3":4}))
        get = space.getattr(d, w("get"))
        assert self.space.eq_w(space.call_function(get, w("1")), w(2))
        assert self.space.eq_w(space.call_function(get, w("1"), w(44)), w(2))
        assert self.space.eq_w(space.call_function(get, w("33")), w(None))
        assert self.space.eq_w(space.call_function(get, w("33"), w(44)), w(44))



class AppTest_DictObject:

    def test_equality(self):
        d = {1:2} 
        f = {1:2} 
        assert d == f
        assert d != {1:3}

    def test_clear(self):
        d = {1:2, 3:4}
        d.clear()
        assert len(d) == 0
                         
    def test_copy(self):
        d = {1:2, 3:4}
        dd = d.copy()
        assert d == dd
        assert not d is dd
        
    def tooslow_test_get(self):
        d = {1:2, 3:4}
        assert d.get(1) == 2
        assert d.get(1,44) == 2
        assert d.get(33) == None
        assert d.get(33,44) == 44

    def tooslow_test_pop(self):
        d = {1:2, 3:4}
        dd = d.copy()
        result = dd.pop(1)
        assert result == 2
        assert len(dd) == 1
        dd = d.copy()
        result = dd.pop(1, 44)
        assert result == 2
        assert len(dd) == 1
        result = dd.pop(1, 44)
        assert result == 44
        assert len(dd) == 1
        raises(KeyError, dd.pop, 33)
    
    def test_has_key(self):
        d = {1:2, 3:4}
        assert d.has_key(1)
        assert not d.has_key(33)
    
    def test_items(self):
        d = {1:2, 3:4}
        its = d.items()
        its.sort()
        assert its == [(1,2),(3,4)]
    
    def test_iteritems(self):
        d = {1:2, 3:4}
        dd = d.copy()
        for k, v in d.iteritems():
            assert v == dd[k]
            del dd[k]
        assert not dd
    
    def test_iterkeys(self):
        d = {1:2, 3:4}
        dd = d.copy()
        for k in d.iterkeys():
            del dd[k]
        assert not dd
    
    def test_itervalues(self):
        d = {1:2, 3:4}
        values = []
        for k in d.itervalues():
            values.append(k)
        assert values == d.values()
    
    def test_keys(self):
        d = {1:2, 3:4}
        kys = d.keys()
        kys.sort()
        assert kys == [1,3]
    
    def test_popitem(self):
        d = {1:2, 3:4}
        it = d.popitem()
        assert len(d) == 1
        assert it==(1,2) or it==(3,4)
        it1 = d.popitem()
        assert len(d) == 0
        assert (it!=it1) and (it1==(1,2) or it1==(3,4))
    
    def test_setdefault(self):
        d = {1:2, 3:4}
        dd = d.copy()
        x = dd.setdefault(1, 99)
        assert d == dd
        assert x == 2
        x = dd.setdefault(33, 99)
        d[33] = 99
        assert d == dd
        assert x == 99
    
    def test_update(self):
        d = {1:2, 3:4}
        dd = d.copy()
        d.update({})
        assert d == dd
        d.update({3:5, 6:7})
        assert d == {1:2, 3:5, 6:7}
    
    def test_values(self):
        d = {1:2, 3:4}
        vals = d.values()
        vals.sort()
        assert vals == [2,4]

    def test_eq(self):
        d1 = {1:2, 3:4}
        d2 = {1:2, 3:4}
        d3 = {1:2}
        bool = d1 == d2
        assert bool == True
        bool = d1 == d3
        assert bool == False
        bool = d1 != d2
        assert bool == False
        bool = d1 != d3
        assert bool == True

    def test_lt(self):
        d1 = {1:2, 3:4}
        d2 = {1:2, 3:4}
        d3 = {1:2, 3:5}
        d4 = {1:2}
        bool = d1 < d2
        assert bool == False
        bool = d1 < d3
        assert bool == True
        bool = d1 < d4
        assert bool == False

    def test_str_repr(self):
        assert '{}' == str({})
        assert '{1: 2}' == str({1: 2})
        assert "{'ba': 'bo'}" == str({'ba': 'bo'})
        # NOTE: the string repr depends on hash values of 1 and 'ba'!!!
        ok_reprs = ["{1: 2, 'ba': 'bo'}", "{'ba': 'bo', 1: 2}"]
        assert str({1: 2, 'ba': 'bo'}) in ok_reprs
        assert '{}' == repr({})
        assert '{1: 2}' == repr({1: 2})
        assert "{'ba': 'bo'}" == repr({'ba': 'bo'})
        assert str({1: 2, 'ba': 'bo'}) in ok_reprs
        
    def test_new(self):
        d = dict()
        assert d == {}
        args = [['a',2], [23,45]]
        d = dict(args)
        assert d == {'a':2, 23:45}
        d = dict(args, a=33, b=44)
        assert d == {'a':33, 'b':44, 23:45}
        d = dict(a=33, b=44)
        assert d == {'a':33, 'b':44}
        d = dict({'a':33, 'b':44})
        assert d == {'a':33, 'b':44}        
        try: d = dict(23)
        except (TypeError, ValueError): pass
        else: self.fail("dict(23) should raise!")
        try: d = dict([[1,2,3]])
        except (TypeError, ValueError): pass
        else: self.fail("dict([[1,2,3]]) should raise!")

    def test_fromkeys(self):
        assert {}.fromkeys([1, 2], 1) == {1: 1, 2: 1}
        assert {}.fromkeys([1, 2]) == {1: None, 2: None}
        assert {}.fromkeys([]) == {}
        assert {1: 0, 2: 0, 3: 0}.fromkeys([1, '1'], 'j') == (
                          {1: 'j', '1': 'j'})

# the minimal 'space' needed to use a W_DictObject
class FakeSpace:
    def hash(self, obj):
        return hash(obj)
    def unwrap(self, x):
        return x
    def is_true(self, x):
        return x
    def is_(self, x, y):
        return x is y
    def eq(self, x, y):
        return x == y

from pypy.objspace.std.dictobject import getitem__Dict_ANY, setitem__Dict_ANY_ANY

class TestDictImplementation:
    
    def setup_method(self,method):
        self.space = FakeSpace()

    def test_stressdict(self):
        from random import randint
        d = W_DictObject(self.space, [])
        N = 10000
        pydict = {}
        for i in range(N):
            x = randint(-N, N)
            setitem__Dict_ANY_ANY(self.space, d, x, i)
            pydict[x] = i
        for x in pydict:
            assert pydict[x] == getitem__Dict_ANY(self.space, d, x)
