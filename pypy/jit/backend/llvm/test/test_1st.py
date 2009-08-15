import py
from pypy.jit.metainterp.history import ResOperation, BoxInt, ConstInt,\
     BoxPtr, ConstPtr, TreeLoop
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.llvm.runner import LLVMCPU


def test_simple_case():
    v1 = BoxInt()
    v2 = BoxInt()
    v3 = BoxInt()
    v4 = BoxInt()
    loop = TreeLoop('test')
    loop.inputargs = [v1]
    loop.operations = [
        ResOperation(rop.INT_ADD, [v1, v1], v2),
        ResOperation(rop.INT_INVERT, [v2], v3),
        ResOperation(rop.UINT_RSHIFT, [v1, ConstInt(3)], v4),
        ResOperation(rop.FAIL, [v4, v3], None),
        ]
    cpu = LLVMCPU(None)
    cpu.setup_once()
    cpu.compile_operations(loop)
    cpu.set_future_value_int(0, 19)
    cpu.execute_operations(loop)
    assert cpu.get_latest_value_int(0) == (19 >> 3)
    assert cpu.get_latest_value_int(1) == (~38)

def test_loop_1():
    v1 = BoxInt(); v2 = BoxInt(); v3 = BoxInt()
    v4 = BoxInt(); v5 = BoxInt(); v6 = BoxInt()
    loop = TreeLoop('loop_1')
    loop.inputargs = [v1, v2, v3]
    loop.operations = [
        ResOperation(rop.INT_IS_TRUE, [v1], v4),
        ResOperation(rop.GUARD_TRUE, [v4], None),
        ResOperation(rop.INT_ADD, [v2, v3], v5),
        ResOperation(rop.INT_SUB, [v1, ConstInt(1)], v6),
        ResOperation(rop.JUMP, [v6, v2, v5], None),
        ]
    loop.operations[-1].jump_target = loop
    loop.operations[1].suboperations = [
        ResOperation(rop.FAIL, [v3], None),
        ]
    cpu = LLVMCPU(None)
    cpu.setup_once()
    cpu.compile_operations(loop)
    cpu.set_future_value_int(0, 2**11)
    cpu.set_future_value_int(1, 3)
    cpu.set_future_value_int(2, 0)
    cpu.execute_operations(loop)
    assert cpu.get_latest_value_int(0) == 3*(2**11)
    cpu.set_future_value_int(0, 2**29)
    cpu.set_future_value_int(1, 3)
    cpu.set_future_value_int(2, 0)
    cpu.execute_operations(loop)
    assert cpu.get_latest_value_int(0) == 3*(2**29)

def test_loop_2():
    cpu = LLVMCPU(None)
    cpu.setup_once()
    #
    v1 = BoxInt(); v2 = BoxInt()
    loop1 = TreeLoop('loop1')
    loop1.inputargs = [v1]
    loop1.operations = [
        ResOperation(rop.INT_ADD, [ConstInt(1), v1], v2),
        ResOperation(rop.FAIL, [v2], None),
        ]
    cpu.compile_operations(loop1)
    #
    cpu.set_future_value_int(0, 123)
    cpu.execute_operations(loop1)
    assert cpu.get_latest_value_int(0) == 124
    #
    v3 = BoxInt(); v4 = BoxInt(); v5 = BoxInt()
    loop2 = TreeLoop('loop2')
    loop2.inputargs = [v3, v4]
    loop2.operations = [
        ResOperation(rop.INT_SUB, [v3, v4], v5),
        ResOperation(rop.JUMP, [v5], None),
        ]
    loop2.operations[-1].jump_target = loop1
    cpu.compile_operations(loop2)
    #
    cpu.set_future_value_int(0, 1500)
    cpu.set_future_value_int(1, 60)
    cpu.execute_operations(loop2)
    assert cpu.get_latest_value_int(0) == 1441
    #
    # Now try to change the definition of loop1...
    loop1.operations = [
        ResOperation(rop.INT_ADD, [ConstInt(3), v1], v2),
        ResOperation(rop.FAIL, [v2], None),
        ]
    cpu.compile_operations(loop1)
    #
    cpu.set_future_value_int(0, 1500)
    cpu.set_future_value_int(1, 60)
    cpu.execute_operations(loop2)
    assert cpu.get_latest_value_int(0) == 1443    # should see the change

def test_descrof():
    cpu = LLVMCPU(None)
    # just to check that we can call them before setup_once():
    from pypy.rpython.lltypesystem import lltype, rclass
    cpu.sizeof(rclass.OBJECT)
    cpu.fielddescrof(rclass.OBJECT, 'typeptr')
    cpu.arraydescrof(lltype.GcArray(lltype.Signed))
    cpu.calldescrof(lltype.FuncType([], lltype.Signed), (), lltype.Signed)

def test_debug_merge_point():
    loop = TreeLoop('test')
    loop.inputargs = []
    loop.operations = [
        ResOperation(rop.DEBUG_MERGE_POINT, [], None),
        ResOperation(rop.FAIL, [], None),
        ]
    cpu = LLVMCPU(None)
    cpu.setup_once()
    cpu.compile_operations(loop)
    cpu.execute_operations(loop)
