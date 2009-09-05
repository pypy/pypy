from pypy.jit.metainterp.executor import make_execute_list, execute
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import BoxInt, ConstInt
from pypy.jit.metainterp.history import BoxFloat, ConstFloat
from pypy.jit.backend.model import AbstractCPU


class FakeCPU(AbstractCPU):
    pass
make_execute_list(FakeCPU)


def test_int_ops():
    box = execute(FakeCPU(), rop.INT_ADD, [BoxInt(40), ConstInt(2)])
    assert box.value == 42

def test_float_ops():
    cpu = FakeCPU()
    box = execute(cpu, rop.FLOAT_ADD, [BoxFloat(40.5), ConstFloat(2.25)])
    assert box.value == 42.75
    box = execute(cpu, rop.FLOAT_SUB, [BoxFloat(40.5), ConstFloat(2.25)])
    assert box.value == 38.25
    box = execute(cpu, rop.FLOAT_MUL, [BoxFloat(40.5), ConstFloat(2.25)])
    assert box.value == 91.125
    box = execute(cpu, rop.FLOAT_TRUEDIV, [BoxFloat(10.125), ConstFloat(2.25)])
    assert box.value == 4.5
