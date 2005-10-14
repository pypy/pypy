from pypy.translator.translator import Translator
from pypy.rpython import lltype
from pypy.rpython.ootypesystem import ootype

def specialize(f, input_types):
    t = Translator(f)
    t.annotate(input_types)
    t.specialize(type_system="ootype")

    graph = t.flowgraphs[f]
    check_only_ootype(graph)

def check_only_ootype(graph):
    def check_ootype(v):
        t = v.concretetype
        assert isinstance(t, ootype.Primitive) or isinstance(t, ootype.OOType)
	
    for block in graph.iterblocks():
    	for var in block.getvariables():
	    check_ootype(var)
	for const in block.getconstants():
	    check_ootype(const)

def test_simple():
    def f(a, b):
        return a + b
    specialize(f, [int, int])

def test_simple_call():
    def f(a, b):
        return a + b

    def g():
        return f(5, 3)
    specialize(g, [])

# Adjusted from test_rclass.py
class EmptyBase(object):
    pass

def inprogress_test_simple_empty_base():
    def dummyfn():
        x = EmptyBase()
        return x
    specialize(dummyfn, [])
