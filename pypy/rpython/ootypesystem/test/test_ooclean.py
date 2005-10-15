from pypy.translator.translator import Translator
from pypy.rpython import lltype
from pypy.rpython.ootypesystem import ootype

def specialize(f, input_types, viewBefore=False, viewAfter=False):
    t = Translator(f)
    t.annotate(input_types)
    if viewBefore:
        t.view()
    t.specialize(type_system="ootype")
    if viewAfter:
        t.view()

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

def test_simple_empty_base():
    def dummyfn():
        x = EmptyBase()
        return x
    specialize(dummyfn, [])


def test_instance_attribute():
    def dummyfn():
        x = EmptyBase()
        x.a = 1
        return x.a
    specialize(dummyfn, [])

class Subclass(EmptyBase):
    pass

def test_subclass_attributes():
    def dummyfn():
        x = EmptyBase()
        x.a = 1
        y = Subclass()
        y.a = 2
        y.b = 3
        return x.a + y.a + y.b
    specialize(dummyfn, [])
    
        
