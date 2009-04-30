import py, sys
from pypy.rlib.rarithmetic import intmask, LONG_BIT
from pypy.jit.backend.test import conftest as demo_conftest
from pypy.jit.metainterp.history import TreeLoop, BoxInt, ConstInt
from pypy.jit.metainterp.history import BoxPtr, ConstPtr, ConstAddr
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.executor import execute


class OperationBuilder:
    def __init__(self, cpu, loop, vars):
        self.cpu = cpu
        self.loop = loop
        self.intvars = vars
        self.boolvars = []   # subset of self.intvars
        self.ptrvars = []
        self.prebuilt_ptr_consts = []
        self.should_fail_by = None
        self.counter = 0

    def do(self, opnum, argboxes, descr=None):
        v_result = execute(self.cpu, opnum, argboxes, descr)
        if isinstance(v_result, ConstInt):
            v_result = BoxInt(v_result.value)
        self.loop.operations.append(ResOperation(opnum, argboxes, v_result,
                                                 descr))
        return v_result

    def get_bool_var(self, r):
        if self.boolvars and r.random() < 0.8:
            v = r.choice(self.boolvars)
        elif self.ptrvars and r.random() < 0.4:
            v, S = r.choice(self.ptrvars)
            if r.random() < 0.5:
                v = self.do(rop.OONONNULL, [v])
            else:
                v = self.do(rop.OOISNULL, [v])
        else:
            v = r.choice(self.intvars)
            v = self.do(rop.INT_IS_TRUE, [v])
        return v

    def print_loop_prebuilt(self, names, writevar, s):
        pass

    def print_loop(self):
        if demo_conftest.option.output:
            s = open(demo_conftest.option.output, "w")
        else:
            s = sys.stdout
        names = {None: 'None'}
        #
        def writevar(v, nameprefix, init=''):
            names[v] = '%s%d' % (nameprefix, len(names))
            print >>s, '    %s = %s(%s)' % (names[v], v.__class__.__name__,
                                            init)
        #
        for v in self.intvars:
            writevar(v, 'v')
        for v, S in self.ptrvars:
            writevar(v, 'p')
        for op in self.loop.operations:
            v = op.result
            if v not in names:
                writevar(v, 'tmp')
        #
        self.print_loop_prebuilt(names, writevar, s)
        #
        print >>s, '    cpu = CPU(None, None)'
        print >>s, "    loop = TreeLoop('test')"
        print >>s, '    loop.inputargs = [%s]' % (
            ', '.join([names[v] for v in self.loop.inputargs]))
        from pypy.jit.metainterp.resoperation import opname
        print >>s, '    loop.operations = ['
        for op in self.loop.operations:
            args = []
            for v in op.args:
                if v in names:
                    args.append(names[v])
                elif isinstance(v, ConstAddr):
                    name = ''.join([v.value.ptr.name[i]
                                    for i in range(len(v.value.ptr.name)-1)])
                    args.append(
                        'ConstAddr(llmemory.cast_ptr_to_adr(%s_vtable), cpu)'
                        % name)
                else:
                    args.append('ConstInt(%d)' % v.value)
            if op.descr is None:
                descrstr = ''
            else:
                descrstr = ', ' + op.descr._random_info
            print >>s, '        ResOperation(rop.%s, [%s], %s%s),' % (
                opname[op.opnum], ', '.join(args), names[op.result], descrstr)
        print >>s, '        ]'
        for i, op in enumerate(self.loop.operations):
            if getattr(op, 'suboperations', None) is not None:
                [op] = op.suboperations
                assert op.opnum == rop.FAIL
                print >>s, '    loop.operations[%d].suboperations = [' % i
                print >>s, '        ResOperation(rop.FAIL, [%s], None)]' % (
                    ', '.join([names[v] for v in op.args]))
        print >>s, '    cpu.compile_operations(loop)'
        for i, v in enumerate(self.loop.inputargs):
            print >>s, '    cpu.set_future_value_int(%d, %d)' % (i, v.value)
        print >>s, '    op = cpu.execute_operations(loop)'
        if self.should_fail_by is None:
            for i, v in enumerate(self.loop.operations[-1].args):
                print >>s, '    assert cpu.get_latest_value_int(%d) == %d' % (
                    i, v.value)
        else:
            print >>s, '    assert op is loop.operations[%d].suboperations[0]' % self.should_fail_by_num
            for i, v in enumerate(self.should_fail_by.args):
                print >>s, '    assert cpu.get_latest_value_int(%d) == %d' % (
                    i, v.value)
        self.names = names
        if demo_conftest.option.output:
            s.close()

class CannotProduceOperation(Exception):
    pass

class AbstractOperation:
    def __init__(self, opnum, boolres=False):
        self.opnum = opnum
        self.boolres = boolres
    def put(self, builder, args, descr=None):
        v_result = builder.do(self.opnum, args, descr=descr)
        builder.intvars.append(v_result)
        if self.boolres:
            builder.boolvars.append(v_result)

class UnaryOperation(AbstractOperation):
    def produce_into(self, builder, r):
        self.put(builder, [r.choice(builder.intvars)])

class BooleanUnaryOperation(UnaryOperation):
    def produce_into(self, builder, r):
        v = builder.get_bool_var(r)
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
            v_first = r.choice(builder.intvars)
        if k > 0.75:
            value = r.random_integer()
            v_second = ConstInt((value & self.and_mask) | self.or_mask)
        else:
            v = r.choice(builder.intvars)
            if (v.value & self.and_mask) != v.value:
                v = builder.do(rop.INT_AND, [v, ConstInt(self.and_mask)])
            if (v.value | self.or_mask) != v.value:
                v = builder.do(rop.INT_OR, [v, ConstInt(self.or_mask)])
            v_second = v
        self.put(builder, [v_first, v_second])

class GuardOperation(AbstractOperation):
    def gen_guard(self, builder, r):
        v = builder.get_bool_var(r)
        op = ResOperation(self.opnum, [v], None)
        passing = ((self.opnum == rop.GUARD_TRUE and v.value) or
                   (self.opnum == rop.GUARD_FALSE and not v.value))
        return op, passing

    def produce_into(self, builder, r):
        op, passing = self.gen_guard(builder, r)
        builder.loop.operations.append(op)
        k = r.random()
        subset = []
        num = int(k * len(builder.intvars))
        for i in range(num):
            subset.append(r.choice(builder.intvars))
        r.shuffle(subset)
        op.suboperations = [ResOperation(rop.FAIL, subset, None)]
        if not passing:
            builder.should_fail_by = op.suboperations[0]
            builder.should_fail_by_num = len(builder.loop.operations) - 1

# ____________________________________________________________

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

OPERATIONS.append(BinaryOperation(rop.INT_FLOORDIV, ~3, 2))
OPERATIONS.append(BinaryOperation(rop.INT_MOD, ~3, 2))
OPERATIONS.append(BinaryOperation(rop.INT_RSHIFT, LONG_BIT-1))
OPERATIONS.append(BinaryOperation(rop.INT_LSHIFT, LONG_BIT-1))
OPERATIONS.append(BinaryOperation(rop.UINT_RSHIFT, LONG_BIT-1))

OPERATIONS.append(GuardOperation(rop.GUARD_TRUE))
OPERATIONS.append(GuardOperation(rop.GUARD_FALSE))

for _op in [rop.INT_NEG,
            rop.INT_INVERT,
            rop.INT_ABS,
            ]:
    OPERATIONS.append(UnaryOperation(_op))

OPERATIONS.append(UnaryOperation(rop.INT_IS_TRUE, boolres=True))
OPERATIONS.append(BooleanUnaryOperation(rop.BOOL_NOT, boolres=True))

OperationBuilder.OPERATIONS = OPERATIONS

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
            result = int(r.expovariate(0.05))
            if result <= sys.maxint:
                break
        if r.randrange(0, 5) <= 1:
            result = -result
        if result not in (0, -1) and r.random() < 0.1:
            # occasionally produce a very large integer.  The algo is such
            # that it's likely we get a special value, e.g. sys.maxint or
            # -sys.maxint-1.
            while intmask(result << 2) == (result << 2):
                result = (result << 2) | (result & 0x3)
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

def check_random_function(BuilderClass, r):
    block_length = demo_conftest.option.block_length
    vars = [BoxInt(r.random_integer())
            for i in range(demo_conftest.option.n_vars)]
    valueboxes = [BoxInt(box.value) for box in vars]

    cpu = get_cpu()
    loop = TreeLoop('test_random_function')
    loop.inputargs = vars[:]
    loop.operations = []

    builder = BuilderClass(cpu, loop, vars)

    for i in range(block_length):
        try:
            r.choice(BuilderClass.OPERATIONS).produce_into(builder, r)
        except CannotProduceOperation:
            pass
        if builder.should_fail_by is not None:
            break

    endvars = []
    used_later = {}
    for op in loop.operations:
        for v in op.args:
            used_later[v] = True
    for v in vars:
        if v not in used_later:
            endvars.append(v)
    r.shuffle(endvars)
    loop.operations.append(ResOperation(rop.FAIL, endvars, None))
    builder.print_loop()

    cpu.compile_operations(loop)

    if builder.should_fail_by is not None:
        endvars = builder.should_fail_by.args
    expected = {}
    for v in endvars:
        expected[v] = v.value

    for v, S, fields in builder.prebuilt_ptr_consts:
        container = v.value._obj.container
        for name, value in fields.items():
            setattr(container, name, value)

    for i, v in enumerate(valueboxes):
        cpu.set_future_value_int(i, v.value)
    op = cpu.execute_operations(loop)
    assert op.args == endvars

    for i, v in enumerate(endvars):
        value = cpu.get_latest_value_int(i)
        assert value == expected[v], (
            "Got %d, expected %d, in the variable %s" % (value,
                                                         expected[v],
                                                         builder.names[v])
            )

    print '    # passed.'
    print


def test_random_function(BuilderClass=OperationBuilder):
    r = Random()
    if demo_conftest.option.repeat == -1:
        while 1: 
            check_random_function(BuilderClass, r)
    else:
        for i in range(demo_conftest.option.repeat):
            check_random_function(BuilderClass, r)
