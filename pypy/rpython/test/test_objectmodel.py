import py
from pypy.rpython.objectmodel import *
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.test.test_llinterp import interpret

def test_we_are_translated():
    assert we_are_translated() == False

    def fn():
        return we_are_translated()
    res = interpret(fn, [])
    assert res is True

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

def test_rtype_r_dict():
    res = interpret(test_r_dict, [])
    assert res is True

def test_rtype_r_dict_bm():
    res = interpret(test_r_dict_bm, [])
    assert res is True

def test_rtype_constant_r_dicts():
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
    res = interpret(fn, [1])
    assert res == 1
    res = interpret(fn, [2])
    assert res == 2

def test_rtype_keepalive():
    from pypy.rpython import objectmodel
    def f():
        x = [1]
        y = ['b']
        objectmodel.keepalive_until_here(x,y)
        return 1

    res = interpret(f, [])
    assert res == 1

def test_hint():
    from pypy.rpython import objectmodel
    def f():
        x = objectmodel.hint(5, hello="world")
        return x
    res = interpret(f, [])
    assert res == 5

def test_cast_ptr_to_adr():
    from pypy.rpython import objectmodel
    from pypy.rpython.memory.test.test_llinterpsim import interpret
    class A(object):
        pass
    def f(x):
        if x:
            a = A()
        else:
            a = None
        adr_a = objectmodel.cast_ptr_to_adr(a)
        return bool(adr_a)
    res = interpret(f, [1])
    assert res
    res = interpret(f, [0])
    assert not res

def test_cast_adr_to_ptr():
    from pypy.rpython import objectmodel
    from pypy.rpython.memory.test.test_llinterpsim import interpret
    from pypy.rpython.lltypesystem import lltype
    S = lltype.GcStruct("S", ("x", lltype.Signed))
    Sptr = lltype.Ptr(S)
    def f():
        s1 = lltype.malloc(S)
        adr = objectmodel.cast_ptr_to_adr(s1)
        s2 = objectmodel.cast_adr_to_ptr(adr, Sptr)
        return s1 == s2
    res = interpret(f, [])
    assert res
