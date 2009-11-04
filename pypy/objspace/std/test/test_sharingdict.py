import py
from pypy.conftest import gettestobjspace
from pypy.objspace.std.sharingdict import SharedStructure, NUM_DIGITS, SharedDictImplementation
from pypy.interpreter import gateway
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace

def instance_with_keys(structure, *keys):
    for key in keys:
        structure = structure.get_next_structure(key)
    return structure

def test_size_estimate():
    empty_structure = SharedStructure()
    instances = []
    for i in range(100):
        instances.append(instance_with_keys(empty_structure, "a", "b", "c", "d", "e", "f"))
        instances.append(instance_with_keys(empty_structure, "x", "y"))
    assert empty_structure.size_estimate() == 4
    assert empty_structure.other_structs.get("a").size_estimate() == 6
    assert empty_structure.other_structs.get("x").size_estimate() == 2

def test_size_estimate2():
    empty_structure = SharedStructure()
    instances = []
    for i in range(100):
        instances.append(instance_with_keys(empty_structure, "a", "b", "c", "d", "e", "f"))
        instances.append(instance_with_keys(empty_structure, "x", "y"))
        instances.append(instance_with_keys(empty_structure, "x", "y"))
    assert empty_structure.size_estimate() == 3
    assert empty_structure.other_structs.get("a").size_estimate() == 6
    assert empty_structure.other_structs.get("x").size_estimate() == 2

def test_delete():
    space = FakeSpace()
    d = SharedDictImplementation(space)
    d.setitem_str("a", 1)
    d.setitem_str("b", 2)
    d.setitem_str("c", 3)
    d.delitem("b")
    assert d.r_dict_content is None
    assert d.entries == [1, 3, None]
    assert d.structure.keys == {"a": 0, "c": 1}
    assert d.getitem("a") == 1
    assert d.getitem("c") == 3
    assert d.getitem("b") is None
    py.test.raises(KeyError, d.delitem, "b")

    d.delitem("c")
    assert d.entries == [1, None, None]
    assert d.structure.keys == {"a": 0}

    d.delitem("a")
    assert d.entries == [None, None, None]
    assert d.structure.keys == {}

    d = SharedDictImplementation(space)
    d.setitem_str("a", 1)
    d.setitem_str("b", 2)
    d.setitem_str("c", 3)
    d.setitem_str("d", 4)
    d.setitem_str("e", 5)
    d.setitem_str("f", 6)
    d.setitem_str("g", 7)
    d.setitem_str("h", 8)
    d.setitem_str("i", 9)
    d.delitem("d")
    assert d.entries == [1, 2, 3, 5, 6, 7, 8, 9, None]
    assert d.structure.keys == {"a": 0, "b": 1, "c": 2, "e": 3, "f": 4, "g": 5, "h": 6, "i": 7}
