""" The purpose of this test file is to check that the optimizeopt *test* cases
are correct. It uses the z3 SMT solver to check the before/after optimization
traces for equivalence. Only supports very few operations for now, but would
have found the buggy tests in d9616aacbd02/issue #3832."""
import sys
import pytest

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    BaseTest, convert_old_style_to_targets, FakeJitDriverStaticData)
from rpython.jit.metainterp.optimizeopt.test.test_optimizeintbound import (
    TestOptimizeIntBounds as TOptimizeIntBounds)
from rpython.jit.metainterp import compile
from rpython.jit.metainterp.resoperation import (
    rop, ResOperation, InputArgInt, OpHelpers, InputArgRef)
from rpython.jit.metainterp.history import (
    JitCellToken, Const, ConstInt, get_const_ptr_for_string)
from rpython.jit.tool.oparser import parse, convert_loop_to_trace
from rpython.jit.backend.test.test_random import RandomLoop, Random, OperationBuilder, AbstractOperation
from rpython.jit.backend.llgraph.runner import LLGraphCPU
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.optimizeopt.intutils import MININT, MAXINT

try:
    import z3
    from hypothesis import given, strategies
except ImportError:
    pytest.skip("please install z3 (z3-solver on pypi) and hypothesis")

TRUEBV = z3.BitVecVal(1, LONG_BIT)
FALSEBV = z3.BitVecVal(0, LONG_BIT)

class CheckError(Exception):
    pass


def check_z3(beforeinputargs, beforeops, afterinputargs, afterops):
    c = Checker(beforeinputargs, beforeops, afterinputargs, afterops)
    c.check()
    return c.unsat_count, c.unknown_count

def z3_pydiv(x, y):
    r = x / y
    psubx = r * y - x
    return z3.If(
            y == z3.BitVecVal(0, LONG_BIT),
            z3.BitVecVal(0xdeadbeef, LONG_BIT), # XXX model "undefined" better
            r + (z3.If(y < 0, psubx, -psubx) >> (LONG_BIT - 1)))

def z3_pymod(x, y):
    r = x % y
    return z3.If(
            y == z3.BitVecVal(0, LONG_BIT),
            z3.BitVecVal(0xdeadbeef, LONG_BIT),
            r + (y & z3.If(y < 0, -r, r) >> (LONG_BIT - 1)))

class Checker(object):
    def __init__(self, beforeinputargs, beforeops, afterinputargs, afterops):
        self.solver = z3.Solver()
        if pytest.config.option.z3timeout:
            self.solver.set("timeout", pytest.config.option.z3timeout)
        self.box_to_z3 = {}
        self.seen_names = {}
        self.beforeinputargs = beforeinputargs
        self.beforeops = beforeops
        self.afterinputargs = afterinputargs
        self.afterops = afterops
        self.unsat_count = self.unknown_count = 0

        self.result_ovf = None

    def convert(self, box):
        if isinstance(box, ConstInt):
            return z3.BitVecVal(box.getint(), LONG_BIT)
        assert not isinstance(box, Const) # not supported
        return self.box_to_z3[box]

    def convertarg(self, box, arg):
        return self.convert(box.getarg(arg))

    def newvar(self, box, repr=None):
        if repr is None:
            repr = box.repr_short(box._repr_memo)
        while repr in self.seen_names:
            repr += "_"
        self.seen_names[repr] = None

        result = z3.BitVec(repr, LONG_BIT)
        self.box_to_z3[box] = result
        return result

    def print_chunk(self, chunk, label, model):
        print
        print "=============", label, "=================="
        for op in chunk:
            if op in self.box_to_z3:
                text = "-----> " + hex(intmask(r_uint(int(str(model[self.box_to_z3[op]])))))
            else:
                text = ""
            print op, text

    def prove(self, cond, *ops):
        z3res = self.solver.check(z3.Not(cond))
        if z3res == z3.unsat:
            self.unsat_count += 1
        elif z3res == z3.unknown:
            self.unknown_count += 1
        elif z3res == z3.sat:
            # not possible to prove!
            # print some nice stuff
            model = self.solver.model()
            print "ERROR counterexample:"
            print "inputs:"
            for beforeinput, afterinput in zip(self.beforeinputargs, self.afterinputargs):
                print beforeinput, afterinput, hex(int(str(model[self.box_to_z3[beforeinput]])))
            print "chunks:"
            for i, chunk in enumerate(self.chunks):
                beforechunk, beforelast, afterchunk, afterlast = chunk
                if i == self.chunkindex:
                    print "vvvvvvvvvvvvvvv Problem vvvvvvvvvvvvvvv"
                self.print_chunk(beforechunk + [beforelast], "before", model)
                self.print_chunk(afterchunk + [afterlast], "after", model)
                print
                if i == self.chunkindex:
                    break
            print "END counterexample"

            # raise error
            l = []
            if ops:
                l.append("in the following ops:")
                for op in ops:
                    l.append(str(op))
            l.append("the following SMT condition was not provable:")
            l.append(str(cond))
            l.append("_________________")
            l.append("smt model:")
            l.append(str(self.solver))
            l.append("_________________")
            l.append("counterexample:")
            l.append(str(model))
            raise CheckError("\n".join(l))

    def cond(self, z3expr):
        return z3.If(z3expr, TRUEBV, FALSEBV)

    def add_to_solver(self, ops, state):
        for op in ops:
            if op.type != 'v':
                res = self.newvar(op)
            else:
                res = None

            opname = op.getopname()
            # clear state
            arg0 = arg1 = None
            if not op.is_guard():
                state.no_ovf = None

            # convert arguments
            if op.numargs() == 1:
                arg0 = self.convert(op.getarg(0))
            elif op.numargs() == 2:
                arg0 = self.convert(op.getarg(0))
                arg1 = self.convert(op.getarg(1))

            # compute results
            if opname == "int_add":
                expr = arg0 + arg1
            elif opname == "int_sub":
                expr = arg0 - arg1
            elif opname == "int_mul":
                expr = arg0 * arg1
            elif opname == "int_and":
                expr = arg0 & arg1
            elif opname == "int_or":
                expr = arg0 | arg1
            elif opname == "int_xor":
                expr = arg0 ^ arg1
            elif opname == "int_eq":
                expr = self.cond(arg0 == arg1)
            elif opname == "int_ne":
                expr = self.cond(arg0 != arg1)
            elif opname == "int_lt":
                expr = self.cond(arg0 < arg1)
            elif opname == "int_le":
                expr = self.cond(arg0 <= arg1)
            elif opname == "int_gt":
                expr = self.cond(arg0 > arg1)
            elif opname == "int_ge":
                expr = self.cond(arg0 >= arg1)
            elif opname == "int_is_true":
                expr = self.cond(arg0 != FALSEBV)
            elif opname == "uint_lt":
                expr = self.cond(z3.ULT(arg0, arg1))
            elif opname == "uint_le":
                expr = self.cond(z3.ULE(arg0, arg1))
            elif opname == "uint_gt":
                expr = self.cond(z3.UGT(arg0, arg1))
            elif opname == "uint_ge":
                expr = self.cond(z3.UGE(arg0, arg1))
            elif opname == "int_is_zero":
                expr = self.cond(arg0 == FALSEBV)
            elif opname == "int_neg":
                expr = -arg0
            elif opname == "int_invert":
                expr = ~arg0
            elif opname == "int_lshift":
                expr = arg0 << arg1
            elif opname == "int_rshift":
                expr = arg0 >> arg1
            elif opname == "uint_rshift":
                expr = z3.LShR(arg0, arg1)
            elif opname == "int_add_ovf":
                expr = arg0 + arg1
                m = z3.SignExt(LONG_BIT, arg0) + z3.SignExt(LONG_BIT, arg1)
                state.no_ovf = m == z3.SignExt(LONG_BIT, expr)
            elif opname == "int_sub_ovf":
                expr = arg0 - arg1
                m = z3.SignExt(LONG_BIT, arg0) - z3.SignExt(LONG_BIT, arg1)
                state.no_ovf = m == z3.SignExt(LONG_BIT, expr)
            elif opname == "int_mul_ovf":
                expr = arg0 * arg1
                m = z3.SignExt(LONG_BIT, arg0) * z3.SignExt(LONG_BIT, arg1)
                state.no_ovf = m == z3.SignExt(LONG_BIT, expr)
            elif opname == "int_signext":
                numbits = op.getarg(1).getint() * 8
                expr = z3.SignExt(64 - numbits, z3.Extract(numbits - 1, 0, arg0))
            elif opname == "uint_mul_high":
                # zero-extend args to 2*LONG_BIT bit, then multiply and extract
                # highest LONG_BIT bits
                zarg0 = z3.ZeroExt(LONG_BIT, arg0)
                zarg1 = z3.ZeroExt(LONG_BIT, arg1)
                expr = z3.Extract(LONG_BIT * 2 - 1, LONG_BIT, zarg0 * zarg1)
            elif opname == "same_as_i":
                expr = arg0
            elif op.is_guard():
                assert state.before
                cond = self.guard_to_condition(op, state) # was optimized away, must be true
                self.prove(cond, op)
                continue
            elif opname == "label":
                continue # ignore for now
            elif opname == "call_pure_i" or opname == "call_i":
                # only div and mod supported
                effectinfo = op.getdescr().get_extra_info()
                oopspecindex = effectinfo.oopspecindex
                if oopspecindex == EffectInfo.OS_INT_PY_DIV:
                    arg0 = self.convert(op.getarg(1)) # arg 0 is the function
                    arg1 = self.convert(op.getarg(2))
                    expr = z3_pydiv(arg0, arg1)
                elif oopspecindex == EffectInfo.OS_INT_PY_MOD:
                    arg0 = self.convert(op.getarg(1)) # arg 0 is the function
                    arg1 = self.convert(op.getarg(2))
                    expr = z3_pymod(arg0, arg1)
                else:
                    assert 0, "unsupported"
            else:
                assert 0, "unsupported"
            self.solver.add(res == expr)

    def guard_to_condition(self, guard, state):
        opname = guard.getopname()
        if opname == "guard_true":
            return self.convertarg(guard, 0) == TRUEBV
        elif opname == "guard_false":
            return self.convertarg(guard, 0) == FALSEBV
        elif opname == "guard_value":
            return self.convertarg(guard, 0) == self.convertarg(guard, 1)
        elif opname == "guard_no_overflow":
            assert state.no_ovf is not None
            return state.no_ovf
        elif opname == "guard_overflow":
            assert state.no_ovf is not None
            return z3.Not(state.no_ovf)
        else:
            assert 0, "unsupported"

    def check_last(self, beforelast, state_before, afterlast, state_after):
        if beforelast.getopname() in ("jump", "finish"):
            assert beforelast.numargs() == afterlast.numargs()
            for i in range(beforelast.numargs()):
                before = self.convertarg(beforelast, i)
                after = self.convertarg(afterlast, i)
                self.prove(before == after, beforelast, afterlast)
            return
        assert beforelast.is_guard()
        # first, check the failing case
        cond_before = self.guard_to_condition(beforelast, state_before)
        if afterlast is None:
            # beforelast was optimized away, must be true
            self.prove(cond_before, beforelast)
        else:
            cond_after = self.guard_to_condition(afterlast, state_after)
            equivalent = cond_before == cond_after
            self.prove(equivalent, beforelast, afterlast)
        # then assert the true case
        self.solver.add(cond_before)
        if afterlast:
            self.solver.add(cond_after)

    def check(self):
        for beforeinput, afterinput in zip(self.beforeinputargs, self.afterinputargs):
            self.box_to_z3[beforeinput] = self.newvar(afterinput, "input_%s_%s" % (beforeinput, afterinput))

        state_before = State(before=True)
        state_after = State()
        self.chunks = list(chunk_ops(self.beforeops, self.afterops))
        for chunkindex, (beforechunk, beforelast, afterchunk, afterlast) in enumerate(self.chunks):
            self.chunkindex = chunkindex
            self.add_to_solver(beforechunk, state_before)
            self.add_to_solver(afterchunk, state_after)
            self.check_last(beforelast, state_before, afterlast, state_after)

class State(object):
    def __init__(self, before=False):
        self.before = before
        self.no_ovf = None

def chunk_ops(beforeops, afterops):
    beforeops = list(reversed(beforeops))
    afterops = list(reversed(afterops))
    while 1:
        if not beforeops:
            assert not afterops
            return
        beforechunk, beforelast = up_to_guard(beforeops)
        afterchunk, afterlast = up_to_guard(afterops)
        while (beforelast is not None and
               (afterlast is None or
                beforelast.rd_resume_position < afterlast.rd_resume_position)):
            beforechunk.append(beforelast)
            bc, beforelast = up_to_guard(beforeops)
            beforechunk.extend(bc)
        if beforelast is None:
            beforelast = beforechunk.pop()
        if afterlast is None and afterchunk:
            afterlast = afterchunk.pop()
        yield beforechunk, beforelast, afterchunk, afterlast


def up_to_guard(oplist):
    res = []
    while oplist:
        op = oplist.pop()
        if op.is_guard():
            return res, op
        res.append(op)
    return res, None

# ____________________________________________________________


class BaseCheckZ3(BaseTest):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap"

    def optimize_loop(self, ops, optops, call_pure_results=None):
        from rpython.jit.metainterp.opencoder import Trace, TraceIterator
        loop = self.parse(ops)
        token = JitCellToken()
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        exp = parse(optops, namespace=self.namespace.copy())
        expected = convert_old_style_to_targets(exp, jump=True)
        call_pure_results = self._convert_call_pure_results(call_pure_results)
        trace = convert_loop_to_trace(loop, self.metainterp_sd)
        compile_data = compile.SimpleCompileData(
            trace, call_pure_results=call_pure_results,
            enable_opts=self.enable_opts)
        compile_data.forget_optimization_info = lambda *args, **kwargs: None
        jitdriver_sd = FakeJitDriverStaticData()
        info, ops = compile_data.optimize_trace(self.metainterp_sd, jitdriver_sd, {})
        beforeinputargs, beforeops = trace.unpack()
        # check that the generated trace is correct
        check_z3(beforeinputargs, beforeops, info.inputargs, ops)


class TestBuggyTestsFail(BaseCheckZ3):
    def test_bound_lt_add_before(self, monkeypatch):
        from rpython.jit.metainterp.optimizeopt.intutils import IntBound
        # check that if we recreate the original bug, it fails:
        monkeypatch.setattr(IntBound, "add_bound", IntBound.add_bound_no_overflow)
        ops = """
        [i0]
        i2 = int_add(i0, 10)
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        i1 = int_lt(i0, 6)
        guard_true(i1) []
        jump(i0)
        """
        expected = """
        [i0]
        i2 = int_add(i0, 10)
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        jump(i0)
        """
        with pytest.raises(CheckError):
            self.optimize_loop(ops, expected)

    def Xtest_int_neg_postprocess(self):
        ops = """
        [i1]
        i2 = int_neg(i1)
        i3 = int_le(i2, 0)
        guard_true(i3) []
        i4 = int_ge(i1, 0)
        guard_true(i4) []
        """
        expected = """
        [i1]
        i2 = int_neg(i1)
        i3 = int_le(i2, 0)
        guard_true(i3) []
        """
        with pytest.raises(CheckError):
            self.optimize_loop(ops, expected)


class CallIntPyModPyDiv(AbstractOperation):
    def produce_into(self, builder, r):
        from rpython.jit.backend.test.test_random import getint
        k = r.random()
        if k < 0.20:
            v_second = ConstInt(r.random_integer())
        else:
            v_second = r.choice(builder.intvars)

        if k > 0.80 and type(v_second) is not ConstInt:
            v_first = ConstInt(r.random_integer())
        else:
            v_first = r.choice(builder.intvars)
        # exclude overflow and div by zero
        while ((
                getint(v_second) == -1 and getint(v_first) == MININT)
                or getint(v_second) == 0
        ):
            v_second = ConstInt(r.random_integer())

        if r.random() > 0.5:
            descr = BaseTest.int_py_div_descr
            res = getint(v_first) // getint(v_second)
            func = 12
        else:
            descr = BaseTest.int_py_mod_descr
            res = getint(v_first) % getint(v_second)
            func = 14
        ops = builder.loop.operations
        op = ResOperation(rop.INT_EQ, [v_second, ConstInt(0)])
        op._example_int = 0
        ops.append(op)

        op = ResOperation(rop.GUARD_FALSE, [op])
        op.setdescr(builder.getfaildescr())
        op.setfailargs(builder.subset_of_intvars(r))
        ops.append(op)

        op1 = ResOperation(rop.INT_EQ, [v_first, ConstInt(MININT)])
        op1._example_int = int(getint(v_first) == MININT)
        ops.append(op1)

        op2 = ResOperation(rop.INT_EQ, [v_second, ConstInt(-1)])
        op2._example_int = int(getint(v_second) == -1)
        ops.append(op2)

        op = ResOperation(rop.INT_AND, [op1, op2])
        op._example_int = 0 # excluded above
        ops.append(op)

        op = ResOperation(rop.GUARD_FALSE, [op])
        op.setdescr(builder.getfaildescr())
        op.setfailargs(builder.subset_of_intvars(r))
        ops.append(op)

        op = ResOperation(rop.CALL_PURE_I, [ConstInt(func), v_first, v_second],
                          descr=descr)
        if not hasattr(builder, "call_pure_results"):
            builder.call_pure_results = {}
        builder.call_pure_results[(ConstInt(func), ConstInt(getint(v_first)), ConstInt(getint(v_second)))] = ConstInt(res)
        op._example_int = res
        ops.append(op)
        builder.intvars.append(op)

class RangeCheck(AbstractOperation):
    def produce_into(self, builder, r):
        from rpython.jit.backend.test.test_random import getint
        v_int = r.choice(list(set(builder.intvars) - set(builder.boolvars)))
        val = getint(v_int)
        ops = builder.loop.operations
        bound = r.random_integer()
        if bound > val:
            op = ResOperation(rop.INT_LE, [v_int, ConstInt(bound)])
        else:
            op = ResOperation(rop.INT_GE, [v_int, ConstInt(bound)])
        op._example_int = 1
        ops.append(op)

        op = ResOperation(rop.GUARD_TRUE, [op])
        op.setdescr(builder.getfaildescr())
        op.setfailargs(builder.subset_of_intvars(r))
        ops.append(op)


OPERATIONS = OperationBuilder.OPERATIONS + [CallIntPyModPyDiv(rop.CALL_PURE_I), RangeCheck(None)]


class Z3OperationBuilder(OperationBuilder):
    produce_failing_guards = False
    OPERATIONS = OPERATIONS

class TestOptimizeIntBoundsZ3(BaseCheckZ3, TOptimizeIntBounds):
    def check_random_function_z3(self, cpu, r, num=None, max=None):
        import time
        t1 = time.time()
        loop = RandomLoop(cpu, Z3OperationBuilder, r)
        trace = convert_loop_to_trace(loop.loop, self.metainterp_sd)
        compile_data = compile.SimpleCompileData(
            trace, call_pure_results=self._convert_call_pure_results(getattr(loop.builder, 'call_pure_results', None)),
            enable_opts=self.enable_opts)
        jitdriver_sd = FakeJitDriverStaticData()
        info, ops = compile_data.optimize_trace(self.metainterp_sd, jitdriver_sd, {})
        print info.inputargs
        for op in ops:
            print op
        beforeinputargs, beforeops = trace.unpack()
        # check that the generated trace is correct
        t2 = time.time()
        correct, timeout = check_z3(beforeinputargs, beforeops, info.inputargs, ops)
        t3 = time.time()
        print 'generation/optimization [s]:', t2 - t1, 'z3:', t3 - t2, "total:", t3 - t1
        print 'correct conditions:', correct, 'timed out conditions:', timeout
        if num is not None:
            print '    # passed (%d/%s).' % (num + 1, max)
        else:
            print '    # passed.'
        print

    def test_random_z3(self):
        cpu = LLGraphCPU(None)
        cpu.supports_floats = False
        cpu.setup_once()
        r = Random()
        seed = pytest.config.option.randomseed
        try:
            if pytest.config.option.repeat == -1:
                i = 0
                while 1:
                    self.check_random_function_z3(cpu, r, i)
                    i += 1
                    seed = r.randrange(sys.maxint)
                    r.seed(seed)
            else:
                for i in range(pytest.config.option.repeat):
                    r.seed(seed)
                    self.check_random_function_z3(cpu, r, i,
                                             pytest.config.option.repeat)
                    seed = r.randrange(sys.maxint)
        except Exception as e:
            print "_" * 60
            print "got exception", e
            print "seed was", seed
            raise

