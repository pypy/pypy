from pypy.rpython.objectmodel import *
from pypy.translator.translator import Translator
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
    d['hello'] = 42
    assert d['hi there'] == 42
    try:
        d["dumb"]
    except KeyError:
        pass
    else:
        assert False, "should have raised"
    assert len(d) == 1
    assert 'oops' not in d
    x, = d
    assert x == 'hello'
    assert d.get('hola', -1) == 42
    assert d.get('salut', -1) == -1
    d1 = d.copy()
    del d['hu!']
    assert len(d) == 0
    assert d1.keys() == ['hello']
    d.update(d1)
    assert d.values() == [42]
    assert d.items() == [('hello', 42)]
    x, = d.iterkeys()
    assert x == 'hello'
    x, = d.itervalues()
    assert x == 42
    x, = d.iteritems()
    assert x == ('hello', 42)
    d.clear()
    assert d.keys() == []
    return True   # for the tests below


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
    t = Translator(test_r_dict)
    a = t.annotate([])
    #t.view()
    assert strange_key_eq in t.flowgraphs
    assert strange_key_hash in t.flowgraphs
    graph = t.flowgraphs[strange_key_eq]
    assert a.binding(graph.getargs()[0]).knowntype == str
    assert a.binding(graph.getargs()[1]).knowntype == str
    graph = t.flowgraphs[strange_key_hash]
    assert a.binding(graph.getargs()[0]).knowntype == str

def test_annotate_r_dict_bm():
    t = Translator(test_r_dict_bm)
    a = t.annotate([])
    #t.view()
    strange_key_eq = Strange.key_eq.im_func
    strange_key_hash = Strange.key_hash.im_func

    assert strange_key_eq in t.flowgraphs
    assert strange_key_hash in t.flowgraphs
    graph = t.flowgraphs[strange_key_eq]
    assert a.binding(graph.getargs()[0]).knowntype == Strange
    assert a.binding(graph.getargs()[1]).knowntype == str
    assert a.binding(graph.getargs()[2]).knowntype == str
    graph = t.flowgraphs[strange_key_hash]
    assert a.binding(graph.getargs()[0]).knowntype == Strange
    assert a.binding(graph.getargs()[1]).knowntype == str

def INPROGRESS_test_rtype_r_dict():
    res = interpret(test_r_dict, [])
    assert res is True
