import autopath
from pypy.rpython.lltypes import *
from pypy.translator.c.database import LowLevelDatabase
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypes import Struct, Array, malloc



def test_primitive():
    db = LowLevelDatabase()
    assert db.get(5) == '5'
    assert db.get(True) == '1'

def test_struct():
    db = LowLevelDatabase()
    S = Struct('test', ('x', Signed))
    s = malloc(S)
    s.x = 42
    assert db.get(s).startswith('&g_')
    assert db.containernodes.keys() == [s]
    assert db.structdefnodes.keys() == [S]

def test_inlined_struct():
    db = LowLevelDatabase()
    S = Struct('test', ('x', Struct('subtest', ('y', Signed))))
    s = malloc(S)
    s.x.y = 42
    assert db.get(s).startswith('&g_')
    assert db.containernodes.keys() == [s]
    assert len(db.structdefnodes) == 2
    assert S in db.structdefnodes
    assert S.x in db.structdefnodes

def test_complete():
    db = LowLevelDatabase()
    T = Struct('subtest', ('y', Signed))
    S = Struct('test', ('x', GcPtr(T)))
    s = malloc(S)
    s.x = malloc(T)
    s.x.y = 42
    assert db.get(s).startswith('&g_')
    assert db.containernodes.keys() == [s]
    db.complete()
    assert len(db.containernodes) == 2
    assert s in db.containernodes
    assert s.x in db.containernodes
    assert len(db.structdefnodes) == 2
    assert S in db.structdefnodes
    assert S.x.TO in db.structdefnodes
