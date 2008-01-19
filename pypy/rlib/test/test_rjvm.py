import py
try:
    import jpype
except ImportError:
    py.test.skip("In Progress...")

from pypy.rlib.rjvm import java, JavaWrapper, JavaClassWrapper, JavaInstanceWrapper, JavaMethodWrapper, JavaStaticMethodWrapper

def test_static_method():
    assert isinstance(java.lang, JavaWrapper)
    assert isinstance(java.lang.Math, JavaClassWrapper)
    assert isinstance(java.lang.Math.abs, JavaStaticMethodWrapper)
    result = java.lang.Math.abs(-42)
    assert isinstance(result, int)
    assert result == 42

def test_class_instantiate():
    al = java.util.ArrayList()
    assert isinstance(al, JavaInstanceWrapper)
    assert isinstance(al.add, JavaMethodWrapper)
    al.add("test")
    assert al.get(0) == "test"

def test_reflection():
    py.test.skip('in progress')
    al_class = java.lang.Class.forName("java.util.ArrayList")
    assert isinstance(al_class, JavaInstanceWrapper)
    #meths = al_class.__javaclass__.getDeclaredMethods()
    constructors = al_class.getDeclaredConstructors()
    meths = al_class.getDeclaredMethods()
    al = constructors[0].newInstance([])
    al_org = java.util.ArrayList()
    assert isinstance(al, JavaInstanceWrapper)
    assert isinstance(al.add, JavaMethodWrapper)
    al_add = meths[2]
    assert isinstance(al_add, JavaInstanceWrapper)
    assert isinstance(al_add.invoke, JavaMethodWrapper)
    # This fail, but work on the command line
    al_add.invoke(al_org, ["Hello"])
    assert al_org[0] == "Hello"
    al_add.invoke(al, ["Hello"])
    assert al[0] == "Hello"
