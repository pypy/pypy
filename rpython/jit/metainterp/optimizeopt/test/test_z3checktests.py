#!/usr/bin/env pypy
""" The purpose of this test file is to check that the optimizeopt *test* cases
are correct. It uses the z3 SMT solver to check the before/after optimization
traces for equivalence. Only supports very few operations for now, but would
have found the buggy tests in d9616aacbd02/issue #3832.

It can also be used to do bounded model checking on the optimizer, by
generating random traces."""
import sys
import pytest

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    BaseTest, convert_old_style_to_targets, FakeJitDriverStaticData)
from rpython.jit.metainterp.optimizeopt.test.test_optimizeintbound import (
    TestOptimizeIntBounds as TOptimizeIntBounds)
from rpython.jit.metainterp.optimizeopt.test.test_optimizeheap import (
    TestOptimizeHeap as TOptimizeHeap)
from rpython.jit.metainterp import compile
from rpython.jit.metainterp.resoperation import (
    rop, ResOperation, InputArgInt, OpHelpers, InputArgRef)
from rpython.jit.metainterp.history import (
    JitCellToken, Const, ConstInt, ConstPtr, get_const_ptr_for_string)
from rpython.jit.tool.oparser import parse, convert_loop_to_trace
from rpython.jit.backend.test.test_random import RandomLoop, Random, OperationBuilder, AbstractOperation
from rpython.jit.backend.test import test_ll_random
from rpython.jit.backend.llgraph.runner import LLGraphCPU
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.optimizeopt.intutils import MININT, MAXINT
from rpython.jit.metainterp.history import new_ref_dict
from rpython.rtyper.lltypesystem import lltype

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
        self.constptr_to_z3 = new_ref_dict()
        self.beforeinputargs = beforeinputargs
        self.beforeops = beforeops
        self.afterinputargs = afterinputargs
        self.afterops = afterops
        self.unsat_count = self.unknown_count = 0

        self.result_ovf = None
        self.heapindex = 0
        self.true_for_all_heaps = []
        self.fresh_pointers = []
        self._init_heap_types()
    
    def _init_heap_types(self):
        nodetype = z3.BitVec('nodetype', LONG_BIT)
        arraytype = z3.BitVec('arraytype', LONG_BIT)
        self.fielddescr_to_z3indexvar = {}

        self.solver.add(nodetype == z3.BitVecVal(7, LONG_BIT))
        self.solver.add(arraytype == z3.BitVecVal(17, LONG_BIT))
        self.nullpointer = z3.BitVec('NULL', LONG_BIT)
        self.solver.add(self.nullpointer == z3.BitVecVal(0, LONG_BIT))

        self.nodetype = nodetype
        self.arraytype = arraytype
    
    def fielddescr_indexvar(self, descr):
        if descr in self.fielddescr_to_z3indexvar:
            return self.fielddescr_to_z3indexvar[descr]
        repr = "%s_%s" % (descr.S._name, descr.fieldname)
        var = z3.BitVec(repr, LONG_BIT)
        self.solver.add(var == len(self.fielddescr_to_z3indexvar))
        self.fielddescr_to_z3indexvar[descr] = var
        return var

    def convert(self, box):
        if isinstance(box, ConstInt):
            return z3.BitVecVal(box.getint(), LONG_BIT)
        if isinstance(box, ConstPtr):
            if not box.value:
                return self.nullpointer
            if box.value in self.constptr_to_z3:
                return self.constptr_to_z3[box.value]
            res = z3.BitVec('constPTR_%s' % len(self.constptr_to_z3), LONG_BIT)
            self.constptr_to_z3[box.value] = res
            for freshptr in self.fresh_pointers:
                self.solver.add(freshptr != res)
            return res
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

    def newheaptypes(self):
        pointersort = typesort = z3.BitVecSort(LONG_BIT)
        return z3.Array('types', pointersort, typesort)
    
    def newarraylength(self):
        pointersort = arraylengthsort = z3.BitVecSort(LONG_BIT)
        return z3.Array('arraylength', pointersort, arraylengthsort)
          
    def newheap(self):
        pointersort = z3.BitVecSort(LONG_BIT)
        heapobjectsort = z3.ArraySort(pointersort, pointersort)
        self.heapindex += 1
        heap = z3.Array('heap%s'% self.heapindex, pointersort, heapobjectsort)
        for ptr, index, res in self.true_for_all_heaps:
            self.solver.add(heap[ptr][index] == res)
        return heap 

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
                if model[self.box_to_z3[beforeinput]] is not None:
                    print beforeinput, afterinput, hex(int(str(model[self.box_to_z3[beforeinput]])))
                else:
                    print beforeinput, afterinput, "unassigned in the model"
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
            descr = op.getdescr()
            # clear state
            arg0 = arg1 = arg2 = None
            if not op.is_guard():
                state.no_ovf = None

            # convert arguments
            if op.numargs() == 1:
                arg0 = self.convert(op.getarg(0))
            elif op.numargs() == 2:
                arg0 = self.convert(op.getarg(0))
                arg1 = self.convert(op.getarg(1))
            elif op.numargs() == 3:
                arg0 = self.convert(op.getarg(0))
                arg1 = self.convert(op.getarg(1))
                arg2 = self.convert(op.getarg(2))

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
            elif opname == "int_force_ge_zero":
                expr = z3.If(arg0 < 0, 0, arg0)
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
            # heap operations
            elif opname == "ptr_eq" or opname == "instance_ptr_eq":
                expr = self.cond(arg0 == arg1)
            elif opname == "ptr_ne" or opname == "instance_ptr_ne":
                expr = self.cond(arg0 != arg1)
            elif opname == "new_with_vtable":
                expr = res
                self.fresh_pointer(res)
            elif opname == "getfield_gc_i" or opname == "getfield_gc_r":# int and reference
                # we dont differentiate between struct and field in z3 heap structure
                # so a field is an array at a specific index
                # thus we need to set the types for array and field writes, so z3 knows they cant interfere
                index = self.fielddescr_indexvar(descr)
                self.solver.add(state.heaptypes[arg0] == self.nodetype)
                expr = state.heap[arg0][index]
                if descr.is_always_pure():
                    self.true_for_all_heaps.append((arg0, index, expr))
                if isinstance(op.getarg(0), ConstPtr) and descr.is_always_pure():
                    ptr = lltype.cast_opaque_ptr(lltype.Ptr(descr.S), op.getarg(0).value)
                    const_res = getattr(ptr, descr.fieldname)
                    assert opname == "getfield_gc_i"
                    self.solver.add(expr == const_res)                
                if descr.is_integer_bounded():
                    self.solver.add(expr >= descr.get_integer_min())
                    self.solver.add(expr <= descr.get_integer_max())
            elif opname == "setfield_gc":
                index = self.fielddescr_indexvar(descr)
                # copys old heap with new value inserted
                heapexpr = z3.Store(state.heap, arg0, z3.Store(state.heap[arg0], index, arg1))
                # mark ptr of array write as array 
                # so that fieldwrite and arraywrite cant interfere
                self.solver.add(state.heaptypes[arg0] == self.nodetype)
                # create new heap
                state.heap = self.newheap()
                # set new heap to modified heap with constraint
                self.solver.add(state.heap == heapexpr)
                # mark arg1 as non-null if arg1 is const or constptr
                if self.is_const(op.getarg(1)):
                    self.solver.add(arg0 != self.nullpointer)
            elif opname == "getarrayitem_gc_r" or opname == "getarrayitem_gc_i":
                # TODO: immutable arrays
                self.solver.add(state.heaptypes[arg0] == self.arraytype)
                expr = state.heap[arg0][arg1]
                if descr.is_item_integer_bounded():
                    self.solver.add(expr >= descr.get_item_integer_min())
                    self.solver.add(expr <= descr.get_item_integer_max())
            elif opname == "setarrayitem_gc":
                heapexpr = z3.Store(state.heap, arg0, z3.Store(state.heap[arg0], arg1, arg2))
                self.solver.add(state.heaptypes[arg0] == self.arraytype)
                state.heap = self.newheap()
                self.solver.add(state.heap == heapexpr)
                if self.is_const(op.getarg(2)):
                    self.solver.add(arg0 != self.nullpointer)
            elif opname == "arraylen_gc":
                expr = state.arraylength[arg0]
            elif opname == "escape_n":
                # the heap is completely new, but it's the same between
                # the before and the after state
                state.heap = state.nextheap(self)
            # end heap operations
            elif opname in ["label", "escape_i", "debug_merge_point"]:
                # TODO: handling escape this way probably is not correct
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
            if res is not None:
                self.solver.add(res == expr)

    def is_const(self, arg):
        return isinstance(arg, Const) or isinstance(arg, ConstPtr)

    def fresh_pointer(self, res):
        for box, var in self.box_to_z3.iteritems():
            if box.type == "r" and res is not var:
                self.solver.add(res != var)
        self.fresh_pointers.append(res)

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
        elif opname == "guard_class":
            arg0 = self.convertarg(guard, 0)
            cls = guard.getarg(1)
            vtable = cls.value.adr.ptr
            return state.heaptypes[arg0] == vtable.subclassrange_min
        elif opname == "guard_nonnull":
            # returns z3 var, or returns nullptr if no val in box
            arg0 = self.convertarg(guard, 0)
            self.set_arg0_to_nullptr_if_not_val(arg0)
            return arg0 != self.nullpointer
        elif opname == "guard_isnull":
            arg0 = self.convertarg(guard, 0)
            self.set_arg0_to_nullptr_if_not_val(arg0)
            return arg0 == self.nullpointer
        else:
            assert 0, "unsupported " + opname

    def set_arg0_to_nullptr_if_not_val(self, arg):
        # if arg is nullptr => set arg0 'officially' to nullptr 
        # happens e.g. if arg is ConstPTR with no value
        if arg is self.nullpointer:
            self.solver.add(arg == self.nullpointer)
        else:
            self.solver.add(arg != self.nullpointer)

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

        state_before = State()
        state_after = State(state_before)
        state_before.heap = state_after.heap = self.newheap()# heap is created new on every write
        state_before.heaptypes = state_after.heaptypes = self.newheaptypes()# types 'set' by constraints
        state_before.arraylength = state_after.arraylength = self.newarraylength()
        self.chunks = list(chunk_ops(self.beforeops, self.afterops))
        for chunkindex, (beforechunk, beforelast, afterchunk, afterlast) in enumerate(self.chunks):
            self.chunkindex = chunkindex
            self.add_to_solver(beforechunk, state_before)
            self.add_to_solver(afterchunk, state_after)
            self.check_last(beforelast, state_before, afterlast, state_after)

class State(object):
    def __init__(self, state_before=None):
        self.before = state_before is None
        self.no_ovf = None
        if self.before:
            self.heap_sequence = []
        else:
            self.heap_sequence = state_before.heap_sequence
            self.heap_index = 0
    
    def nextheap(self, checker):
        if self.before:
            res = checker.newheap()
            self.heap_sequence.append(res)
        else:
            res = self.heap_sequence[self.heap_index]
            self.heap_index += 1
        return res

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
        correct, timeout = check_z3(beforeinputargs, beforeops, info.inputargs, ops)
        print 'correct conditions:', correct, 'timed out conditions:', timeout


class TestBuggyTestsFail(BaseCheckZ3):
    def check_z3_throws_error(self, ops, optops, call_pure_results=None):
        from rpython.jit.metainterp.opencoder import Trace, TraceIterator
        loop = self.parse(ops)
        token = JitCellToken()
        if loop.operations[-1].getopnum() == rop.JUMP:
            loop.operations[-1].setdescr(token)
        trace = convert_loop_to_trace(loop, self.metainterp_sd)
        beforeinputargs, beforeops = trace.unpack()
        loopopt = self.parse(optops)
        if loopopt.operations[-1].getopnum() == rop.JUMP:
            loopopt.operations[-1].setdescr(token)
        opttrace = convert_loop_to_trace(loopopt, self.metainterp_sd)
        afterinputargs, afterops = opttrace.unpack()
        for afterop in afterops:
            assert not afterop.is_guard() # we can't chunk the operations when running in this mode
        with pytest.raises(CheckError):
            check_z3(beforeinputargs, beforeops, afterinputargs, afterops)

    def test_duplicate_getarrayitem_after_setarrayitem_3(self):
        ops = """
        [p1, p2, p3, i1]
        setarrayitem_gc(p1, i1, p2, descr=arraydescr2)
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        jump(p5)
        """
        expected = """
        [p1, p2, p3, i1]
        setarrayitem_gc(p1, i1, p2, descr=arraydescr2)
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        jump(p2)
        """
        self.check_z3_throws_error(ops, expected)


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

class KnownBitsCheck(AbstractOperation):
    def produce_into(self, builder, r):
        # inject knowledge about a random subset of the bits of an integer
        # variable
        from rpython.jit.backend.test.test_random import getint
        v_int = r.choice(list(set(builder.intvars) - set(builder.boolvars)))
        val = getint(v_int)
        ops = builder.loop.operations
        mask = r.random_integer()
        res = val & mask
        op = ResOperation(rop.INT_AND, [v_int, ConstInt(mask)])
        op._example_int = res
        ops.append(op)

        op = ResOperation(rop.GUARD_VALUE, [op, ConstInt(res)])
        op.setdescr(builder.getfaildescr())
        op.setfailargs(builder.subset_of_intvars(r))
        ops.append(op)


OPERATIONS = OperationBuilder.OPERATIONS + [ #CallIntPyModPyDiv(rop.CALL_PURE_I)] + [
        RangeCheck(None), KnownBitsCheck(None)] * 10

for i in range(4):
    OPERATIONS.append(test_ll_random.GetFieldOperation(rop.GETFIELD_GC_I))
    OPERATIONS.append(test_ll_random.GetFieldOperation(rop.GETFIELD_GC_I))
    OPERATIONS.append(test_ll_random.SetFieldOperation(rop.SETFIELD_GC))
    #OPERATIONS.append(test_ll_random.NewOperation(rop.NEW))
    OPERATIONS.append(test_ll_random.NewOperation(rop.NEW_WITH_VTABLE))

    OPERATIONS.append(test_ll_random.GetArrayItemOperation(rop.GETARRAYITEM_GC_I))
    OPERATIONS.append(test_ll_random.GetArrayItemOperation(rop.GETARRAYITEM_GC_I))
    OPERATIONS.append(test_ll_random.SetArrayItemOperation(rop.SETARRAYITEM_GC))
    #OPERATIONS.append(test_ll_random.NewArrayOperation(rop.NEW_ARRAY_CLEAR))
    #OPERATIONS.append(test_ll_random.ArrayLenOperation(rop.ARRAYLEN_GC))

#for i in range(2):
#    OPERATIONS.append(test_ll_random.GuardClassOperation(rop.GUARD_CLASS))



class Z3OperationBuilder(test_ll_random.LLtypeOperationBuilder):
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

@given(strategies.randoms())
def test_random_hypothesis(r):
    cpu = LLGraphCPU(None)
    cpu.supports_floats = False
    cpu.setup_once()
    t = TestOptimizeIntBoundsZ3()
    t.cls_attributes()
    t.check_random_function_z3(cpu, Random(r), 0)


class TestOptimizeHeapZ3(BaseCheckZ3, TOptimizeHeap):
    def dont_execute(self):
        pass # skip, can't work yet


if __name__ == '__main__':
    # this code is there so we can use the file to automatically reduce crashes
    # with shrinkray.
    # 1) install shrinkray
    # 2) put the buggy (big) trace into crash.txt
    # 3) run shrinkray like this:
    #    shrinkray test/test_z3checktests.py crash.txt --timeout=100
    # this takes a while (can be hours) but it will happily turn the huge trace
    # into a tiny one

    with open(sys.argv[1], "r") as f:
        ops = f.read()
    import pytest, os
    class config:
        class option:
            z3timeout = 100000
    pytest.config = config
    b = TestBuggyTestsFail()
    try:
        b.cls_attributes()
        b.optimize_loop(ops, ops)
    except CheckError as e:
        print e
        os._exit(0)
    except Exception as e:
        print e
        os._exit(-1)
    os._exit(-1)


