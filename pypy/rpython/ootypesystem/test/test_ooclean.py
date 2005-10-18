from pypy.translator.translator import Translator
from pypy.rpython import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.test.test_llinterp import interpret
import py

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
    result = interpret(f, [1, 2], type_system='ootype')
    assert result == 3

def test_simple_call():
    def f(a, b):
        return a + b

    def g():
        return f(5, 3)
    result = interpret(g, [], type_system='ootype')
    assert result == 8

# Adjusted from test_rclass.py
class EmptyBase(object):
    pass

def test_simple_empty_base():
    def dummyfn():
        x = EmptyBase()
        return x
    result = interpret(dummyfn, [], type_system='ootype')
    assert isinstance(ootype.typeOf(result), ootype.Instance)


def test_instance_attribute():
    def dummyfn():
        x = EmptyBase()
        x.a = 1
        return x.a
    result = interpret(dummyfn, [], type_system='ootype')
    assert result == 1

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
    result = interpret(dummyfn, [], type_system='ootype')
    assert result == 1 + 2 + 3

def test_polymorphic_field():
    def dummyfn(choosesubclass):
        if choosesubclass:
            y = Subclass()
            y.a = 0
            y.b = 1
        else:
            y = EmptyBase()
            y.a = 1
        return y.a
    result = interpret(dummyfn, [True], type_system='ootype')
    assert result == 0
    result = interpret(dummyfn, [False], type_system='ootype')
    assert result == 1    

class HasAMethod(object):
    def f(self):
        return 1
        
def test_method():
    def dummyfn():
        inst = HasAMethod()
        return inst.f()
    result = interpret(dummyfn, [], type_system='ootype')
    assert result == 1

class OverridesAMethod(HasAMethod):
    def f(self):
        return 2

def test_override():
    def dummyfn(flag):
        if flag:
            inst = HasAMethod()
        else:
            inst = OverridesAMethod()
        return inst.f()
    result = interpret(dummyfn, [True], type_system='ootype')
    assert result == 1
    result = interpret(dummyfn, [False], type_system='ootype')
    assert result == 2

class HasAField(object):
    def f(self):
        return self.a

def test_prebuilt_instance():
    inst = HasAField()
    inst.a = 3
    def dummyfn():
        return inst.f()
    result = interpret(dummyfn, [], type_system='ootype')
    assert result == 3

def test_recursive_prebuilt_instance():
    a = EmptyBase()
    b = EmptyBase()
    a.x = 5
    b.x = 6
    a.peer = b
    b.peer = a
    def dummyfn():
        return a.peer.peer.peer.x
    res = interpret(dummyfn, [], type_system='ootype')
    assert res == 6

class HasClassAttr(object):
    a = 3
    def f(self, n):
        return n + self.a

class OverridesClassAttr(HasClassAttr):
    a = 42

def test_single_class_attr():
    def dummyfn():
        inst = HasClassAttr()
        return inst.f(100)
    result = interpret(dummyfn, [], type_system='ootype')
    assert result == 103

def test_class_attr():
    def dummyfn(flag):
        if flag:
            inst = HasClassAttr()
        else:
            inst = OverridesClassAttr()
        return inst.f(100)
    result = interpret(dummyfn, [True], type_system='ootype')
    assert result == 103
    result = interpret(dummyfn, [False], type_system='ootype')
    assert result == 142

def test_classattr_as_defaults():
    class MySubclass(HasClassAttr):
        pass
    def dummyfn():
        x = MySubclass()
        x.a += 1
        return x.a
    res = interpret(dummyfn, [], type_system='ootype')
    assert res == 4
