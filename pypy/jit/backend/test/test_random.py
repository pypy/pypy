import py, sys, math
from pypy.rlib.rarithmetic import intmask, LONG_BIT
from pypy.jit.backend.test import conftest as demo_conftest
from pypy.jit.metainterp.history import TreeLoop, BoxInt, ConstInt
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.executor import execute


class OperationBuilder:
    def __init__(self, cpu, loop, vars):
        self.cpu = cpu
        self.loop = loop
        self.vars = vars
        self.boolvars = []   # subset of self.vars

    def do(self, opnum, argboxes):
        v_result = execute(self.cpu, opnum, argboxes)
        v_result = BoxInt(v_result.value)
        self.loop.operations.append(ResOperation(opnum, argboxes, v_result))
        return v_result

class AbstractOperation:
    def __init__(self, opnum, boolres=False):
        self.opnum = opnum
        self.boolres = boolres
    def put(self, builder, args):
        v_result = builder.do(self.opnum, args)
        builder.vars.append(v_result)
        if self.boolres:
            builder.boolvars.append(v_result)

class UnaryOperation(AbstractOperation):
    def produce_into(self, builder, r):
        self.put(builder, [r.choice(builder.vars)])

class BooleanUnaryOperation(UnaryOperation):
    def produce_into(self, builder, r):
        if builder.boolvars:
            v = r.choice(builder.boolvars)
        else:
            v = r.choice(builder.vars)
            v = builder.do(rop.INT_IS_TRUE, [v])
        self.put(builder, [v])

class BinaryOperation(AbstractOperation):
    def __init__(self, opnum, and_mask=-1, or_mask=0, boolres=False):
        AbstractOperation.__init__(self, opnum, boolres=boolres)
        self.and_mask = and_mask
        self.or_mask = or_mask
    def produce_into(self, builder, r):
        k = r.random()
        if k < 0.2:
            v_first = ConstInt(r.random_integer())
        else:
            v_first = r.choice(builder.vars)
        if k > 0.75:
            value = r.random_integer()
            v_second = ConstInt((value & self.and_mask) | self.or_mask)
        else:
            v = r.choice(builder.vars)
            if self.and_mask != 1:
                v = builder.do(rop.INT_AND, [v, ConstInt(self.and_mask)])
            if self.or_mask != 0:
                v = builder.do(rop.INT_OR, [v, ConstInt(self.or_mask)])
            v_second = v
        self.put(builder, [v_first, v_second])

OPERATIONS = []

for _op in [rop.INT_ADD,
            rop.INT_SUB,
            rop.INT_MUL,
            rop.INT_AND,
            rop.INT_OR,
            rop.INT_XOR,
            ]:
    OPERATIONS.append(BinaryOperation(_op))

for _op in [rop.INT_LT,
            rop.INT_LE,
            rop.INT_EQ,
            rop.INT_NE,
            rop.INT_GT,
            rop.INT_GE,
            rop.UINT_LT,
            rop.UINT_LE,
            rop.UINT_GT,
            rop.UINT_GE,
            ]:
    OPERATIONS.append(BinaryOperation(_op, boolres=True))

OPERATIONS.append(BinaryOperation(rop.INT_FLOORDIV, ~3, 1))
OPERATIONS.append(BinaryOperation(rop.INT_MOD, ~3, 1))
OPERATIONS.append(BinaryOperation(rop.INT_RSHIFT, LONG_BIT-1))
OPERATIONS.append(BinaryOperation(rop.INT_LSHIFT, LONG_BIT-1))
OPERATIONS.append(BinaryOperation(rop.UINT_RSHIFT, LONG_BIT-1))

for _op in [rop.INT_NEG,
            rop.INT_INVERT,
            rop.INT_ABS,
            ]:
    OPERATIONS.append(UnaryOperation(_op))

OPERATIONS.append(UnaryOperation(rop.INT_IS_TRUE, boolres=True))
OPERATIONS.append(BooleanUnaryOperation(rop.BOOL_NOT, boolres=True))

# ____________________________________________________________

def Random():
    import random
    seed = demo_conftest.option.randomseed
    print
    print 'Random seed value is %d.' % (seed,)
    print
    r = random.Random(seed)
    def get_random_integer():
        while True:
            result = int(random.expovariate(0.05))
            if result <= sys.maxint:
                break
        if random.randrange(0, 5) <= 1:
            result = -result
        return result
    r.random_integer = get_random_integer
    return r

def get_cpu():
    if demo_conftest.option.backend == 'llgraph':
        from pypy.jit.backend.llgraph.runner import LLtypeCPU
        return LLtypeCPU(None)
    elif demo_conftest.option.backend == 'minimal':
        from pypy.jit.backend.minimal.runner import CPU
        return CPU(None)
    elif demo_conftest.option.backend == 'x86':
        from pypy.jit.backend.x86.runner import CPU386
        return CPU386(None, None)
    else:
        assert 0, "unknown backend %r" % demo_conftest.option.backend

# ____________________________________________________________

def test_random_function():
    r = Random()
    block_length = demo_conftest.option.block_length
    vars = [BoxInt(r.random_integer())
            for i in range(demo_conftest.option.n_vars)]
    valueboxes = [BoxInt(box.value) for box in vars]

    cpu = get_cpu()
    loop = TreeLoop('test_random_function')
    loop.inputargs = vars[:]
    loop.operations = []

    builder = OperationBuilder(cpu, loop, vars)

    for i in range(block_length):
        r.choice(OPERATIONS).produce_into(builder, r)

    endvars = []
    for v in vars:
        for op in loop.operations:
            if v in op.args:
                break
        else:
            endvars.append(v)
    r.shuffle(endvars)
    loop.operations.append(ResOperation(rop.FAIL, endvars, None))

    cpu.compile_operations(loop)

    expected = {}
    for v in endvars:
        expected[v] = v.value
        v.changevalue_int(-sys.maxint-1)

    cpu.execute_operations(loop, valueboxes)

    for v in endvars:
        assert v.value == expected[v]
