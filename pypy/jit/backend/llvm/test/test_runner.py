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
    py.test.skip("fails because tail-recursion is not handled yet")
    cpu.set_future_value_int(0, 2**29)
    cpu.set_future_value_int(1, 3)
    cpu.set_future_value_int(2, 0)
    cpu.execute_operations(loop)
    assert cpu.get_latest_value_int(0) == 3*(2**29)
