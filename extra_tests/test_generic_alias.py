import pytest
from types import GenericAlias, UnionType
from _pypy_generic_alias import _create_union
from typing import TypeVar, Any, Union
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

def test_ga_init():
    g = GenericAlias(list, int)
    assert g.__origin__ is list
    assert g.__args__ == (int, )
    assert g.__parameters__ == ()
    g = GenericAlias(list, (int, ))
    assert g.__origin__ is list
    assert g.__args__ == (int, )
    assert g.__parameters__ == ()

def test_ga_instantiate():
    g = GenericAlias(list, int)
    assert g("abc") == list("abc")

def test_ga_subclass():
    g = GenericAlias(list, int)
    class l(g): pass
    assert l.__bases__ == (list, )

def test_ga_unbound_methods():
    g = GenericAlias(list, int)
    l = [1, 2, 3]
    g.append(l, 4)
    assert l == [1, 2, 3, 4]

def test_ga_classmethod():
    g = GenericAlias(dict, int)
    d = g.fromkeys([1, 2, 3])
    assert d == dict.fromkeys([1, 2, 3])

def test_ga_no_chaining():
    g = GenericAlias(dict, int)
    with pytest.raises(TypeError):
        g[int]

def test_ga_repr():
    g = GenericAlias(dict, int)
    assert repr(g) == "dict[int]"
    g = GenericAlias(dict, (int, ...))
    assert repr(g) == "dict[int, ...]"
    g = GenericAlias(dict, ())
    assert repr(g) == "dict[()]"

def test_ga_repr_bug():
    l = list[list[int]]
    assert repr(l) == 'list[list[int]]'

def test_ga_equality():
    g = GenericAlias(dict, int)
    assert g == GenericAlias(dict, int)
    assert g != GenericAlias(dict, float)

def test_ga_hash():
    g = GenericAlias(dict, int)
    assert hash(g) == hash(GenericAlias(dict, int))
    assert hash(g) != hash(GenericAlias(dict, float))

def test_ga_dir():
    g = GenericAlias(dict, int)
    assert set(dir(dict)).issubset(set(dir(g)))
    assert "__origin__" in dir(g)
    # Make sure the list does not have repeats
    assert len(set(dir(g))) == len(dir(g))

def test_ga_parameters():
    g = GenericAlias(dict, (int, V))
    assert g.__parameters__ == (V, )
    g = GenericAlias(dict, (V, V))
    assert g.__parameters__ == (V, )
    g1 = GenericAlias(list, g)
    assert g1.__parameters__ == (V, )

def test_ga_parameters_instantiate():
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

def test_ga_subclasscheck():
    with pytest.raises(TypeError):
        issubclass(dict, GenericAlias(dict, int))

def test_ga_instancescheck():
    with pytest.raises(TypeError):
        isinstance({}, GenericAlias(dict, int))

def test_ga_new():
    g = GenericAlias.__new__(GenericAlias, list, int)
    assert g.__origin__ is list
    assert g.__args__ == (int, )

def test_ga_reduce():
    g = GenericAlias.__new__(GenericAlias, list, int)
    assert g.__reduce__() == (GenericAlias, (list, (int, )))

def test_ga_orig_class():
    class A:
        pass

    g = GenericAlias(A, int)
    assert g().__orig_class__ is g

def test_ga_cmp_not_implemented():
    g = GenericAlias(list, int)
    assert not (g == Any)
    assert g != Any

def test_ga_cant_write_attributes():
    g = GenericAlias(list, int)
    with pytest.raises(AttributeError):
        g.__origin__ = dict
    with pytest.raises(AttributeError):
        g.__args__ = (1, )
    with pytest.raises(AttributeError):
        g.__parameters__ = (2, )
    with pytest.raises(AttributeError):
        g.test = 127

def test_ga_orig_class_writing_gives_typeerror():
    class A:
        def __new__(cls):
            return int

    g = GenericAlias(A, int)
    assert g() is int # does not crash

def test_ga_or_does_not_use_typing():
    union1 = int | float
    union2 = list[int] | float
    assert type(union1) is type(union2)

def test_ga_or():
    assert list[int] | float == UnionType((list[int], float))
    assert list[int] | None == UnionType((list[int], None))

def test_ga_ror():
    assert float | list[int] == UnionType((float, list[int]))
    assert None | list[int] == UnionType((None, list[int]))

def test_ga_subclass_repr():
    import types
    a = list[int]
    class SubClass(types.GenericAlias): ...
    d = SubClass(list, float)
    assert repr(a | d) == repr(a) + " | " + repr(d)

# union tests

def test_union_create():
    u = UnionType((int, list))
    assert u.__args__ == (int, list)
    u = UnionType((int, list, int))
    assert u.__args__ == (int, list) # deduplicate
    u = UnionType((int, UnionType((list, int, str, float))))
    assert u.__args__ == (int, list, str, float) # flatten

def test_union_forbidden_args():
    assert _create_union(1, int) is NotImplemented
    assert _create_union(int, 1) is NotImplemented

def test_union_with_itself():
    assert _create_union(int, int) is int

def test_union_hash_eq():
    u1 = UnionType((int, list))
    u2 = UnionType((int, list))
    u3 = UnionType((int, str))
    u4 = UnionType((list, int))
    assert u1 == u2
    assert u1 == u4
    assert u3 != u1
    assert u3 != u4

    assert hash(u1) == hash(u2)
    assert hash(u1) == hash(u4)
    assert hash(u3) != hash(u1)
    assert hash(u3) != hash(u4)

def test_union_isinstance():
    u = UnionType((int, list))
    assert isinstance(1, u)
    assert isinstance([], u)
    assert issubclass(int, u)
    assert issubclass(list, u)

    u2 = UnionType((int, None))
    assert isinstance(None, u2)
    assert isinstance(6, u2)
    assert issubclass(int, u2)
    assert issubclass(type(None), u2)

    with pytest.raises(TypeError):
        issubclass(int, UnionType((int, GenericAlias(dict, int))))
    with pytest.raises(TypeError):
        isinstance(2, UnionType((int, GenericAlias(dict, int))))

def test_union_repr():
    u = UnionType((int, list))
    assert repr(u) == "int | list"

def test_union_or():
    u = UnionType((int, list))
    assert u | int == UnionType((int, list))

def test_union_ror():
    assert None | int == UnionType((None, int))
    assert None | (int | float) == UnionType((None, int, float))

def test_union_parameters():
    assert (int | list[T]).__parameters__ == (T, )

def test_union_typevars():
    assert (float | list[T])[int] == float | list[int]

def test_union_type_none():
    assert int | type(None) == int | None

