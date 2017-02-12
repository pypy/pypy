import sys
import py

from pypy.objspace.std.dictmultiobject import (W_DictMultiObject,
    W_DictObject, BytesDictStrategy, ObjectDictStrategy)


class TestW_DictObject(object):
    def test_empty(self):
        d = self.space.newdict()
        assert not self.space.is_true(d)
        assert type(d.get_strategy()) is not ObjectDictStrategy

    def test_nonempty(self):
        space = self.space
        wNone = space.w_None
        d = self.space.newdict()
        d.initialize_content([(wNone, wNone)])
        assert space.is_true(d)
        i = space.getitem(d, wNone)
        equal = space.eq(i, wNone)
        assert space.is_true(equal)

    def test_setitem(self):
        space = self.space
        wk1 = space.wrap('key')
        wone = space.wrap(1)
        d = self.space.newdict()
        d.initialize_content([(space.wrap('zero'),space.wrap(0))])
        space.setitem(d,wk1,wone)
        wback = space.getitem(d,wk1)
        assert self.space.eq_w(wback,wone)

    def test_delitem(self):
        space = self.space
        wk1 = space.wrap('key')
        d = self.space.newdict()
        d.initialize_content( [(space.wrap('zero'),space.wrap(0)),
                               (space.wrap('one'),space.wrap(1)),
                               (space.wrap('two'),space.wrap(2))])
        space.delitem(d,space.wrap('one'))
        assert self.space.eq_w(space.getitem(d,space.wrap('zero')),space.wrap(0))
        assert self.space.eq_w(space.getitem(d,space.wrap('two')),space.wrap(2))
        self.space.raises_w(self.space.w_KeyError,
                            space.getitem,d,space.wrap('one'))

    def test_wrap_dict(self):
        assert isinstance(self.space.wrap({}), W_DictMultiObject)


    def test_dict_compare(self):
        w = self.space.wrap
        w0, w1, w2, w3 = map(w, range(4))
        def wd(items):
            d = self.space.newdict()
            d.initialize_content(items)
            return d
        wd1 = wd([(w0, w1), (w2, w3)])
        wd2 = wd([(w2, w3), (w0, w1)])
        assert self.space.eq_w(wd1, wd2)
        wd3 = wd([(w2, w2), (w0, w1)])
        assert not self.space.eq_w(wd1, wd3)
        wd4 = wd([(w3, w3), (w0, w1)])
        assert not self.space.eq_w(wd1, wd4)
        wd5 = wd([(w3, w3)])
        assert not self.space.eq_w(wd1, wd4)

    def test_dict_call(self):
        space = self.space
        w = space.wrap
        def wd(items):
            d = space.newdict()
            d.initialize_content(items)
            return d
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

    def test_fromkeys_fastpath(self):
        space = self.space
        w = space.wrap

        w_l = space.newlist([w("a"),w("b")])
        w_l.getitems = None
        w_d = space.call_method(space.w_dict, "fromkeys", w_l)

        assert space.eq_w(w_d.getitem_str("a"), space.w_None)
        assert space.eq_w(w_d.getitem_str("b"), space.w_None)

    def test_listview_bytes_dict(self):
        w = self.space.wrap
        wb = self.space.newbytes
        w_d = self.space.newdict()
        w_d.initialize_content([(wb("a"), w(1)), (wb("b"), w(2))])
        assert self.space.listview_bytes(w_d) == ["a", "b"]

    def test_listview_unicode_dict(self):
        w = self.space.wrap
        w_d = self.space.newdict()
        w_d.initialize_content([(w(u"a"), w(1)), (w(u"b"), w(2))])
        assert self.space.listview_unicode(w_d) == [u"a", u"b"]

    def test_listview_int_dict(self):
        w = self.space.wrap
        w_d = self.space.newdict()
        w_d.initialize_content([(w(1), w("a")), (w(2), w("b"))])
        assert self.space.listview_int(w_d) == [1, 2]

    def test_keys_on_string_unicode_int_dict(self, monkeypatch):
        w = self.space.wrap
        wb = self.space.newbytes

        w_d = self.space.newdict()
        w_d.initialize_content([(w(1), wb("a")), (w(2), wb("b"))])
        w_l = self.space.call_method(w_d, "keys")
        assert sorted(self.space.listview_int(w_l)) == [1,2]
        
        # make sure that .keys() calls newlist_bytes for string dicts
        def not_allowed(*args):
            assert False, 'should not be called'
        monkeypatch.setattr(self.space, 'newlist', not_allowed)
        #
        w_d = self.space.newdict()
        w_d.initialize_content([(wb("a"), w(1)), (wb("b"), w(6))])
        w_l = self.space.call_method(w_d, "keys")
        assert sorted(self.space.listview_bytes(w_l)) == ["a", "b"]

        # XXX: it would be nice if the test passed without monkeypatch.undo(),
        # but we need space.newlist_unicode for it
        monkeypatch.undo() 
        w_d = self.space.newdict()
        w_d.initialize_content([(w(u"a"), w(1)), (w(u"b"), w(6))])
        w_l = self.space.call_method(w_d, "keys")
        assert sorted(self.space.listview_unicode(w_l)) == [u"a", u"b"]

class AppTest_DictObject:
    def setup_class(cls):
        cls.w_on_pypy = cls.space.wrap("__pypy__" in sys.builtin_module_names)

    def test_equality(self):
        d = {1: 2}
        f = {1: 2}
        assert d == f
        assert d != {1: 3}

    def test_clear(self):
        d = {1: 2, 3: 4}
        d.clear()
        assert len(d) == 0

    def test_copy(self):
        d = {1: 2, 3: 4}
        dd = d.copy()
        assert d == dd
        assert not d is dd

    def test_get(self):
        d = {1: 2, 3: 4}
        assert d.get(1) == 2
        assert d.get(1, 44) == 2
        assert d.get(33) == None
        assert d.get(33, 44) == 44

    def test_pop(self):
        d = {1: 2, 3: 4}
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
        d = {1: 2, 3: 4}
        assert d.has_key(1)
        assert not d.has_key(33)

    def test_items(self):
        d = {1: 2, 3: 4}
        its = d.items()
        its.sort()
        assert its == [(1, 2), (3, 4)]

    def test_iteritems(self):
        d = {1: 2, 3: 4}
        dd = d.copy()
        for k, v in d.iteritems():
            assert v == dd[k]
            del dd[k]
        assert not dd

    def test_iterkeys(self):
        d = {1: 2, 3: 4}
        dd = d.copy()
        for k in d.iterkeys():
            del dd[k]
        assert not dd

    def test_itervalues(self):
        d = {1: 2, 3: 4}
        values = []
        for k in d.itervalues():
            values.append(k)
        assert values == d.values()

    def test_reversed_dict(self):
        import __pypy__
        for d in [{}, {1: 2, 3: 4, 5: 6}, {"a": 5, "b": 2, "c": 6}]:
            assert list(__pypy__.reversed_dict(d)) == d.keys()[::-1]
        raises(TypeError, __pypy__.reversed_dict, 42)

    def test_reversed_dict_runtimeerror(self):
        import __pypy__
        d = {1: 2, 3: 4, 5: 6}
        it = __pypy__.reversed_dict(d)
        key = it.next()
        assert key in [1, 3, 5]   # on CPython, dicts are not ordered
        del d[key]
        raises(RuntimeError, it.next)

    def test_dict_popitem_first(self):
        import __pypy__
        d = {"a": 5}
        assert __pypy__.dict_popitem_first(d) == ("a", 5)
        raises(KeyError, __pypy__.dict_popitem_first, d)

        def kwdict(**k):
            return k
        d = kwdict(a=55)
        assert __pypy__.dict_popitem_first(d) == ("a", 55)
        raises(KeyError, __pypy__.dict_popitem_first, d)

    def test_delitem_if_value_is(self):
        import __pypy__
        class X:
            pass
        x2 = X()
        x3 = X()
        d = {2: x2, 3: x3}
        __pypy__.delitem_if_value_is(d, 2, x3)
        assert d == {2: x2, 3: x3}
        __pypy__.delitem_if_value_is(d, 2, x2)
        assert d == {3: x3}
        __pypy__.delitem_if_value_is(d, 2, x3)
        assert d == {3: x3}

    def test_move_to_end(self):
        import __pypy__
        raises(KeyError, __pypy__.move_to_end, {}, 'foo')
        raises(KeyError, __pypy__.move_to_end, {}, 'foo', last=True)
        raises(KeyError, __pypy__.move_to_end, {}, 'foo', last=False)
        def kwdict(**k):
            return k
        for last in [False, True]:
            for d, key in [({1: 2, 3: 4, 5: 6}, 3),
                           ({"a": 5, "b": 2, "c": 6}, "b"),
                           (kwdict(d=7, e=8, f=9), "e")]:
                other_keys = [k for k in d if k != key]
                __pypy__.move_to_end(d, key, last=last)
                if not self.on_pypy:
                    # when running tests on CPython, the underlying
                    # dicts are not ordered.  We don't get here if
                    # we're running tests on PyPy or with -A.
                    assert set(d.keys()) == set(other_keys + [key])
                elif last:
                    assert list(d) == other_keys + [key]
                else:
                    assert list(d) == [key] + other_keys
                raises(KeyError, __pypy__.move_to_end, d, key * 3, last=last)

    def test_keys(self):
        d = {1: 2, 3: 4}
        kys = d.keys()
        kys.sort()
        assert kys == [1, 3]

    def test_popitem(self):
        d = {1: 2, 3: 4}
        it = d.popitem()
        assert len(d) == 1
        assert it == (1, 2) or it == (3, 4)
        it1 = d.popitem()
        assert len(d) == 0
        assert (it != it1) and (it1 == (1, 2) or it1 == (3, 4))
        raises(KeyError, d.popitem)

    def test_popitem_2(self):
        class A(object):
            pass
        d = A().__dict__
        d['x'] = 5
        it1 = d.popitem()
        assert it1 == ('x', 5)
        raises(KeyError, d.popitem)

    def test_popitem3(self):
        #object
        d = {"a": 1, 2: 2, "c": 3}
        l = []
        while True:
            try:
                l.append(d.popitem())
            except KeyError:
                break;
        assert ("a", 1) in l
        assert (2, 2) in l
        assert ("c", 3) in l

        #string
        d = {"a": 1, "b":2, "c":3}
        l = []
        while True:
            try:
                l.append(d.popitem())
            except KeyError:
                break;
        assert ("a", 1) in l
        assert ("b", 2) in l
        assert ("c", 3) in l

    def test_setdefault(self):
        d = {1: 2, 3: 4}
        dd = d.copy()
        x = dd.setdefault(1, 99)
        assert d == dd
        assert x == 2
        x = dd.setdefault(33, 99)
        d[33] = 99
        assert d == dd
        assert x == 99

    def test_setdefault_fast(self):
        class Key(object):
            calls = 0
            def __hash__(self):
                self.calls += 1
                return object.__hash__(self)

        k = Key()
        d = {}
        d.setdefault(k, [])
        if self.on_pypy:
            assert k.calls == 1

        d.setdefault(k, 1)
        if self.on_pypy:
            assert k.calls == 2

        k = Key()
        d.setdefault(k, 42)
        if self.on_pypy:
            assert k.calls == 1

    def test_update(self):
        d = {1: 2, 3: 4}
        dd = d.copy()
        d.update({})
        assert d == dd
        d.update({3: 5, 6: 7})
        assert d == {1: 2, 3: 5, 6: 7}

    def test_update_iterable(self):
        d = {}
        d.update((('a',1),))
        assert d == {'a': 1}
        d.update([('a',2), ('c',3)])
        assert d == {'a': 2, 'c': 3}

    def test_update_nop(self):
        d = {}
        d.update()
        assert d == {}

    def test_update_kwargs(self):
        d = {}
        d.update(foo='bar', baz=1)
        assert d == {'foo': 'bar', 'baz': 1}

    def test_update_dict_and_kwargs(self):
        d = {}
        d.update({'foo': 'bar'}, baz=1)
        assert d == {'foo': 'bar', 'baz': 1}

    def test_update_keys_method(self):
        class Foo(object):
            def keys(self):
                return [4, 1]
            def __getitem__(self, key):
                return key * 10
        d = {}
        d.update(Foo())
        assert d == {1: 10, 4: 40}

    def test_values(self):
        d = {1: 2, 3: 4}
        vals = d.values()
        vals.sort()
        assert vals == [2,4]

    def test_eq(self):
        d1 = {1: 2, 3: 4}
        d2 = {1: 2, 3: 4}
        d3 = {1: 2}
        bool = d1 == d2
        assert bool == True
        bool = d1 == d3
        assert bool == False
        bool = d1 != d2
        assert bool == False
        bool = d1 != d3
        assert bool == True

    def test_lt(self):
        d1 = {1: 2, 3: 4}
        d2 = {1: 2, 3: 4}
        d3 = {1: 2, 3: 5}
        d4 = {1: 2}
        bool = d1 < d2
        assert bool == False
        bool = d1 < d3
        assert bool == True
        bool = d1 < d4
        assert bool == False

    def test_lt2(self):
        assert {'a': 1 } < { 'a': 2 }
        assert not {'a': 1 } > { 'a': 2 }
        assert not {'a': 1, 'b': 0 } > { 'a': 2, 'b': 0 }
        assert {'a': 1, 'b': 0 } < { 'a': 2, 'b': 0 }
        assert {'a': 1, 'b': 0 } < { 'a': 1, 'b': 2 }
        assert not {'a': 1, 'b': 0 } < { 'a': 1, 'b': -2 }
        assert {'a': 1 } < { 'b': 1}
        assert {'a': 1, 'x': 2 } < { 'b': 1, 'x': 2}

    def test_other_rich_cmp(self):
        d1 = {1: 2, 3: 4}
        d2 = {1: 2, 3: 4}
        d3 = {1: 2, 3: 5}
        d4 = {1: 2}

        assert d1 <= d2
        assert d1 <= d3
        assert not d1 <= d4

        assert not d1 > d2
        assert not d1 > d3
        assert d1 > d4

        assert d1 >= d2
        assert not d1 >= d3
        assert d1 >= d4

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

        # Now test self-containing dict
        d = {}
        d[0] = d
        assert str(d) == '{0: {...}}'

        # Mutating while repr'ing
        class Machiavelli(object):
            def __repr__(self):
                d.clear()
                return "42"
        d = {Machiavelli(): True}
        str(d)
        assert d == {}

    def test_new(self):
        d = dict()
        assert d == {}
        args = [['a', 2], [23, 45]]
        d = dict(args)
        assert d == {'a': 2, 23: 45}
        d = dict(args, a=33, b=44)
        assert d == {'a': 33, 'b': 44, 23: 45}
        d = dict(a=33, b=44)
        assert d == {'a': 33, 'b': 44}
        d = dict({'a': 33, 'b': 44})
        assert d == {'a': 33, 'b': 44}
        raises((TypeError, ValueError), dict, 23)
        raises((TypeError, ValueError), dict, [[1, 2, 3]])

    def test_fromkeys(self):
        assert {}.fromkeys([1, 2], 1) == {1: 1, 2: 1}
        assert {}.fromkeys([1, 2]) == {1: None, 2: None}
        assert {}.fromkeys([]) == {}
        assert {1: 0, 2: 0, 3: 0}.fromkeys([1, '1'], 'j') == (
                          {1: 'j', '1': 'j'})
        class D(dict):
            def __new__(cls):
                return E()
        class E(dict):
            pass
        assert isinstance(D.fromkeys([1, 2]), E)
        assert dict.fromkeys({"a": 2, "b": 3}) == {"a": None, "b": None}
        assert dict.fromkeys({"a": 2, 1: 3}) == {"a": None, 1: None}

    def test_str_uses_repr(self):
        class D(dict):
            def __repr__(self):
                return 'hi'
        assert repr(D()) == 'hi'
        assert str(D()) == 'hi'

    def test_overridden_setitem(self):
        class D(dict):
            def __setitem__(self, key, value):
                dict.__setitem__(self, key, 42)
        d = D([('x', 'foo')], y = 'bar')
        assert d['x'] == 'foo'
        assert d['y'] == 'bar'

        d.setdefault('z', 'baz')
        assert d['z'] == 'baz'

        d['foo'] = 'bar'
        assert d['foo'] == 42

        d.update({'w': 'foobar'})
        assert d['w'] == 'foobar'

        d = d.copy()
        assert d['x'] == 'foo'

        d3 = D.fromkeys(['x', 'y'], 'foo')
        assert d3['x'] == 42
        assert d3['y'] == 42

    def test_overridden_setitem_customkey(self):
        class D(dict):
            def __setitem__(self, key, value):
                dict.__setitem__(self, key, 42)
        class Foo(object):
            pass

        d = D()
        key = Foo()
        d[key] = 'bar'
        assert d[key] == 42

    def test_repr_with_overridden_items(self):
        class D(dict):
            def items(self):
                return []

        d = D([("foo", "foobar")])
        assert repr(d) == "{'foo': 'foobar'}"

    def test_popitem_with_overridden_delitem(self):
        class D(dict):
            def __delitem__(self, key):
                assert False
        d = D()
        d['a'] = 42
        item = d.popitem()
        assert item == ('a', 42)

    def test_dict_update_overridden_getitem(self):
        class D(dict):
            def __getitem__(self, key):
                return 42
        d1 = {}
        d2 = D(a='foo')
        d1.update(d2)
        assert d1['a'] == 'foo'
        # a bit of an obscure case: now (from r78295) we get the same result
        # as CPython does

    def test_index_keyerror_unpacking(self):
        d = {}
        for v1 in ['Q', (1,)]:
            try:
                d[v1]
            except KeyError as e:
                v2 = e.args[0]
                assert v1 == v2
            else:
                assert False, 'Expected KeyError'

    def test_del_keyerror_unpacking(self):
        d = {}
        for v1 in ['Q', (1,)]:
            try:
                del d[v1]
            except KeyError as e:
                v2 = e.args[0]
                assert v1 == v2
            else:
                assert False, 'Expected KeyError'

    def test_pop_keyerror_unpacking(self):
        d = {}
        for v1 in ['Q', (1,)]:
            try:
                d.pop(v1)
            except KeyError as e:
                v2 = e.args[0]
                assert v1 == v2
            else:
                assert False, 'Expected KeyError'

    def test_no_len_on_dict_iter(self):
        iterable = {1: 2, 3: 4}
        raises(TypeError, len, iter(iterable))
        iterable = {"1": 2, "3": 4}
        raises(TypeError, len, iter(iterable))
        iterable = {}
        raises(TypeError, len, iter(iterable))

    def test_missing(self):
        class X(dict):
            def __missing__(self, x):
                assert x == 'hi'
                return 42
        assert X()['hi'] == 42

    def test_missing_more(self):
        def missing(self, x):
            assert x == 'hi'
            return 42
        class SpecialDescr(object):
            def __init__(self, impl):
                self.impl = impl
            def __get__(self, obj, owner):
                return self.impl.__get__(obj, owner)
        class X(dict):
            __missing__ = SpecialDescr(missing)
        assert X()['hi'] == 42

    def test_empty_dict(self):
        d = {}
        raises(KeyError, d.popitem)
        assert d.items() == []
        assert d.values() == []
        assert d.keys() == []

    def test_cmp_with_noncmp(self):
        assert not {} > object()

class AppTest_DictMultiObject(AppTest_DictObject):

    def test_emptydict_unhashable(self):
        raises(TypeError, "{}[['x']]")
        raises(TypeError, "del {}[['x']]")

    def test_string_subclass_via_setattr(self):
        class A(object):
            pass
        class S(str):
            def __hash__(self):
                return 123
        a = A()
        s = S("abc")
        setattr(a, s, 42)
        key = a.__dict__.keys()[0]
        assert key == s
        assert key is not s
        assert type(key) is str
        assert getattr(a, s) == 42

    def test_setattr_string_identify(self):
        class StrHolder(object):
            pass
        holder = StrHolder()
        class A(object):
            def __setattr__(self, attr, value):
                holder.seen = attr

        a = A()
        s = "abc"
        setattr(a, s, 123)
        assert holder.seen is s

    def test_internal_delitem(self):
        class K:
            def __hash__(self):
                return 42
            def __eq__(self, other):
                if is_equal[0]:
                    is_equal[0] -= 1
                    return True
                return False
        is_equal = [0]
        k1 = K()
        k2 = K()
        d = {k1: 1, k2: 2}
        k3 = K()
        is_equal = [1]
        try:
            x = d.pop(k3)
        except RuntimeError:
            # This used to give a Fatal RPython error: KeyError.
            # Now at least it should raise an app-level RuntimeError,
            # or just work.
            assert len(d) == 2
        else:
            assert (x == 1 or x == 2) and len(d) == 1


class AppTestDictViews:
    def test_dictview(self):
        d = {1: 2, 3: 4}
        assert len(d.viewkeys()) == 2
        assert len(d.viewitems()) == 2
        assert len(d.viewvalues()) == 2

    def test_constructors_not_callable(self):
        kt = type({}.viewkeys())
        raises(TypeError, kt, {})
        raises(TypeError, kt)
        it = type({}.viewitems())
        raises(TypeError, it, {})
        raises(TypeError, it)
        vt = type({}.viewvalues())
        raises(TypeError, vt, {})
        raises(TypeError, vt)

    def test_dict_keys(self):
        d = {1: 10, "a": "ABC"}
        keys = d.viewkeys()
        assert len(keys) == 2
        assert set(keys) == set([1, "a"])
        assert keys == set([1, "a"])
        assert keys == frozenset([1, "a"])
        assert keys != set([1, "a", "b"])
        assert keys != set([1, "b"])
        assert keys != set([1])
        assert keys != 42
        assert 1 in keys
        assert "a" in keys
        assert 10 not in keys
        assert "Z" not in keys
        assert d.viewkeys() == d.viewkeys()
        e = {1: 11, "a": "def"}
        assert d.viewkeys() == e.viewkeys()
        del e["a"]
        assert d.viewkeys() != e.viewkeys()
        assert not d.viewkeys() == 42

    def test_dict_items(self):
        d = {1: 10, "a": "ABC"}
        items = d.viewitems()
        assert len(items) == 2
        assert set(items) == set([(1, 10), ("a", "ABC")])
        assert items == set([(1, 10), ("a", "ABC")])
        assert items == frozenset([(1, 10), ("a", "ABC")])
        assert items != set([(1, 10), ("a", "ABC"), "junk"])
        assert items != set([(1, 10), ("a", "def")])
        assert items != set([(1, 10)])
        assert items != 42
        assert (1, 10) in items
        assert ("a", "ABC") in items
        assert (1, 11) not in items
        assert 1 not in items
        assert () not in items
        assert (1,) not in items
        assert (1, 2, 3) not in items
        assert d.viewitems() == d.viewitems()
        e = d.copy()
        assert d.viewitems() == e.viewitems()
        e["a"] = "def"
        assert d.viewitems() != e.viewitems()
        assert not d.viewitems() == 42

    def test_dict_mixed_keys_items(self):
        d = {(1, 1): 11, (2, 2): 22}
        e = {1: 1, 2: 2}
        assert d.viewkeys() == e.viewitems()
        assert d.viewitems() != e.viewkeys()

    def test_dict_values(self):
        d = {1: 10, "a": "ABC"}
        values = d.viewvalues()
        assert set(values) == set([10, "ABC"])
        assert len(values) == 2
        assert not values == 42

    def test_dict_repr(self):
        d = {1: 10, "a": "ABC"}
        assert isinstance(repr(d), str)
        r = repr(d.viewitems())
        assert isinstance(r, str)
        assert (r == "dict_items([('a', 'ABC'), (1, 10)])" or
                r == "dict_items([(1, 10), ('a', 'ABC')])")
        r = repr(d.viewkeys())
        assert isinstance(r, str)
        assert (r == "dict_keys(['a', 1])" or
                r == "dict_keys([1, 'a'])")
        r = repr(d.viewvalues())
        assert isinstance(r, str)
        assert (r == "dict_values(['ABC', 10])" or
                r == "dict_values([10, 'ABC'])")

    def test_keys_set_operations(self):
        d1 = {'a': 1, 'b': 2}
        d2 = {'b': 3, 'c': 2}
        d3 = {'d': 4, 'e': 5}
        assert d1.viewkeys() & d1.viewkeys() == set('ab')
        assert d1.viewkeys() & d2.viewkeys() == set('b')
        assert d1.viewkeys() & d3.viewkeys() == set()
        assert d1.viewkeys() & set(d1.viewkeys()) == set('ab')
        assert d1.viewkeys() & set(d2.viewkeys()) == set('b')
        assert d1.viewkeys() & set(d3.viewkeys()) == set()

        assert d1.viewkeys() | d1.viewkeys() == set('ab')
        assert d1.viewkeys() | d2.viewkeys() == set('abc')
        assert d1.viewkeys() | d3.viewkeys() == set('abde')
        assert d1.viewkeys() | set(d1.viewkeys()) == set('ab')
        assert d1.viewkeys() | set(d2.viewkeys()) == set('abc')
        assert d1.viewkeys() | set(d3.viewkeys()) == set('abde')

        assert d1.viewkeys() ^ d1.viewkeys() == set()
        assert d1.viewkeys() ^ d2.viewkeys() == set('ac')
        assert d1.viewkeys() ^ d3.viewkeys() == set('abde')
        assert d1.viewkeys() ^ set(d1.viewkeys()) == set()
        assert d1.viewkeys() ^ set(d2.viewkeys()) == set('ac')
        assert d1.viewkeys() ^ set(d3.viewkeys()) == set('abde')

        assert d1.viewkeys() - d1.viewkeys() == set()
        assert d1.viewkeys() - d2.viewkeys() == set('a')
        assert d1.viewkeys() - d3.viewkeys() == set('ab')
        assert d1.viewkeys() - set(d1.viewkeys()) == set()
        assert d1.viewkeys() - set(d2.viewkeys()) == set('a')
        assert d1.viewkeys() - set(d3.viewkeys()) == set('ab')

    def test_items_set_operations(self):
        d1 = {'a': 1, 'b': 2}
        d2 = {'a': 2, 'b': 2}
        d3 = {'d': 4, 'e': 5}
        assert d1.viewitems() & d1.viewitems() == set([('a', 1), ('b', 2)])
        assert d1.viewitems() & d2.viewitems() == set([('b', 2)])
        assert d1.viewitems() & d3.viewitems() == set()
        assert d1.viewitems() & set(d1.viewitems()) == set([('a', 1), ('b', 2)])
        assert d1.viewitems() & set(d2.viewitems()) == set([('b', 2)])
        assert d1.viewitems() & set(d3.viewitems()) == set()

        assert d1.viewitems() | d1.viewitems() == set([('a', 1), ('b', 2)])
        assert (d1.viewitems() | d2.viewitems() ==
                set([('a', 1), ('a', 2), ('b', 2)]))
        assert (d1.viewitems() | d3.viewitems() ==
                set([('a', 1), ('b', 2), ('d', 4), ('e', 5)]))
        assert (d1.viewitems() | set(d1.viewitems()) ==
                set([('a', 1), ('b', 2)]))
        assert (d1.viewitems() | set(d2.viewitems()) ==
                set([('a', 1), ('a', 2), ('b', 2)]))
        assert (d1.viewitems() | set(d3.viewitems()) ==
                set([('a', 1), ('b', 2), ('d', 4), ('e', 5)]))

        assert d1.viewitems() ^ d1.viewitems() == set()
        assert d1.viewitems() ^ d2.viewitems() == set([('a', 1), ('a', 2)])
        assert (d1.viewitems() ^ d3.viewitems() ==
                set([('a', 1), ('b', 2), ('d', 4), ('e', 5)]))

        assert d1.viewitems() - d1.viewitems() == set()
        assert d1.viewitems() - d2.viewitems() == set([('a', 1)])
        assert d1.viewitems() - d3.viewitems() == set([('a', 1), ('b', 2)])

    def test_keys_set_operations_any_type(self):
        d = {1: u'a', 2: u'b', 3: u'c'}
        assert d.viewkeys() & set([1]) == set([1])
        assert d.viewkeys() & {1: u'foo'} == set([1])
        assert d.viewkeys() & [1, 2] == set([1, 2])
        #
        assert set([1]) & d.viewkeys() == set([1])
        assert {1: u'foo'} & d.viewkeys() == set([1])
        assert [1, 2] & d.viewkeys() == set([1, 2])
        #
        assert d.viewkeys() - set([1]) == set([2, 3])
        assert set([1, 4]) - d.viewkeys() == set([4])
        #
        assert d.viewkeys() == set([1, 2, 3])
        # XXX: The following 4 commented out are CPython 2.7 bugs
        #assert set([1, 2, 3]) == d.viewkeys()
        assert d.viewkeys() == frozenset(set([1, 2, 3]))
        #assert frozenset(set([1, 2, 3])) == d.viewkeys()
        assert not d.viewkeys() != set([1, 2, 3])
        #assert not set([1, 2, 3]) != d.viewkeys()
        assert not d.viewkeys() != frozenset(set([1, 2, 3]))
        #assert not frozenset(set([1, 2, 3])) != d.viewkeys()

    def test_items_set_operations_any_type(self):
        d = {1: u'a', 2: u'b', 3: u'c'}
        assert d.viewitems() & set([(1, u'a')]) == set([(1, u'a')])
        assert d.viewitems() & {(1, u'a'): u'foo'} == set([(1, u'a')])
        assert d.viewitems() & [(1, u'a'), (2, u'b')] == set([(1, u'a'), (2, u'b')])
        #
        assert set([(1, u'a')]) & d.viewitems() == set([(1, u'a')])
        assert {(1, u'a'): u'foo'} & d.viewitems() == set([(1, u'a')])
        assert [(1, u'a'), (2, u'b')] & d.viewitems() == set([(1, u'a'), (2, u'b')])
        #
        assert d.viewitems() - set([(1, u'a')]) == set([(2, u'b'), (3, u'c')])
        assert set([(1, u'a'), 4]) - d.viewitems() == set([4])
        #
        assert d.viewitems() == set([(1, u'a'), (2, u'b'), (3, u'c')])
        # XXX: The following 4 commented out are CPython 2.7 bugs
        #assert set([(1, u'a'), (2, u'b'), (3, u'c')]) == d.viewitems()
        assert d.viewitems() == frozenset(set([(1, u'a'), (2, u'b'), (3, u'c')]))
        #assert frozenset(set([(1, u'a'), (2, u'b'), (3, u'c')])) == d.viewitems()
        assert not d.viewitems() != set([(1, u'a'), (2, u'b'), (3, u'c')])
        #assert not set([(1, u'a'), (2, u'b'), (3, u'c')]) != d.viewitems()
        assert not d.viewitems() != frozenset(set([(1, u'a'), (2, u'b'), (3, u'c')]))
        #assert not frozenset(set([(1, u'a'), (2, u'b'), (3, u'c')])) != d.viewitems()

    def test_dictviewset_unhashable_values(self):
        class C:
            def __eq__(self, other):
                return True
        d = {1: C()}
        assert d.viewitems() <= d.viewitems()

    def test_compare_keys_and_items(self):
        d1 = {1: 2}
        d2 = {(1, 2): 'foo'}
        assert d1.viewitems() == d2.viewkeys()

    def test_keys_items_contained(self):
        def helper(fn):
            empty = fn(dict())
            empty2 = fn(dict())
            smaller = fn({1:1, 2:2})
            larger = fn({1:1, 2:2, 3:3})
            larger2 = fn({1:1, 2:2, 3:3})
            larger3 = fn({4:1, 2:2, 3:3})

            assert smaller <  larger
            assert smaller <= larger
            assert larger >  smaller
            assert larger >= smaller

            assert not smaller >= larger
            assert not smaller >  larger
            assert not larger  <= smaller
            assert not larger  <  smaller

            assert not smaller <  larger3
            assert not smaller <= larger3
            assert not larger3 >  smaller
            assert not larger3 >= smaller

            # Inequality strictness
            assert larger2 >= larger
            assert larger2 <= larger
            assert not larger2 > larger
            assert not larger2 < larger

            assert larger == larger2
            assert smaller != larger

            # There is an optimization on the zero-element case.
            assert empty == empty2
            assert not empty != empty2
            assert not empty == smaller
            assert empty != smaller

            # With the same size, an elementwise compare happens
            assert larger != larger3
            assert not larger == larger3

        helper(lambda x: x.viewkeys())
        helper(lambda x: x.viewitems())

    def test_contains(self):
        logger = []

        class Foo(object):

            def __init__(self, value, name=None):
                self.value = value
                self.name = name or value

            def __repr__(self):
                return '<Foo %s>' % self.name

            def __eq__(self, other):
                logger.append((self, other))
                return self.value == other.value

            def __hash__(self):
                return 42  # __eq__ will be used given all objects' hashes clash

        foo1, foo2, foo3 = Foo(1), Foo(2), Foo(3)
        foo42 = Foo(42)
        foo_dict = {foo1: 1, foo2: 1, foo3: 1}
        del logger[:]
        foo42 in foo_dict
        logger_copy = set(logger[:])  # prevent re-evaluation during pytest error print
        assert logger_copy == {(foo3, foo42), (foo2, foo42), (foo1, foo42)}

        del logger[:]
        foo2_bis = Foo(2, '2 bis')
        foo2_bis in foo_dict
        logger_copy = set(logger[:])  # prevent re-evaluation during pytest error print
        assert (foo2, foo2_bis) in logger_copy
        assert logger_copy.issubset({(foo1, foo2_bis), (foo2, foo2_bis), (foo3, foo2_bis)})


class AppTestStrategies(object):
    def setup_class(cls):
        if cls.runappdirect:
            py.test.skip("__repr__ doesn't work on appdirect")

    def w_get_strategy(self, obj):
        import __pypy__
        r = __pypy__.internal_repr(obj)
        return r[r.find("(") + 1: r.find(")")]

    def test_empty_to_string(self):
        d = {}
        assert "EmptyDictStrategy" in self.get_strategy(d)
        d[b"a"] = 1
        assert "BytesDictStrategy" in self.get_strategy(d)

        class O(object):
            pass
        o = O()
        d = o.__dict__ = {}
        assert "EmptyDictStrategy" in self.get_strategy(d)
        o.a = 1
        assert "BytesDictStrategy" in self.get_strategy(d)

    def test_empty_to_unicode(self):
        d = {}
        assert "EmptyDictStrategy" in self.get_strategy(d)
        d[u"a"] = 1
        assert "UnicodeDictStrategy" in self.get_strategy(d)
        assert d[u"a"] == 1
        assert d["a"] == 1
        assert d.keys() == [u"a"]
        assert type(d.keys()[0]) is unicode

    def test_empty_to_int(self):
        import sys
        d = {}
        d[1] = "hi"
        assert "IntDictStrategy" in self.get_strategy(d)
        assert d[1L] == "hi"

    def test_iter_dict_length_change(self):
        d = {1: 2, 3: 4, 5: 6}
        it = d.iteritems()
        d[7] = 8
        # 'd' is now length 4
        raises(RuntimeError, it.next)

    def test_iter_dict_strategy_only_change_1(self):
        d = {1: 2, 3: 4, 5: 6}
        it = d.iteritems()
        class Foo(object):
            def __eq__(self, other):
                return False
        assert d.get(Foo()) is None    # this changes the strategy of 'd'
        lst = list(it)  # but iterating still works
        assert sorted(lst) == [(1, 2), (3, 4), (5, 6)]

    def test_iter_dict_strategy_only_change_2(self):
        d = {1: 2, 3: 4, 5: 6}
        it = d.iteritems()
        d['foo'] = 'bar'
        del d[1]
        # 'd' is still length 3, but its strategy changed.  we are
        # getting a RuntimeError because iterating over the old storage
        # gives us (1, 2), but 1 is not in the dict any longer.
        raises(RuntimeError, list, it)


class FakeWrapper(object):
    hash_count = 0
    def unwrap(self, space):
        self.unwrapped = True
        return str(self)

    def __hash__(self):
        self.hash_count += 1
        return str.__hash__(self)

class FakeString(FakeWrapper, str):
    pass

class FakeUnicode(FakeWrapper, unicode):
    pass

# the minimal 'space' needed to use a W_DictMultiObject
class FakeSpace:
    hash_count = 0
    def hash_w(self, obj):
        self.hash_count += 1
        return hash(obj)
    def unwrap(self, x):
        return x
    def is_true(self, x):
        return x
    def is_(self, x, y):
        return x is y
    is_w = is_
    def eq(self, x, y):
        return x == y
    eq_w = eq
    def newlist(self, l):
        return l
    def newlist_bytes(self, l):
        return l
    DictObjectCls = W_DictObject
    def type(self, w_obj):
        if isinstance(w_obj, FakeString):
            return str
        return type(w_obj)
    w_str = str

    def str_w(self, string):
        assert isinstance(string, str)
        return string

    def int_w(self, integer, allow_conversion=True):
        assert isinstance(integer, int)
        return integer

    def wrap(self, obj):
        return obj

    def isinstance_w(self, obj, klass):
        return isinstance(obj, klass)
    isinstance = isinstance_w

    def newtuple(self, l):
        return tuple(l)

    def newdict(self, module=False, instance=False):
        return W_DictObject.allocate_and_init_instance(
                self, module=module, instance=instance)

    def view_as_kwargs(self, w_d):
        return w_d.view_as_kwargs() # assume it's a multidict

    def finditem_str(self, w_dict, s):
        return w_dict.getitem_str(s) # assume it's a multidict

    def setitem_str(self, w_dict, s, w_value):
        return w_dict.setitem_str(s, w_value) # assume it's a multidict

    def delitem(self, w_dict, w_s):
        return w_dict.delitem(w_s) # assume it's a multidict

    def allocate_instance(self, cls, type):
        return object.__new__(cls)

    def fromcache(self, cls):
        return cls(self)

    w_StopIteration = StopIteration
    w_None = None
    w_NoneType = type(None, None)
    w_int = int
    w_bool = bool
    w_float = float
    StringObjectCls = FakeString
    UnicodeObjectCls = FakeUnicode
    w_dict = W_DictObject
    iter = iter
    fixedview = list
    listview  = list

class Config:
    class objspace:
        class std:
            withcelldict = False
            methodcachesizeexp = 11
            withmethodcachecounter = False

FakeSpace.config = Config()


class TestDictImplementation:
    def setup_method(self,method):
        self.space = FakeSpace()

    def test_stressdict(self):
        from random import randint
        d = self.space.newdict()
        N = 10000
        pydict = {}
        for i in range(N):
            x = randint(-N, N)
            d.descr_setitem(self.space, x, i)
            pydict[x] = i
        for key, value in pydict.iteritems():
            assert value == d.descr_getitem(self.space, key)

class BaseTestRDictImplementation:

    def setup_method(self,method):
        self.fakespace = FakeSpace()
        self.string = self.fakespace.wrap("fish")
        self.string2 = self.fakespace.wrap("fish2")
        self.impl = self.get_impl()

    def get_impl(self):
        strategy = self.StrategyClass(self.fakespace)
        storage = strategy.get_empty_storage()
        w_dict = self.fakespace.allocate_instance(W_DictObject, None)
        W_DictObject.__init__(w_dict, self.fakespace, strategy, storage)
        return w_dict

    def fill_impl(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)

    def check_not_devolved(self):
        #XXX check if strategy changed!?
        assert type(self.impl.get_strategy()) is self.StrategyClass
        #assert self.impl.r_dict_content is None

    def test_popitem(self):
        self.fill_impl()
        assert self.impl.length() == 2
        a, b = self.impl.popitem()
        assert self.impl.length() == 1
        if a == self.string:
            assert b == 1000
            assert self.impl.getitem(self.string2) == 2000
        else:
            assert a == self.string2
            assert b == 2000
            assert self.impl.getitem_str(self.string) == 1000
        self.check_not_devolved()

    def test_setitem(self):
        self.impl.setitem(self.string, 1000)
        assert self.impl.length() == 1
        assert self.impl.getitem(self.string) == 1000
        assert self.impl.getitem_str(self.string) == 1000
        self.check_not_devolved()

    def test_setitem_str(self):
        self.impl.setitem_str(self.fakespace.str_w(self.string), 1000)
        assert self.impl.length() == 1
        assert self.impl.getitem(self.string) == 1000
        assert self.impl.getitem_str(self.string) == 1000
        self.check_not_devolved()

    def test_delitem(self):
        self.fill_impl()
        assert self.impl.length() == 2
        self.impl.delitem(self.string2)
        assert self.impl.length() == 1
        self.impl.delitem(self.string)
        assert self.impl.length() == 0
        self.check_not_devolved()

    def test_clear(self):
        self.fill_impl()
        assert self.impl.length() == 2
        self.impl.clear()
        assert self.impl.length() == 0
        self.check_not_devolved()


    def test_keys(self):
        self.fill_impl()
        keys = self.impl.w_keys() # wrapped lists = lists in the fake space
        keys.sort()
        assert keys == [self.string, self.string2]
        self.check_not_devolved()

    def test_values(self):
        self.fill_impl()
        values = self.impl.values()
        values.sort()
        assert values == [1000, 2000]
        self.check_not_devolved()

    def test_items(self):
        self.fill_impl()
        items = self.impl.items()
        items.sort()
        assert items == zip([self.string, self.string2], [1000, 2000])
        self.check_not_devolved()

    def test_iter(self):
        self.fill_impl()
        iteratorimplementation = self.impl.iteritems()
        items = []
        while 1:
            item = iteratorimplementation.next_item()
            if item == (None, None):
                break
            items.append(item)
        items.sort()
        assert items == zip([self.string, self.string2], [1000, 2000])
        self.check_not_devolved()

    def test_devolve(self):
        impl = self.impl
        for x in xrange(100):
            impl.setitem(self.fakespace.str_w(str(x)), x)
            impl.setitem(x, x)
        assert type(impl.get_strategy()) is ObjectDictStrategy


    setdefault_hash_count = 1

    def test_setdefault_fast(self):
        on_pypy = "__pypy__" in sys.builtin_module_names
        impl = self.impl
        key = FakeString(self.string)
        x = impl.setdefault(key, 1)
        assert x == 1
        if on_pypy:
            assert key.hash_count == self.setdefault_hash_count
        x = impl.setdefault(key, 2)
        assert x == 1
        if on_pypy:
            assert key.hash_count == self.setdefault_hash_count + 1

    def test_fallback_evil_key(self):
        class F(object):
            def __hash__(self):
                return hash("s")
            def __eq__(self, other):
                return other == "s"

        d = self.get_impl()
        w_key = FakeString("s")
        d.setitem(w_key, 12)
        assert d.getitem(w_key) == 12
        assert d.getitem(F()) == d.getitem(w_key)

        d = self.get_impl()
        x = d.setdefault(w_key, 12)
        assert x == 12
        x = d.setdefault(F(), 12)
        assert x == 12

        d = self.get_impl()
        x = d.setdefault(F(), 12)
        assert x == 12

        d = self.get_impl()
        d.setitem(w_key, 12)
        d.delitem(F())

        assert w_key not in d.w_keys()
        assert F() not in d.w_keys()

class TestBytesDictImplementation(BaseTestRDictImplementation):
    StrategyClass = BytesDictStrategy

    def test_str_shortcut(self):
        self.fill_impl()
        s = FakeString(self.string)
        assert self.impl.getitem(s) == 1000
        assert s.unwrapped

    def test_view_as_kwargs(self):
        self.fill_impl()
        assert self.fakespace.view_as_kwargs(self.impl) == (["fish", "fish2"], [1000, 2000])


class BaseTestDevolvedDictImplementation(BaseTestRDictImplementation):
    def fill_impl(self):
        BaseTestRDictImplementation.fill_impl(self)
        self.impl.get_strategy().switch_to_object_strategy(self.impl)

    def check_not_devolved(self):
        pass

class TestDevolvedBytesDictImplementation(BaseTestDevolvedDictImplementation):
    StrategyClass = BytesDictStrategy


def test_module_uses_strdict():
    fakespace = FakeSpace()
    d = fakespace.newdict(module=True)
    assert type(d.get_strategy()) is BytesDictStrategy

