import py
from pypy.rlib.objectmodel import *
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.conftest import option

def strange_key_eq(key1, key2):
    return key1[0] == key2[0]   # only the 1st character is relevant
def strange_key_hash(key):
    return ord(key[0])

def play_with_r_dict(d):
    d['hello'] = 41
    d['hello'] = 42
    assert d['hi there'] == 42
    try:
        unexpected = d["dumb"]
    except KeyError:
        pass
    else:
        assert False, "should have raised, got %s" % unexpected
    assert len(d) == 1
    assert 'oops' not in d

    count = 0
    for x in d:
        assert x == 'hello'
        count += 1
    assert count == 1

    assert d.get('hola', -1) == 42
    assert d.get('salut', -1) == -1
    d1 = d.copy()
    del d['hu!']
    assert len(d) == 0
    assert d1.keys() == ['hello']
    d.update(d1)
    assert d.values() == [42]
    lst = d.items()
    assert len(lst) == 1 and len(lst[0]) == 2
    assert lst[0][0] == 'hello' and lst[0][1] == 42

    count = 0
    for x in d.iterkeys():
        assert x == 'hello'
        count += 1
    assert count == 1

    count = 0
    for x in d.itervalues():
        assert x == 42
        count += 1
    assert count == 1
        
    count = 0
    for x in d.iteritems():
        assert len(x) == 2 and x[0] == 'hello' and x[1] == 42
        count += 1
    assert count == 1
        
    d.clear()
    assert d.keys() == []
    return True   # for the tests below


def test_recursive_r_dict_repr():
    import operator
    rdic = r_dict(operator.eq, hash)
    rdic['x'] = rdic
    assert str(rdic) == "r_dict({'x': r_dict({...})})"
    assert repr(rdic)== "r_dict({'x': r_dict({...})})"

def test_r_dict():
    # NB. this test function is also annotated/rtyped by the next tests
    d = r_dict(strange_key_eq, strange_key_hash)
    return play_with_r_dict(d)

class Strange:
    def key_eq(strange, key1, key2):
        return key1[0] == key2[0]   # only the 1st character is relevant
    def key_hash(strange, key):
        return ord(key[0])

def test_r_dict_bm():
    # NB. this test function is also annotated by the next tests
    strange = Strange()
    d = r_dict(strange.key_eq, strange.key_hash)
    return play_with_r_dict(d)

def test_annotate_r_dict():
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(test_r_dict, [])
    #t.view()
    graph = graphof(t, strange_key_eq)
    assert a.binding(graph.getargs()[0]).knowntype == str
    assert a.binding(graph.getargs()[1]).knowntype == str
    graph = graphof(t, strange_key_hash)
    assert a.binding(graph.getargs()[0]).knowntype == str

def test_annotate_r_dict_bm():
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(test_r_dict_bm, [])
    #t.view()
    strange_key_eq = Strange.key_eq.im_func
    strange_key_hash = Strange.key_hash.im_func

    Strange_def = a.bookkeeper.getuniqueclassdef(Strange)

    graph = graphof(t, strange_key_eq)
    assert a.binding(graph.getargs()[0]).knowntype == Strange_def
    assert a.binding(graph.getargs()[1]).knowntype == str
    assert a.binding(graph.getargs()[2]).knowntype == str
    graph = graphof(t, strange_key_hash)
    assert a.binding(graph.getargs()[0]).knowntype == Strange_def
    assert a.binding(graph.getargs()[1]).knowntype == str


def test_unboxed_value():
    class Base(object):
        __slots__ = ()
    class C(Base, UnboxedValue):
        __slots__ = 'smallint'

    assert C(17).smallint == 17
    assert C(17).get_untagged_value() == 17

    class A(UnboxedValue):
        __slots__ = ['value']

    assert A(12098).value == 12098
    assert A(12098).get_untagged_value() == 12098

def test_symbolic():
    py.test.skip("xxx no test here")

def test_symbolic_raises():
    s1 = Symbolic()
    s2 = Symbolic()
    py.test.raises(TypeError, "s1 < s2")
    py.test.raises(TypeError, "hash(s1)")

def test_compute_hash():
    from pypy.rlib.objectmodel import _hash_string, _hash_float, _hash_tuple
    assert compute_hash("Hello") == _hash_string("Hello")
    assert compute_hash(7) == 7
    assert compute_hash(-3.5) == _hash_float(-3.5)
    assert compute_hash(None) == 0
    assert compute_hash(("world", None, 7)) == _hash_tuple(("world", None, 7))
    #
    class Foo(object):
        def __hash__(self):
            return 42
    foo = Foo()
    h = compute_hash(foo)
    assert h == object.__hash__(foo)
    assert h == getattr(foo, '__precomputed_identity_hash')
    assert compute_hash(None) == 0

def test_compute_hash_float():
    from pypy.rlib.rfloat import INFINITY, NAN
    assert compute_hash(INFINITY) == 314159
    assert compute_hash(-INFINITY) == -271828
    assert compute_hash(NAN) == 0

def test_compute_identity_hash():
    class Foo(object):
        def __hash__(self):
            return 42
    foo = Foo()
    h = compute_identity_hash(foo)
    assert h == object.__hash__(foo)
    assert h == getattr(foo, '__precomputed_identity_hash')

def test_compute_unique_id():
    class Foo(object):
        pass
    foo = Foo()
    assert compute_unique_id(foo) == id(foo)

def test_current_object_addr_as_int():
    from pypy.rlib.rarithmetic import intmask
    class Foo(object):
        pass
    foo = Foo()
    assert current_object_addr_as_int(foo) == intmask(id(foo))

class BaseTestObjectModel(BaseRtypingTest):

    def test_we_are_translated(self):
        assert we_are_translated() == False

        def fn():
            return we_are_translated()
        res = self.interpret(fn, [])
        assert res is True
    
    def test_rtype_r_dict(self):
        res = self.interpret(test_r_dict, [])
        assert res is True

    def test_rtype_r_dict_bm(self):
        res = self.interpret(test_r_dict_bm, [])
        assert res is True

    def test_rtype_constant_r_dicts(self):
        d1 = r_dict(strange_key_eq, strange_key_hash)
        d1['hello'] = 666
        d2 = r_dict(strange_key_eq, strange_key_hash)
        d2['hello'] = 777
        d2['world'] = 888
        def fn(i):
            if i == 1:
                d = d1
            else:
                d = d2
            return len(d)
        res = self.interpret(fn, [1])
        assert res == 1
        res = self.interpret(fn, [2])
        assert res == 2

    def test_rtype_r_dict_singlefrozen_func(self):
        class FreezingClass(Strange):
            def _freeze_(self):
                return True
        obj = FreezingClass()
        def fn():
            d = r_dict(obj.key_eq, obj.key_hash)
            return play_with_r_dict(d)
        assert self.interpret(fn, []) is True

    def test_rtype_r_dict_singlefrozen_func_pbc(self):
        class FreezingClass(Strange):
            def _freeze_(self):
                return True
        obj = FreezingClass()
        pbc_d = r_dict(obj.key_eq, obj.key_hash)        
        def fn():
            return play_with_r_dict(pbc_d)
        assert self.interpret(fn, []) is True

    def test_rtype_r_dict_exceptions(self):
        def raising_hash(obj):
            if obj.startswith("bla"):
                raise TypeError
            return 1
        def eq(obj1, obj2):
            return obj1 is obj2
        def f():
            d1 = r_dict(eq, raising_hash)
            d1['xxx'] = 1
            try:
                x = d1["blabla"]
            except Exception:
                return 42
            return x
        res = self.interpret(f, [])
        assert res == 42

        def f():
            d1 = r_dict(eq, raising_hash)
            d1['xxx'] = 1
            try:
                x = d1["blabla"]
            except TypeError:
                return 42
            return x
        res = self.interpret(f, [])
        assert res == 42

        def f():
            d1 = r_dict(eq, raising_hash)
            d1['xxx'] = 1
            try:
                d1["blabla"] = 2
            except TypeError:
                return 42
            return 0
        res = self.interpret(f, [])
        assert res == 42

    def test_access_in_try(self):
        h = lambda x: 1
        eq = lambda x,y: x==y
        def f(d):
            try:
                return d[2]
            except ZeroDivisionError:
                return 42
            return -1
        def g(n):
            d = r_dict(eq, h)
            d[1] = n
            d[2] = 2*n
            return f(d)
        res = self.interpret(g, [3])
        assert res == 6

    def test_access_in_try_set(self):
        h = lambda x: 1
        eq = lambda x,y: x==y
        def f(d):
            try:
                d[2] = 77
            except ZeroDivisionError:
                return 42
            return -1
        def g(n):
            d = r_dict(eq, h)
            d[1] = n
            f(d)
            return d[2]
        res = self.interpret(g, [3])
        assert res == 77

    def test_compute_hash(self):
        class Foo(object):
            pass
        def f(i):
            assert compute_hash(i) == compute_hash(42)
            assert compute_hash(i+1.0) == compute_hash(43.0)
            assert compute_hash("Hello" + str(i)) == compute_hash("Hello42")
            if i == 42:
                p = None
            else:
                p = Foo()
            assert compute_hash(p) == compute_hash(None)
            assert (compute_hash(("world", None, i, 7.5)) ==
                    compute_hash(("world", None, 42, 7.5)))
            q = Foo()
            assert compute_hash(q) == compute_identity_hash(q)
            from pypy.rlib.rfloat import INFINITY, NAN
            assert compute_hash(INFINITY) == 314159
            assert compute_hash(-INFINITY) == -271828
            assert compute_hash(NAN) == 0
            return i*2
        res = self.interpret(f, [42])
        assert res == 84


class TestLLtype(BaseTestObjectModel, LLRtypeMixin):

    def test_rtype_keepalive(self):
        from pypy.rlib import objectmodel
        def f():
            x = [1]
            y = ['b']
            objectmodel.keepalive_until_here(x,y)
            return 1

        res = self.interpret(f, [])
        assert res == 1

    def test_compute_hash_across_translation(self):
        class Foo(object):
            pass
        q = Foo()

        def f(i):
            assert compute_hash(None) == 0
            assert compute_hash(i) == h_42
            assert compute_hash(i+1.0) == h_43_dot_0
            assert compute_hash((i+3)/6.0) == h_7_dot_5
            assert compute_hash("Hello" + str(i)) == h_Hello42
            if i == 42:
                p = None
            else:
                p = Foo()
            assert compute_hash(p) == h_None
            assert compute_hash(("world", None, i, 7.5)) == h_tuple
            assert compute_hash(q) == h_q
            return i*2
        h_42       = compute_hash(42)
        h_43_dot_0 = compute_hash(43.0)
        h_7_dot_5  = compute_hash(7.5)
        h_Hello42  = compute_hash("Hello42")
        h_None     = compute_hash(None)
        h_tuple    = compute_hash(("world", None, 42, 7.5))
        h_q        = compute_hash(q)
        
        res = self.interpret(f, [42])
        assert res == 84


class TestOOtype(BaseTestObjectModel, OORtypeMixin):
    pass


def test_specialize_decorator():
    def f():
        pass

    specialize.memo()(f)
    
    assert f._annspecialcase_ == 'specialize:memo'

    specialize.arg(0)(f)

    assert f._annspecialcase_ == 'specialize:arg(0)'

    specialize.arg(1)(f)

    assert f._annspecialcase_ == 'specialize:arg(1)'

def test_enforceargs_decorator():
    @enforceargs(int, str, None)
    def f(a, b, c):
        pass

    assert f._annenforceargs_ == (int, str, None)

def getgraph(f, argtypes):
    from pypy.translator.translator import TranslationContext, graphof
    from pypy.translator.backendopt.all import backend_optimizations
    t = TranslationContext()
    a = t.buildannotator()
    typer = t.buildrtyper()
    a.build_types(f, argtypes)
    typer.specialize()
    backend_optimizations(t)
    graph = graphof(t, f)
    if option.view:
        graph.show()
    return graph
