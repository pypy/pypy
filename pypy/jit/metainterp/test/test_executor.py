import py
from pypy.jit.metainterp.executor import make_execute_list, execute
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import BoxInt, ConstInt
from pypy.jit.metainterp.history import BoxFloat, ConstFloat
from pypy.jit.backend.model import AbstractCPU


class FakeCPU(AbstractCPU):
    supports_floats = True
make_execute_list(FakeCPU)


def test_int_ops():
    box = execute(FakeCPU(), rop.INT_ADD, [BoxInt(40), ConstInt(2)])
    assert box.value == 42

def _float_binary_operations():
    for opnum, testcases in [
        (rop.FLOAT_ADD, [(10.5, -2.25, 8.25)]),
        (rop.FLOAT_SUB, [(10.5, -2.25, 12.75)]),
        (rop.FLOAT_MUL, [(-6.5, -3.5, 22.75)]),
        (rop.FLOAT_TRUEDIV, [(118.75, 12.5, 9.5)]),
        ]:
        for x, y, z in testcases:
            yield (opnum, [x, y], 'float', z)

def _float_comparison_operations():
    for y in [-522.25, 10.125, 22.6]:
        yield (rop.FLOAT_LT, [10.125, y], 'int', 10.125 < y)
        yield (rop.FLOAT_LE, [10.125, y], 'int', 10.125 <= y)
        yield (rop.FLOAT_EQ, [10.125, y], 'int', 10.125 == y)
        yield (rop.FLOAT_NE, [10.125, y], 'int', 10.125 != y)
        yield (rop.FLOAT_GT, [10.125, y], 'int', 10.125 > y)
        yield (rop.FLOAT_GE, [10.125, y], 'int', 10.125 >= y)

def _float_unary_operations():
    yield (rop.FLOAT_NEG, [-5.9], 'float', 5.9)
    yield (rop.FLOAT_NEG, [15.9], 'float', -15.9)
    yield (rop.FLOAT_ABS, [-5.9], 'float', 5.9)
    yield (rop.FLOAT_ABS, [15.9], 'float', 15.9)
    yield (rop.FLOAT_IS_TRUE, [-5.9], 'int', 1)
    yield (rop.FLOAT_IS_TRUE, [0.0], 'int', 0)
    yield (rop.CAST_FLOAT_TO_INT, [-5.9], 'int', -5)
    yield (rop.CAST_FLOAT_TO_INT, [5.9], 'int', 5)
    yield (rop.CAST_INT_TO_FLOAT, [123], 'float', 123.0)

def get_float_tests(cpu):
    if not cpu.supports_floats:
        py.test.skip("requires float support from the backend")
    for opnum, args, rettype, retvalue in (
            list(_float_binary_operations()) +
            list(_float_comparison_operations()) +
            list(_float_unary_operations())):
        boxargs = []
        for x in args:
            if isinstance(x, float):
                boxargs.append(BoxFloat(x))
            else:
                boxargs.append(BoxInt(x))
        yield opnum, boxargs, rettype, retvalue

def test_float_ops():
    cpu = FakeCPU()
    for opnum, boxargs, rettype, retvalue in get_float_tests(cpu):
        box = execute(cpu, opnum, boxargs)
        if rettype == 'float':
            assert box.getfloat() == retvalue
        elif rettype == 'int':
            assert box.getint() == retvalue
        else:
            assert retvalue is None
