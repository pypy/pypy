import pytest
from types import GenericAlias
from typing import TypeVar, Any
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

def test_init():
    g = GenericAlias(list, int)
    assert g.__origin__ is list
    assert g.__args__ == (int, )
    assert g.__parameters__ == ()
    g = GenericAlias(list, (int, ))
    assert g.__origin__ is list
    assert g.__args__ == (int, )
    assert g.__parameters__ == ()

def test_instantiate():
    g = GenericAlias(list, int)
    assert g("abc") == list("abc")

def test_subclass():
    g = GenericAlias(list, int)
    class l(g): pass
    assert l.__bases__ == (list, )

def test_unbound_methods():
    g = GenericAlias(list, int)
    l = [1, 2, 3]
    g.append(l, 4)
    assert l == [1, 2, 3, 4]

def test_classmethod():
    g = GenericAlias(dict, int)
    d = g.fromkeys([1, 2, 3])
    assert d == dict.fromkeys([1, 2, 3])

def test_no_chaining():
    g = GenericAlias(dict, int)
    with pytest.raises(TypeError):
        g[int]

def test_repr():
    g = GenericAlias(dict, int)
    assert repr(g) == "dict[int]"
    g = GenericAlias(dict, (int, ...))
    assert repr(g) == "dict[int, ...]"
    g = GenericAlias(dict, ())
    assert repr(g) == "dict[()]"

def test_repr_bug():
    l = list[list[int]]
    assert repr(l) == 'list[list[int]]'

def test_equality():
    g = GenericAlias(dict, int)
    assert g == GenericAlias(dict, int)
    assert g != GenericAlias(dict, float)

def test_hash():
    g = GenericAlias(dict, int)
    assert hash(g) == hash(GenericAlias(dict, int))
    assert hash(g) != hash(GenericAlias(dict, float))

def test_dir():
    g = GenericAlias(dict, int)
    assert set(dir(dict)).issubset(set(dir(g)))
    assert "__origin__" in dir(g)
    # Make sure the list does not have repeats
    assert len(set(dir(g))) == len(dir(g))

def test_parameters():
    g = GenericAlias(dict, (int, V))
    assert g.__parameters__ == (V, )
    g = GenericAlias(dict, (V, V))
    assert g.__parameters__ == (V, )
    g1 = GenericAlias(list, g)
    assert g1.__parameters__ == (V, )

def test_parameters_instantiate():
    g = GenericAlias(dict, (int, V))
    assert g.__parameters__ == (V, )
    g1 = g[float]
    assert g1.__origin__ is dict
    assert g1.__args__ == (int, float)

    g = GenericAlias(dict, (K, V))
    assert g.__parameters__ == (K, V, )
    g1 = g[float, int]
    assert g1.__origin__ is dict
    assert g1.__args__ == (float, int)

    g = GenericAlias(list, GenericAlias(dict, (K, V)))
    assert g.__parameters__ == (K, V, )
    g1 = g[float, int]
    assert g1.__origin__ is list
    assert g1.__args__[0].__origin__ == dict
    assert g1.__args__[0].__args__ == (float, int)

def test_subclasscheck():
    with pytest.raises(TypeError):
        issubclass(dict, GenericAlias(dict, int))

def test_instancescheck():
    with pytest.raises(TypeError):
        isinstance({}, GenericAlias(dict, int))

def test_new():
    g = GenericAlias.__new__(GenericAlias, list, int)
    assert g.__origin__ is list
    assert g.__args__ == (int, )

def test_reduce():
    g = GenericAlias.__new__(GenericAlias, list, int)
    assert g.__reduce__() == (GenericAlias, (list, (int, )))

def test_orig_class():
    class A:
        pass

    g = GenericAlias(A, int)
    assert g().__orig_class__ is g

def test_cmp_not_implemented():
    g = GenericAlias(list, int)
    assert not (g == Any)
    assert g != Any

def test_cant_write_attributes():
    g = GenericAlias(list, int)
    with pytest.raises(AttributeError):
        g.__origin__ = dict
    with pytest.raises(AttributeError):
        g.__args__ = (1, )
    with pytest.raises(AttributeError):
        g.__parameters__ = (2, )
    with pytest.raises(AttributeError):
        g.test = 127

def test_orig_class_writing_gives_typeerror():
    class A:
        def __new__(cls):
            return int

    g = GenericAlias(A, int)
    assert g() is int # does not crash

