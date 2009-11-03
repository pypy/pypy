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
