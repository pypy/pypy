from pypy.conftest import gettestobjspace
from pypy.objspace.std.sharingdict import SharedStructure, NUM_DIGITS
from pypy.interpreter import gateway

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
