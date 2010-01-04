import py
import sys, random
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.jit.metainterp.executor import make_execute_list, execute
from pypy.jit.metainterp.executor import execute_varargs, execute_nonspec
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import BoxInt, ConstInt
from pypy.jit.metainterp.history import BoxFloat, ConstFloat
from pypy.jit.metainterp.history import AbstractDescr, Box
from pypy.jit.backend.model import AbstractCPU


class FakeDescr(AbstractDescr):
    pass

class FakeBox(Box):
    def __init__(self, *args):
        self.args = args

class FakeCPU(AbstractCPU):
    supports_floats = True

    def do_new(self, descr):
        return FakeBox('new', descr)

    def do_arraylen_gc(self, box1, descr):
        return FakeBox('arraylen_gc', box1, descr)

    def do_setfield_gc(self, box1, box2, descr):
        return FakeBox('setfield_gc', box1, box2, descr)

    def do_setarrayitem_gc(self, box1, box2, box3, descr):
        return FakeBox('setarrayitem_gc', box1, box2, box3, descr)

    def do_call(self, args, descr):
        return FakeBox('call', args, descr)

    def do_strsetitem(self, box1, box2, box3):
        return FakeBox('strsetitem', box1, box2, box3)

make_execute_list(FakeCPU)


def test_execute():
    cpu = FakeCPU()
    descr = FakeDescr()
    box = execute(cpu, rop.INT_ADD, None, BoxInt(40), ConstInt(2))
    assert box.value == 42
    box = execute(cpu, rop.NEW, descr)
    assert box.args == ('new', descr)

def test_execute_varargs():
    cpu = FakeCPU()
    descr = FakeDescr()
    argboxes = [BoxInt(321), ConstInt(123)]
    box = execute_varargs(cpu, rop.CALL, argboxes, descr)
    assert box.args == ('call', argboxes, descr)

def test_execute_nonspec():
    cpu = FakeCPU()
    descr = FakeDescr()
    # cases with a descr
    # arity == -1
    argboxes = [BoxInt(321), ConstInt(123)]
    box = execute_nonspec(cpu, rop.CALL, argboxes, descr)
    assert box.args == ('call', argboxes, descr)
    # arity == 0
    box = execute_nonspec(cpu, rop.NEW, [], descr)
    assert box.args == ('new', descr)
    # arity == 1
    box1 = BoxInt(515)
    box = execute_nonspec(cpu, rop.ARRAYLEN_GC, [box1], descr)
    assert box.args == ('arraylen_gc', box1, descr)
    # arity == 2
    box2 = BoxInt(222)
    box = execute_nonspec(cpu, rop.SETFIELD_GC, [box1, box2], descr)
    assert box.args == ('setfield_gc', box1, box2, descr)
    # arity == 3
    box3 = BoxInt(-33)
    box = execute_nonspec(cpu, rop.SETARRAYITEM_GC, [box1, box2, box3], descr)
    assert box.args == ('setarrayitem_gc', box1, box2, box3, descr)
    # cases without descr
    # arity == 1
    box = execute_nonspec(cpu, rop.INT_INVERT, [box1])
    assert box.value == ~515
    # arity == 2
    box = execute_nonspec(cpu, rop.INT_LSHIFT, [box1, BoxInt(3)])
    assert box.value == 515 << 3
    # arity == 3
    box = execute_nonspec(cpu, rop.STRSETITEM, [box1, box2, box3])
    assert box.args == ('strsetitem', box1, box2, box3)

# ints

def _int_binary_operations():
    minint = -sys.maxint-1
    # Test cases.  Note that for each operation there should be at least
    # one case in which the two input arguments are equal.
    for opnum, testcases in [
        (rop.INT_ADD, [(10, -2, 8),
                       (-60, -60, -120)]),
        (rop.INT_SUB, [(10, -2, 12),
                       (133, 133, 0)]),
        (rop.INT_MUL, [(-6, -3, 18),
                       (15, 15, 225)]),
        (rop.INT_FLOORDIV, [(110, 3, 36),
                            (-110, 3, -36),
                            (110, -3, -36),
                            (-110, -3, 36),
                            (-110, -1, 110),
                            (minint, 1, minint),
                            (-87, -87, 1)]),
        (rop.INT_MOD, [(11, 3, 2),
                       (-11, 3, -2),
                       (11, -3, 2),
                       (-11, -3, -2),
                       (-87, -87, 0)]),
        (rop.INT_AND, [(0xFF00, 0x0FF0, 0x0F00),
                       (-111, -111, -111)]),
        (rop.INT_OR, [(0xFF00, 0x0FF0, 0xFFF0),
                      (-111, -111, -111)]),
        (rop.INT_XOR, [(0xFF00, 0x0FF0, 0xF0F0),
                       (-111, -111, 0)]),
        (rop.INT_LSHIFT, [(10, 4, 10<<4),
                          (-5, 2, -20),
                          (-5, 0, -5),
                          (3, 3, 24)]),
        (rop.INT_RSHIFT, [(-17, 2, -5),
                          (19, 1, 9),
                          (3, 3, 0)]),
        (rop.UINT_RSHIFT, [(-1, 4, intmask(r_uint(-1) >> r_uint(4))),
                           ( 1, 4, intmask(r_uint(1) >> r_uint(4))),
                           ( 3, 3, 0)])
        ]:
        for x, y, z in testcases:
            yield opnum, [x, y], z

def _int_comparison_operations():
    cpu = FakeCPU()            
    random_numbers = [-sys.maxint-1, -1, 0, 1, sys.maxint]
    def pick():
        r = random.randrange(-99999, 100000)
        if r & 1:
            return r
        else:
            return random_numbers[r % len(random_numbers)]
    minint = -sys.maxint-1
    for opnum, operation in [
        (rop.INT_LT, lambda x, y: x <  y),
        (rop.INT_LE, lambda x, y: x <= y),
        (rop.INT_EQ, lambda x, y: x == y),
        (rop.INT_NE, lambda x, y: x != y),
        (rop.INT_GT, lambda x, y: x >  y),
        (rop.INT_GE, lambda x, y: x >= y),
        (rop.UINT_LT, lambda x, y: r_uint(x) <  r_uint(y)),
        (rop.UINT_LE, lambda x, y: r_uint(x) <= r_uint(y)),
        (rop.UINT_GT, lambda x, y: r_uint(x) >  r_uint(y)),
        (rop.UINT_GE, lambda x, y: r_uint(x) >= r_uint(y)),
        ]:
        for i in range(20):
            x = pick()
            if i == 1:      # there should be at least one case
                y = x       # where the two arguments are equal
            else:
                y = pick()
            z = int(operation(x, y))
            yield opnum, [x, y], z

def _int_unary_operations():
    minint = -sys.maxint-1
    for opnum, testcases in [
        (rop.INT_IS_TRUE, [(0, 0), (1, 1), (2, 1), (-1, 1), (minint, 1)]),
        (rop.INT_NEG, [(0, 0), (123, -123), (-23127, 23127)]),
        (rop.INT_INVERT, [(0, ~0), (-1, ~(-1)), (123, ~123)]),
        (rop.BOOL_NOT, [(0, 1), (1, 0)]),
        ]:
        for x, y in testcases:
            yield opnum, [x], y

def get_int_tests():
    for opnum, args, retvalue in (
            list(_int_binary_operations()) +
            list(_int_comparison_operations()) +
            list(_int_unary_operations())):
        yield opnum, [BoxInt(x) for x in args], retvalue
        if len(args) > 1:
            assert len(args) == 2
            yield opnum, [BoxInt(args[0]), ConstInt(args[1])], retvalue
            yield opnum, [ConstInt(args[0]), BoxInt(args[1])], retvalue
            if args[0] == args[1]:
                commonbox = BoxInt(args[0])
                yield opnum, [commonbox, commonbox], retvalue


def test_int_ops():
    cpu = FakeCPU()
    for opnum, boxargs, retvalue in get_int_tests():
        box = execute_nonspec(cpu, opnum, boxargs)
        assert box.getint() == retvalue

# floats

def _float_binary_operations():
    # Test cases.  Note that for each operation there should be at least
    # one case in which the two input arguments are equal.
    for opnum, testcases in [
        (rop.FLOAT_ADD, [(10.5, -2.25, 8.25),
                         (5.25, 5.25, 10.5)]),
        (rop.FLOAT_SUB, [(10.5, -2.25, 12.75),
                         (5.25, 5.25, 0.0)]),
        (rop.FLOAT_MUL, [(-6.5, -3.5, 22.75),
                         (1.5, 1.5, 2.25)]),
        (rop.FLOAT_TRUEDIV, [(118.75, 12.5, 9.5),
                             (-6.5, -6.5, 1.0)]),
        ]:
        for x, y, z in testcases:
            yield (opnum, [x, y], 'float', z)

def _float_comparison_operations():
    # Test cases.  Note that for each operation there should be at least
    # one case in which the two input arguments are equal.
    for y in [-522.25, 10.125, 22.6]:
        yield (rop.FLOAT_LT, [10.125, y], 'int', 10.125 < y)
        yield (rop.FLOAT_LE, [10.125, y], 'int', 10.125 <= y)
        yield (rop.FLOAT_EQ, [10.125, y], 'int', 10.125 == y)
        yield (rop.FLOAT_NE, [10.125, y], 'int', 10.125 != y)
        yield (rop.FLOAT_GT, [10.125, y], 'int', 10.125 > y)
        yield (rop.FLOAT_GE, [10.125, y], 'int', 10.125 >= y)
    yield (rop.FLOAT_EQ, [0.0, -0.0], 'int', 0.0 == -0.0)

def _float_unary_operations():
    yield (rop.FLOAT_NEG, [-5.9], 'float', 5.9)
    yield (rop.FLOAT_NEG, [15.9], 'float', -15.9)
    yield (rop.FLOAT_ABS, [-5.9], 'float', 5.9)
    yield (rop.FLOAT_ABS, [15.9], 'float', 15.9)
    yield (rop.FLOAT_IS_TRUE, [-5.9], 'int', 1)
    yield (rop.FLOAT_IS_TRUE, [0.0], 'int', 0)
    yield (rop.FLOAT_IS_TRUE, [-0.0], 'int', 0)
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
        if len(args) > 1:
            assert len(args) == 2
            yield opnum, [boxargs[0], boxargs[1].constbox()], rettype, retvalue
            yield opnum, [boxargs[0].constbox(), boxargs[1]], rettype, retvalue
            if (isinstance(args[0], float) and
                isinstance(args[1], float) and
                args[0] == args[1]):
                commonbox = BoxFloat(args[0])
                yield opnum, [commonbox, commonbox], rettype, retvalue

def test_float_ops():
    cpu = FakeCPU()
    for opnum, boxargs, rettype, retvalue in get_float_tests(cpu):
        box = execute_nonspec(cpu, opnum, boxargs)
        if rettype == 'float':
            assert box.getfloat() == retvalue
        elif rettype == 'int':
            assert box.getint() == retvalue
        else:
            assert 0, "rettype is %r" % (rettype,)
