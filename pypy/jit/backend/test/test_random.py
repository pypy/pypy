import py, sys, math
from pypy.rlib.rarithmetic import intmask, LONG_BIT
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
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

    def get_structptr_var(self, r, must_have_vtable=False):
        while True:
            if self.ptrvars and r.random() < 0.8:
                v, S = r.choice(self.ptrvars)
            elif self.prebuilt_ptr_consts and r.random() < 0.7:
                v, S, _ = r.choice(self.prebuilt_ptr_consts)
            else:
                must_have_vtable = must_have_vtable or r.random() < 0.5
                p = self.get_random_structure(r, has_vtable=must_have_vtable)
                S = lltype.typeOf(p).TO
                v = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, p))
                self.prebuilt_ptr_consts.append((v, S, self.field_values(p)))
            if not (must_have_vtable and S._names[0] != 'parent'):
                break
        return v, S

    def get_random_structure_type(self, r, has_vtable=False):
        fields = []
        if has_vtable:
            fields.append(('parent', rclass.OBJECT))
        for i in range(r.randrange(1, 5)):
            fields.append(('f%d' % i, lltype.Signed))
        S = lltype.GcStruct('S%d' % self.counter, *fields)
        self.counter += 1
        return S

    def get_random_structure_type_and_vtable(self, r):
        S = self.get_random_structure_type(r, has_vtable=True)
        vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        name = S._name
        vtable.name = lltype.malloc(lltype.Array(lltype.Char), len(name)+1,
                                    immortal=True)
        for i in range(len(name)):
            vtable.name[i] = name[i]
        vtable.name[len(name)] = '\x00'
        return S, vtable

    def get_random_structure(self, r, has_vtable=False):
        if has_vtable:
            S, vtable = self.get_random_structure_type_and_vtable(r)
            p = lltype.malloc(S)
            p.parent.typeptr = vtable
        else:
            S = self.get_random_structure_type(r)
            p = lltype.malloc(S)
        for fieldname in lltype.typeOf(p).TO._names:
            if fieldname != 'parent':
                setattr(p, fieldname, r.random_integer())
        return p

    def field_values(self, p):
        dic = {}
        for fieldname in lltype.typeOf(p).TO._names:
            if fieldname != 'parent':
                dic[fieldname] = getattr(p, fieldname)
        return dic

    def print_loop(self):
        if demo_conftest.option.output:
            s = open(demo_conftest.option.output, "w")
        else:
            s = sys.stdout
        names = {None: 'None'}
        #
        def writevar(v, nameprefix):
            names[v] = '%s%d' % (nameprefix, len(names))
            print >>s, '    %s = %s()' % (names[v], v.__class__.__name__)
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
        written = {}
        for v, S, fields in self.prebuilt_ptr_consts:
            if S not in written:
                print >>s, '    %s = lltype.GcStruct(%r,' % (S._name, S._name)
                for name in S._names:
                    if name == 'parent':
                        print >>s, "              ('parent', rclass.OBJECT),"
                    else:
                        print >>s, '              (%r, lltype.Signed),'%(name,)
                print >>s, '              )'
                if S._names[0] == 'parent':
                    print >>s, '    %s_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)' % (S._name,)
                written[S] = True
            print >>s, '    p = lltype.malloc(%s)' % (S._name,)
            if S._names[0] == 'parent':
                print >>s, '    p.parent.typeptr = %s_vtable' % (S._name,)
            for name, value in fields.items():
                print >>s, '    p.%s = %d' % (name, value)
            writevar(v, 'preb')
            print >>s, '    %s.value =' % (names[v],),
            print >>s, 'lltype.cast_opaque_ptr(llmemory.GCREF, p)'
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
                        'ConstAddr(llmemory.cast_ptr_to_adr(%s_vtable))'% name)
                else:
                    args.append('ConstInt(%d)' % v.value)
            if op.descr is None:
                descrstr = ''
            else:
                descrstr = ', ' + op.descr._random_info
            print >>s, '        ResOperation(rop.%s, [%s], %s%s),' % (
                opname[op.opnum], ', '.join(args), names[op.result], descrstr)
        print >>s, '        ]'
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

class GuardClassOperation(GuardOperation):
    def gen_guard(self, builder, r):
        v, S = builder.get_structptr_var(r, must_have_vtable=True)
        if r.random() < 0.3:
            v2 = v
        else:
            v2, S2 = builder.get_structptr_var(r, must_have_vtable=True)
        vtable = v.getptr(rclass.OBJECTPTR).typeptr
        vtable2 = v2.getptr(rclass.OBJECTPTR).typeptr
        c_vtable2 = ConstAddr(llmemory.cast_ptr_to_adr(vtable2), builder.cpu)
        op = ResOperation(self.opnum, [v, c_vtable2], None)
        return op, (vtable == vtable2)

class GetFieldOperation(AbstractOperation):
    def field_descr(self, builder, r):
        v, S = builder.get_structptr_var(r)
        names = S._names
        if names[0] == 'parent':
            names = names[1:]
        name = r.choice(names)
        descr = builder.cpu.fielddescrof(S, name)
        descr._random_info = 'cpu.fielddescrof(%s, %r)' % (S._name, name)
        return v, descr

    def produce_into(self, builder, r):
        while True:
            try:
                v, descr = self.field_descr(builder, r)
                self.put(builder, [v], descr)
            except lltype.UninitializedMemoryAccess:
                continue
            break

class SetFieldOperation(GetFieldOperation):
    def produce_into(self, builder, r):
        v, descr = self.field_descr(builder, r)
        if r.random() < 0.3:
            w = ConstInt(r.random_integer())
        else:
            w = r.choice(builder.intvars)
        builder.do(self.opnum, [v, w], descr)

class NewOperation(AbstractOperation):
    def size_descr(self, builder, S):
        descr = builder.cpu.sizeof(S)
        descr._random_info = 'cpu.sizeof(%s)' % (S._name,)
        return descr

    def produce_into(self, builder, r):
        if self.opnum == rop.NEW_WITH_VTABLE:
            S, vtable = builder.get_random_structure_type_and_vtable(r)
            args = [ConstAddr(llmemory.cast_ptr_to_adr(vtable), builder.cpu)]
        else:
            S = builder.get_random_structure_type(r)
            args = []
        v_ptr = builder.do(self.opnum, args, self.size_descr(builder, S))
        builder.ptrvars.append((v_ptr, S))

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

for _op in [rop.INT_NEG,
            rop.INT_INVERT,
            rop.INT_ABS,
            ]:
    OPERATIONS.append(UnaryOperation(_op))

OPERATIONS.append(UnaryOperation(rop.INT_IS_TRUE, boolres=True))
OPERATIONS.append(BooleanUnaryOperation(rop.BOOL_NOT, boolres=True))

for i in range(3):      # make more common
    OPERATIONS.append(GetFieldOperation(rop.GETFIELD_GC))
    OPERATIONS.append(GetFieldOperation(rop.GETFIELD_GC))
    OPERATIONS.append(SetFieldOperation(rop.SETFIELD_GC))
    OPERATIONS.append(NewOperation(rop.NEW))
    OPERATIONS.append(NewOperation(rop.NEW_WITH_VTABLE))

    OPERATIONS.append(GuardOperation(rop.GUARD_TRUE))
    OPERATIONS.append(GuardOperation(rop.GUARD_FALSE))
    OPERATIONS.append(GuardClassOperation(rop.GUARD_CLASS))

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

def check_random_function(r):
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


def test_random_function():
    r = Random()
    if demo_conftest.option.repeat == -1:
        while 1: 
            check_random_function(r)
    else:
        for i in range(demo_conftest.option.repeat):
            check_random_function(r)
