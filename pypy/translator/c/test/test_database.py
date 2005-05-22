import autopath, sys
from pypy.rpython.lltypes import *
from pypy.translator.c.database import LowLevelDatabase
from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.objspace.flow.model import Block, Link, FunctionGraph
from pypy.rpython.lltypes import Struct, Array, malloc



def test_primitive():
    db = LowLevelDatabase()
    assert db.get(5) == '5'
    assert db.get(True) == '1'

def test_struct():
    db = LowLevelDatabase()
    S = GcStruct('test', ('x', Signed))
    s = malloc(S)
    s.x = 42
    assert db.get(s).startswith('&g_')
    assert db.containernodes.keys() == [s._obj]
    assert db.structdefnodes.keys() == [S]

def test_inlined_struct():
    db = LowLevelDatabase()
    S = GcStruct('test', ('x', Struct('subtest', ('y', Signed))))
    s = malloc(S)
    s.x.y = 42
    assert db.get(s).startswith('&g_')
    assert db.containernodes.keys() == [s._obj]
    assert len(db.structdefnodes) == 2
    assert S in db.structdefnodes
    assert S.x in db.structdefnodes

def test_complete():
    db = LowLevelDatabase()
    T = GcStruct('subtest', ('y', Signed))
    S = GcStruct('test', ('x', GcPtr(T)))
    s = malloc(S)
    s.x = malloc(T)
    s.x.y = 42
    assert db.get(s).startswith('&g_')
    assert db.containernodes.keys() == [s._obj]
    db.complete()
    assert len(db.containernodes) == 2
    assert s._obj in db.containernodes
    assert s.x._obj in db.containernodes
    assert len(db.structdefnodes) == 2
    assert S in db.structdefnodes
    assert S.x.TO in db.structdefnodes

def test_codegen():
    db = LowLevelDatabase()
    U = Struct('inlined', ('z', Signed))
    T = GcStruct('subtest', ('y', Signed))
    S = GcStruct('test', ('x', GcPtr(T)), ('u', U), ('p', NonGcPtr(U)))
    s = malloc(S)
    s.x = malloc(T)
    s.x.y = 42
    s.u.z = -100
    s.p = cast_flags(NonGcPtr(U), s.u)
    db.get(s)
    db.complete()
    db.write_all_declarations(sys.stdout)
    db.write_all_implementations(sys.stdout)

def test_codegen_2():
    db = LowLevelDatabase()
    A = GcArray(('x', Signed))
    S = GcStruct('test', ('aptr', GcPtr(A)))
    a = malloc(A, 3)
    a[0].x = 100
    a[1].x = 101
    a[2].x = 102
    s = malloc(S)
    s.aptr = a
    db.get(s)
    db.complete()
    db.write_all_declarations(sys.stdout)
    db.write_all_implementations(sys.stdout)

def test_codegen_3():
    db = LowLevelDatabase()
    A = GcStruct('varsizedstuff', ('x', Signed), ('y', Array(('i', Signed))))
    S = GcStruct('test', ('aptr', GcPtr(A)),
                         ('anitem', NonGcPtr(A.y.OF)),
                         ('anarray', NonGcPtr(A.y)))
    a = malloc(A, 3)
    a.x = 99
    a.y[0].i = 100
    a.y[1].i = 101
    a.y[2].i = 102
    s = malloc(S)
    s.aptr = a
    s.anitem = cast_flags(NonGcPtr(A.y.OF), a.y[1])
    s.anarray = cast_flags(NonGcPtr(A.y), a.y)
    db.get(s)
    db.complete()
    db.write_all_declarations(sys.stdout)
    db.write_all_implementations(sys.stdout)

def test_func_simple():
    # -------------------- flowgraph building --------------------
    #     def f(x):
    #         return x+1
    x = Variable("x")
    x.concretetype = Signed
    result = Variable("result")
    result.concretetype = Signed
    one = Constant(1)
    one.concretetype = Signed
    op = SpaceOperation("int_add", [x, one], result)
    block = Block([x])
    graph = FunctionGraph("f", block)
    block.operations.append(op)
    block.closeblock(Link([result], graph.returnblock))
    graph.getreturnvar().concretetype = Signed
    # --------------------         end        --------------------
    
    F = FuncType([Signed], Signed)
    f = function(F, "f", graph=graph)
    db = LowLevelDatabase()
    db.get(f)
    db.complete()
    db.write_all_declarations(sys.stdout)
    db.write_all_implementations(sys.stdout)

    S = GcStruct('testing', ('fptr', NonGcPtr(F)))
    s = malloc(S)
    s.fptr = f
    db = LowLevelDatabase()
    db.get(s)
    db.complete()
    db.write_all_declarations(sys.stdout)
    db.write_all_implementations(sys.stdout)
