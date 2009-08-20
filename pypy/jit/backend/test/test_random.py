import py, sys
from pypy.rlib.rarithmetic import intmask, LONG_BIT
from pypy.rpython.lltypesystem import llmemory
from pypy.jit.backend.test import conftest as demo_conftest
from pypy.jit.metainterp.history import TreeLoop, BoxInt, ConstInt
from pypy.jit.metainterp.history import BoxPtr, ConstPtr, ConstAddr
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.executor import execute
from pypy.jit.metainterp.resoperation import opname

class PleaseRewriteMe(Exception):
    pass

class DummyLoop(object):
    def __init__(self, subops):
        self.operations = subops

class OperationBuilder(object):
    def __init__(self, cpu, loop, vars):
        self.cpu = cpu
        self.loop = loop
        self.intvars = vars
        self.boolvars = []   # subset of self.intvars
        self.ptrvars = []
        self.prebuilt_ptr_consts = []
        self.should_fail_by = None
        self.counter = 0

    def fork(self, cpu, loop, vars):
        fork = self.__class__(cpu, loop, vars)
        fork.prebuilt_ptr_consts = self.prebuilt_ptr_consts
        return fork

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
            v, S = r.choice(self.ptrvars + self.prebuilt_ptr_consts)[:2]
            v2, S2 = r.choice(self.ptrvars + self.prebuilt_ptr_consts)[:2]
            if S == S2 and not (isinstance(v, ConstPtr) and
                                isinstance(v2, ConstPtr)):
                if r.random() < 0.5:
                    v = self.do(rop.OOIS, [v, v2])
                else:
                    v = self.do(rop.OOISNOT, [v, v2])
            else:
                if isinstance(v, ConstPtr):
                    v, S = r.choice(self.ptrvars)
                if r.random() < 0.5:
                    v = self.do(rop.OONONNULL, [v])
                else:
                    v = self.do(rop.OOISNULL, [v])
        else:
            v = r.choice(self.intvars)
            v = self.do(rop.INT_IS_TRUE, [v])
        return v

    def subset_of_intvars(self, r):
        subset = []
        k = r.random()
        num = int(k * len(self.intvars))
        for i in range(num):
            subset.append(r.choice(self.intvars))
        return subset

    def process_operation(self, s, op, names, subops):
        args = []
        for v in op.args:
            if v in names:
                args.append(names[v])
            elif isinstance(v, ConstAddr):
                try:
                    name = ''.join([v.value.ptr.name[i]
                                    for i in range(len(v.value.ptr.name)-1)])
                except AttributeError:
                    args.append('ConstAddr(...)')
                else:
                    args.append(
                        'ConstAddr(llmemory.cast_ptr_to_adr(%s_vtable), cpu)'
                        % name)
            else:
                args.append('ConstInt(%d)' % v.value)
        if op.descr is None:
            descrstr = ''
        else:
            try:
                descrstr = ', ' + op.descr._random_info
            except AttributeError:
                descrstr = ', descr=...'
        print >>s, '        ResOperation(rop.%s, [%s], %s%s),' % (
            opname[op.opnum], ', '.join(args), names[op.result], descrstr)
        if getattr(op, 'suboperations', None) is not None:
            subops.append(op)

    def print_loop(self):
        #raise PleaseRewriteMe()
        def update_names(ops):
            for op in ops:
                v = op.result
                if v not in names:
                    writevar(v, 'tmp')
                if getattr(op, 'suboperations', None) is not None:
                    update_names(op.suboperations)

        def print_loop_prebuilt(ops):
            for op in ops:
                for arg in op.args:
                    if isinstance(arg, ConstPtr):
                        if arg not in names:
                            writevar(arg, 'const_ptr')
                if getattr(op, 'suboperations', None) is not None:
                    print_loop_prebuilt(op.suboperations)

        if demo_conftest.option.output:
            s = open(demo_conftest.option.output, "w")
        else:
            s = sys.stdout
        names = {None: 'None'}
        subops = []
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
        update_names(self.loop.operations)
        print_loop_prebuilt(self.loop.operations)
        #
        print >>s, '    cpu = CPU(None, None)'
        print >>s, "    loop = TreeLoop('test')"
        if hasattr(self.loop, 'inputargs'):
            print >>s, '    loop.inputargs = [%s]' % (
                ', '.join([names[v] for v in self.loop.inputargs]))
        print >>s, '    loop.operations = ['
        for op in self.loop.operations:
            self.process_operation(s, op, names, subops)
        print >>s, '        ]'
        while subops:
            next = subops.pop(0)
            for op in next.suboperations:
                self.process_operation(s, op, names, subops)
        # XXX think what to do about the one below
                #if len(op.suboperations) > 1:
                #    continue # XXX
                #[op] = op.suboperations
                #assert op.opnum == rop.FAIL
                #print >>s, '    loop.operations[%d].suboperations = [' % i
                #print >>s, '        ResOperation(rop.FAIL, [%s], None)]' % (
                #    ', '.join([names[v] for v in op.args]))
        print >>s, '    cpu.compile_operations(loop)'
        if hasattr(self.loop, 'inputargs'):
            for i, v in enumerate(self.loop.inputargs):
                print >>s, '    cpu.set_future_value_int(%d, %d)' % (i,
                                                                     v.value)
        print >>s, '    op = cpu.execute_operations(loop)'
        if self.should_fail_by is None:
            for i, v in enumerate(self.loop.operations[-1].args):
                print >>s, '    assert cpu.get_latest_value_int(%d) == %d' % (
                    i, v.value)
        else:
            #print >>s, '    assert op is loop.operations[%d].suboperations[0]' % self.should_fail_by_num
            for i, v in enumerate(self.should_fail_by.args):
                print >>s, '    assert cpu.get_latest_value_int(%d) == %d' % (
                    i, v.value)
        self.names = names
        if demo_conftest.option.output:
            s.close()

class CannotProduceOperation(Exception):
    pass

class AbstractOperation(object):
    def __init__(self, opnum, boolres=False):
        self.opnum = opnum
        self.boolres = boolres
    def put(self, builder, args, descr=None):
        v_result = builder.do(self.opnum, args, descr=descr)
        if v_result is not None:
            builder.intvars.append(v_result)
            boolres = self.boolres
            if boolres == 'sometimes':
                boolres = v_result.value in [0, 1]
            if boolres:
                builder.boolvars.append(v_result)

class UnaryOperation(AbstractOperation):
    def produce_into(self, builder, r):
        self.put(builder, [r.choice(builder.intvars)])

class BooleanUnaryOperation(UnaryOperation):
    def produce_into(self, builder, r):
        v = builder.get_bool_var(r)
        self.put(builder, [v])

class ConstUnaryOperation(UnaryOperation):
    def produce_into(self, builder, r):
        self.put(builder, [ConstInt(r.random_integer())])

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

class AbstractOvfOperation(AbstractOperation):
    def produce_into(self, builder, r):
        fail_subset = builder.subset_of_intvars(r)
        original_intvars = builder.intvars[:]
        super(AbstractOvfOperation, self).produce_into(builder, r)
        if builder.cpu._overflow_flag:   # overflow detected
            del builder.cpu._overflow_flag
            op = ResOperation(rop.GUARD_OVERFLOW, [], None)
            # the overflowed result should not be used any more, but can
            # be used on the failure path: recompute fail_subset including
            # the result, and then remove it from builder.intvars.
            fail_subset = builder.subset_of_intvars(r)
            builder.intvars[:] = original_intvars
        else:
            op = ResOperation(rop.GUARD_NO_OVERFLOW, [], None)
        op.suboperations = [ResOperation(rop.FAIL, fail_subset, None)]
        builder.loop.operations.append(op)

class BinaryOvfOperation(AbstractOvfOperation, BinaryOperation):
    pass

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
        subset = builder.subset_of_intvars(r)        
        op.suboperations = [ResOperation(rop.FAIL, subset, None)]
        if not passing:
            builder.should_fail_by = op.suboperations[0]
            builder.guard_op = op

class GuardValueOperation(GuardOperation):
    def gen_guard(self, builder, r):
        v = r.choice(builder.intvars)
        if r.random() > 0.8:
            other = r.choice(builder.intvars)
        else:
            if r.random() < 0.75:
                value = v.value
            elif r.random() < 0.5:
                value = v.value ^ 1
            else:
                value = r.random_integer()
            other = ConstInt(value)
        op = ResOperation(self.opnum, [v, other], None)
        return op, (v.value == other.value)

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
OPERATIONS.append(GuardOperation(rop.GUARD_TRUE))
OPERATIONS.append(GuardOperation(rop.GUARD_FALSE))
OPERATIONS.append(GuardOperation(rop.GUARD_FALSE))
OPERATIONS.append(GuardValueOperation(rop.GUARD_VALUE))

for _op in [rop.INT_NEG,
            rop.INT_INVERT,
            ]:
    OPERATIONS.append(UnaryOperation(_op))

OPERATIONS.append(UnaryOperation(rop.INT_IS_TRUE, boolres=True))
OPERATIONS.append(BooleanUnaryOperation(rop.BOOL_NOT, boolres=True))
OPERATIONS.append(ConstUnaryOperation(rop.SAME_AS, boolres='sometimes'))

for _op in [rop.INT_ADD_OVF,
            rop.INT_SUB_OVF,
            rop.INT_MUL_OVF,
            ]:
    OPERATIONS.append(BinaryOvfOperation(_op))

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
    def get_random_char():
        return chr(get_random_integer() % 256)
    r.random_integer = get_random_integer
    r.random_char = get_random_char
    return r

def get_cpu():
    if demo_conftest.option.backend == 'llgraph':
        from pypy.jit.backend.llgraph.runner import LLtypeCPU
        return LLtypeCPU(None)
    elif demo_conftest.option.backend == 'x86':
        from pypy.jit.backend.x86.runner import CPU386
        return CPU386(None, None)
    else:
        assert 0, "unknown backend %r" % demo_conftest.option.backend

# ____________________________________________________________    

class RandomLoop(object):
    dont_generate_more = False
    
    def __init__(self, cpu, builder_factory, r, startvars=None):
        self.cpu = cpu
        if startvars is None:
            startvars = [BoxInt(r.random_integer())
                         for i in range(demo_conftest.option.n_vars)]
        self.startvars = startvars
        self.values = [var.value for var in startvars]
        self.prebuilt_ptr_consts = []
        self.r = r
        self.build_random_loop(cpu, builder_factory, r, startvars)
        
    def build_random_loop(self, cpu, builder_factory, r, startvars):

        loop = TreeLoop('test_random_function')
        loop.inputargs = startvars[:]
        loop.operations = []

        builder = builder_factory(cpu, loop, startvars[:])
        self.generate_ops(builder, r, loop, startvars)
        self.builder = builder
        cpu.compile_operations(loop)
        self.loop = loop

    def generate_ops(self, builder, r, loop, startvars):
        block_length = demo_conftest.option.block_length

        for i in range(block_length):
            try:
                r.choice(builder.OPERATIONS).produce_into(builder, r)
            except CannotProduceOperation:
                pass
            if builder.should_fail_by is not None:
                break
        endvars = []
        used_later = {}
        for op in loop.operations:
            for v in op.args:
                used_later[v] = True
        for v in startvars:
            if v not in used_later:
                endvars.append(v)
        r.shuffle(endvars)
        loop.operations.append(ResOperation(rop.FAIL, endvars, None))
        if builder.should_fail_by:
            self.should_fail_by = builder.should_fail_by
            self.guard_op = builder.guard_op
        else:
            self.should_fail_by = loop.operations[-1]
            self.guard_op = None
        self.prebuilt_ptr_consts.extend(builder.prebuilt_ptr_consts)
        endvars = self.should_fail_by.args
        self.expected = {}
        for v in endvars:
            self.expected[v] = v.value
        if demo_conftest.option.output:
            builder.print_loop()

    def clear_state(self):
        for v, S, fields in self.prebuilt_ptr_consts:
            container = v.value._obj.container
            for name, value in fields.items():
                if isinstance(name, str):
                    setattr(container, name, value)
                else:
                    container.setitem(name, value)

    def run_loop(self):
        cpu = self.builder.cpu
        self.clear_state()
        assert not cpu.get_exception()
        assert not cpu.get_exc_value()

        for i, v in enumerate(self.values):
            cpu.set_future_value_int(i, v)
        op = cpu.execute_operations(self.loop)
        assert op is self.should_fail_by
        for i, v in enumerate(op.args):
            value = cpu.get_latest_value_int(i)
            assert value == self.expected[v], (
                "Got %d, expected %d for value #%d" % (value,
                                                       self.expected[v],
                                                       i)
                )
        if (self.guard_op is not None and
            self.guard_op.is_guard_exception()):
            if self.guard_op.opnum == rop.GUARD_NO_EXCEPTION:
                assert cpu.get_exception()
                assert cpu.get_exc_value()
            cpu.clear_exception()
        else:
            assert not cpu.get_exception()
            assert not cpu.get_exc_value()

    def build_bridge(self):
        def exc_handling(guard_op):
            # operations need to start with correct GUARD_EXCEPTION
            if guard_op._exc_box is None:
                op = ResOperation(rop.GUARD_NO_EXCEPTION, [], None)
            else:
                op = ResOperation(rop.GUARD_EXCEPTION, [guard_op._exc_box],
                                  BoxPtr())
            op.suboperations = [ResOperation(rop.FAIL, [], None)]
            return op

        if self.dont_generate_more:
            return False
        r = self.r
        guard_op = self.guard_op
        guard_op.suboperations = []
        op = self.should_fail_by
        if not op.args:
            return False
        subloop = DummyLoop(guard_op.suboperations)
        if guard_op.is_guard_exception():
            guard_op.suboperations.append(exc_handling(guard_op))
        bridge_builder = self.builder.fork(self.builder.cpu, subloop,
                                           op.args[:])
        self.generate_ops(bridge_builder, r, subloop, op.args[:])
        if r.random() < 0.1:
            subset = bridge_builder.subset_of_intvars(r)
            if len(subset) == 0:
                return False
            args = [x.clonebox() for x in subset]
            jump_target = RandomLoop(self.builder.cpu, self.builder.fork,
                                     r, args)
            self.cpu.compile_operations(jump_target.loop)
            jump_op = ResOperation(rop.JUMP, subset, None)
            jump_op.jump_target = jump_target.loop
            self.should_fail_by = jump_target.should_fail_by
            self.expected = jump_target.expected
            if self.guard_op is None:
                guard_op.suboperations[-1] = jump_op
            else:
                if self.guard_op.is_guard_exception():
                    # exception clearing
                    self.guard_op.suboperations.insert(-1, exc_handling(
                        self.guard_op))
                self.guard_op.suboperations[-1] = jump_op
            self.guard_op = jump_target.guard_op
            self.prebuilt_ptr_consts += jump_target.prebuilt_ptr_consts
            self.dont_generate_more = True
        if r.random() < .05:
            return False
        self.builder.cpu.compile_operations(self.loop)
        return True

def check_random_function(cpu, BuilderClass, r, num=None, max=None):
    loop = RandomLoop(cpu, BuilderClass, r)
    while True:
        loop.run_loop()
        if loop.guard_op is not None:
            if not loop.build_bridge():
                break
        else:
            break
    if num is not None:
        print '    # passed (%d/%d).' % (num + 1, max)
    else:
        print '    # passed.'
    print

def test_random_function(BuilderClass=OperationBuilder):
    r = Random()
    cpu = get_cpu()
    if demo_conftest.option.repeat == -1:
        while 1:
            check_random_function(cpu, BuilderClass, r)
    else:
        for i in range(demo_conftest.option.repeat):
            check_random_function(cpu, BuilderClass, r, i,
                                  demo_conftest.option.repeat)
