
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
