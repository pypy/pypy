#!/usr/bin/env pypy
# encoding: utf-8
""" The purpose of this test file is to check that the optimizeopt *test* cases
are correct. It uses the z3 SMT solver to check the before/after optimization
traces for equivalence. Only supports very few operations for now, but would
have found the buggy tests in d9616aacbd02/issue #3832.

It can also be used to do bounded model checking on the optimizer, by
generating random traces."""
import sys
import time, io
import pytest
import struct

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask
from rpython.rlib.longlong2float import float2longlong
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    BaseTest, convert_old_style_to_targets, FakeJitDriverStaticData)
from rpython.jit.metainterp.optimizeopt.test.test_optimizeintbound import (
    TestOptimizeIntBounds as TOptimizeIntBounds)
from rpython.jit.metainterp.optimizeopt.test.test_optimizeheap import (
    TestOptimizeHeap as TOptimizeHeap)
from rpython.rtyper import rclass
from rpython.jit.metainterp import compile
from rpython.jit.metainterp.resoperation import (
    rop, ResOperation, InputArgInt, OpHelpers, InputArgRef,
    AbstractResOp)
from rpython.jit.metainterp.history import (
    JitCellToken, Const, ConstInt, ConstPtr, ConstFloat,
    get_const_ptr_for_string)
from rpython.jit.tool.oparser import parse, convert_loop_to_trace
from rpython.jit.backend.test.test_random import RandomLoop, Random, OperationBuilder, AbstractOperation
from rpython.jit.backend.test.test_random import GuardPtrOperation
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
        self.arraycopyindex = 0
        self.true_for_all_heaps = []
        self.fresh_pointers = []
        self._init_heap_types()

    def _init_heap_types(self):
        self.fielddescr_to_z3indexvar = {}

        self.nullpointer = z3.BitVec('NULL', LONG_BIT)
        self.solver_add(self.nullpointer == z3.BitVecVal(0, LONG_BIT))

        self._lltype_to_index = {}

    def solver_add(self, cond):
        if z3.simplify(cond).eq(z3.BoolVal(True)):
            return
        res = self.solver.check(cond)
        # make sure that we don't add "False" to self.solver
        if res == z3.unsat:
            assert 0, "programming error, trying to add something to solver that is equivalent to False: " + str(cond)
        #z3res = self.solver.check(z3.Not(cond))
        #if z3res == z3.unsat:
        #    print "tautology, not adding:", cond
        #    return
        self.solver.add(cond)

    def fielddescr_indexvar(self, descr):
        if descr in self.fielddescr_to_z3indexvar:
            return self.fielddescr_to_z3indexvar[descr]
        repr = "%s_%s" % (descr.S._name, descr.fieldname)
        var = z3.BitVec(repr, LONG_BIT)
        self.solver_add(var == len(self.fielddescr_to_z3indexvar))
        self.fielddescr_to_z3indexvar[descr] = var
        return var

    def _lltype_heaptypes_index(self, T):
        if T in self._lltype_to_index:
            return self._lltype_to_index[T]
        # return negative numbers to not be confused with subclassrange_min values
        res = ~len(self._lltype_to_index)
        if isinstance(T, lltype.GcArray):
            varname = 'typeindex_array_%s' % (~res)
        else:
            varname = 'typeindex_struct_%s' % T._name
        z3heaptypeindex = z3.BitVec(self._unique_name(varname), LONG_BIT)
        self.solver_add(z3heaptypeindex == res)
        self._lltype_to_index[T] = z3heaptypeindex
        return z3heaptypeindex

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
            is_array = False
            try:
                typeptr = lltype.cast_opaque_ptr(rclass.OBJECTPTR, box.value).typeptr
            except lltype.InvalidCast:
                T = lltype.typeOf(box.value._obj.container)
                typ = self._lltype_heaptypes_index(T)
                if isinstance(T, lltype.GcArray):
                    is_array = True
            else:
                typ = typeptr.subclassrange_min
            self.solver_add(self.state.heaptypes[res] == typ)
            for freshptr in self.fresh_pointers:
                self.solver_add(freshptr != res)
            if is_array:
                self.solver_add(self.state.arraylength[res] == box.value._obj.container.getlength())
            else:
                self.solver_add(self.state.arraylength[res] == -1)
            return res
        if isinstance(box, ConstFloat):
            if LONG_BIT != 64:
                pytest.skip("float checking not supported on 32-bit")
            return z3.BitVecVal(float2longlong(box.getfloat()), LONG_BIT)

        assert not isinstance(box, Const) # not supported
        return self.box_to_z3[box]

    def convertarg(self, box, arg):
        return self.convert(box.getarg(arg))

    def newvar(self, box, repr=None):
        if repr is None:
            repr = box.repr_short(box._repr_memo)
        repr = self._unique_name(repr)

        result = z3.BitVec(repr, LONG_BIT)
        self.box_to_z3[box] = result
        return result

    def _unique_name(self, repr):
        while repr in self.seen_names:
            repr += "_"
        self.seen_names[repr] = None
        return repr

    def newheaptypes(self):
        pointersort = typesort = z3.BitVecSort(LONG_BIT)
        heaptypes = z3.Array('types', pointersort, typesort)
        self.solver_add(heaptypes[self.nullpointer] == -1)
        return heaptypes

    def newarraylength(self):
        pointersort = arraylengthsort = z3.BitVecSort(LONG_BIT)
        return z3.Array('arraylength', pointersort, arraylengthsort)

    def newheap(self):
        pointersort = z3.BitVecSort(LONG_BIT)
        heapobjectsort = z3.ArraySort(pointersort, pointersort)
        self.heapindex += 1
        heap = z3.Array('heap%s'% self.heapindex, pointersort, heapobjectsort)
        for ptr, index, res in self.true_for_all_heaps:
            self.solver_add(heap[ptr][index] == res)
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
                    print beforeinput, afterinput, hex(intmask(r_uint(int(str(model[self.box_to_z3[beforeinput]])))))
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
        self.state = state
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
            else:
                assert state.before
                cond = self.guard_to_condition(op, state) # was optimized away, must be true
                self.prove(cond, op)
                continue

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
            elif opname == "same_as_i" or opname == "same_as_r":
                expr = arg0
            # heap operations
            elif opname == "ptr_eq" or opname == "instance_ptr_eq":
                expr = self.cond(arg0 == arg1)
            elif opname == "ptr_ne" or opname == "instance_ptr_ne":
                expr = self.cond(arg0 != arg1)
            elif opname == "new_with_vtable":
                expr = res
                self.fresh_pointer(res)
                vtable = descr.get_vtable().adr.ptr
                self.solver_add(state.heaptypes[expr] == vtable.subclassrange_min)
                self.solver_add(state.heap[expr] == z3.K(z3.BitVecSort(LONG_BIT), z3.BitVecVal(0, LONG_BIT)))
            elif opname == "getfield_gc_i" or opname == "getfield_gc_r":# int and reference
                # we dont differentiate between struct and field in z3 heap structure
                # so a field is an array at a specific index
                # thus we need to set the types for array and field writes, so z3 knows they cant interfere
                index = self.fielddescr_indexvar(descr)
                parentdescr = descr.get_parent_descr()
                if parentdescr.is_object():
                    vtable = parentdescr.get_vtable().adr.ptr
                    self.solver_add(state.heaptypes[arg0] >= vtable.subclassrange_min)
                    self.solver_add(state.heaptypes[arg0] <= vtable.subclassrange_max)
                expr = state.heap[arg0][index]
                if descr.is_always_pure():
                    self.true_for_all_heaps.append((arg0, index, expr))
                if isinstance(op.getarg(0), ConstPtr) and descr.is_always_pure():
                    ptr = lltype.cast_opaque_ptr(lltype.Ptr(descr.S), op.getarg(0).value)
                    const_res = getattr(ptr, descr.fieldname)
                    assert opname == "getfield_gc_i"
                    self.solver_add(expr == const_res)
                if descr.is_integer_bounded():
                    self.solver_add(expr >= descr.get_integer_min())
                    self.solver_add(expr <= descr.get_integer_max())
            elif opname == "setfield_gc":
                index = self.fielddescr_indexvar(descr)
                # copys old heap with new value inserted
                heapexpr = z3.Store(state.heap, arg0, z3.Store(state.heap[arg0], index, arg1))
                parentdescr = descr.get_parent_descr()
                if parentdescr.is_object():
                    vtable = parentdescr.get_vtable().adr.ptr
                    self.solver_add(state.heaptypes[arg0] >= vtable.subclassrange_min)
                    self.solver_add(state.heaptypes[arg0] <= vtable.subclassrange_max)
                # create new heap
                state.heap = self.newheap()
                # set new heap to modified heap with constraint
                self.solver_add(state.heap == heapexpr)
                # mark arg1 as non-null if arg1 is const or constptr
                if self.is_const(op.getarg(1)):
                    self.solver_add(arg0 != self.nullpointer)
            elif opname == "getarrayitem_gc_r" or opname == "getarrayitem_gc_i" or opname == "getarrayitem_gc_f":
                # TODO: immutable arrays
                z3typ = self._lltype_heaptypes_index(descr.A)
                self.solver_add(state.heaptypes[arg0] == z3typ)
                self.solver_add(arg1 >= 0)
                self.solver_add(arg1 < state.arraylength[arg0])
                expr = state.heap[arg0][arg1]
                if descr.is_item_integer_bounded():
                    self.solver_add(expr >= descr.get_item_integer_min())
                    self.solver_add(expr <= descr.get_item_integer_max())
            elif opname == "setarrayitem_gc":
                heapexpr = z3.Store(state.heap, arg0, z3.Store(state.heap[arg0], arg1, arg2))
                z3typ = self._lltype_heaptypes_index(descr.A)
                self.solver_add(state.heaptypes[arg0] == z3typ)
                self.solver_add(arg1 >= 0)
                self.solver_add(arg1 < state.arraylength[arg0])
                state.heap = self.newheap()
                self.solver_add(state.heap == heapexpr)
                if self.is_const(op.getarg(2)):
                    self.solver_add(arg0 != self.nullpointer)
            elif opname == "arraylen_gc":
                expr = state.arraylength[arg0]
                self.solver_add(expr >= 0)
            elif opname == "new_array" or opname == "new_array_clear":
                expr = res
                self.fresh_pointer(res)
                z3typ = self._lltype_heaptypes_index(descr.A)
                self.solver_add(state.heaptypes[res] == z3typ)
                # new_array cant return null
                self.solver_add(res != self.nullpointer)
                # store array len
                self.solver_add(state.arraylength[res] == arg0)
                self.solver_add(state.heap[expr] == z3.K(z3.BitVecSort(LONG_BIT), z3.BitVecVal(0, LONG_BIT)))
            elif opname == "escape_n":
                # the heap is completely new, but it's the same between
                # the before and the after state
                state.heap = state.nextheap(self)
            # end heap operations
            elif opname in ["label", "escape_i", "debug_merge_point", "force_token"]:
                # TODO: handling escape this way probably is not correct
                continue # ignore for now
            elif opname == "call_n":
                effectinfo = op.getdescr().get_extra_info()
                oopspecindex = effectinfo.oopspecindex
                if oopspecindex == EffectInfo.OS_ARRAYCOPY or oopspecindex == EffectInfo.OS_ARRAYMOVE:
                    array_from = self.convert(op.getarg(1)) # from array
                    if oopspecindex == EffectInfo.OS_ARRAYCOPY:
                        array_to = self.convert(op.getarg(2)) # to array
                        index_from = self.convert(op.getarg(3)) # from index
                        index_to = self.convert(op.getarg(4)) # to index
                        len_arg = op.getarg(5)
                        copy_len = self.convert(len_arg) # len
                    else:
                        array_to = array_from # to array
                        index_from = self.convert(op.getarg(2)) # from index
                        index_to = self.convert(op.getarg(3)) # to index
                        len_arg = op.getarg(4)
                        copy_len = self.convert(len_arg) # len

                    z3typ = self._lltype_heaptypes_index(effectinfo.single_write_descr_array.A)
                    # set types for both arrays
                    self.solver_add(state.heaptypes[array_from] == z3typ)
                    if oopspecindex == EffectInfo.OS_ARRAYCOPY:
                        self.solver_add(state.heaptypes[array_to] == z3typ)

                    if self.is_const(len_arg):
                        len_arg_const = len_arg.getint()
                        # do nothing on len=0 moves/copies
                        if len_arg_const == 0:
                            continue
                        # do the copy manually, to not need a forall
                        curr_heap = state.heap
                        for i in range(len_arg_const):
                            heapexpr = z3.Store(curr_heap, array_to, z3.Store(curr_heap[array_to], index_to + i, curr_heap[array_from][index_from + i]))
                            new_heap = self.newheap()
                            self.solver.add(new_heap == heapexpr)
                            curr_heap = new_heap
                        state.heap = curr_heap
                        continue

                    # general case, use forall
                    #self.solver_add(state.heaptypes[array_from] == z3type)
                    #if oopspecindex == EffectInfo.OS_ARRAYCOPY:
                        #self.solver_add(state.heaptypes[array_to] == z3type)

                    # create vars for copy ranges
                    arr_range_from = z3.BitVec('__arr_index_from_%d' % self.arraycopyindex, LONG_BIT)
                    arr_range_to = z3.BitVec('__arr_index_to_%d' % self.arraycopyindex, LONG_BIT)
                    other_range = z3.BitVec('__arr_other_index_%d' % self.arraycopyindex, LONG_BIT)
                    p = z3.BitVec('__arr_pointer_%d' % self.arraycopyindex, LONG_BIT)

                    # create new heap, but dont set to state yet
                    new_heap = self.newheap()

                    # constraint copy ranges with index and len
                    self.solver.add(z3.ForAll([arr_range_from, arr_range_to],                                               # ∀ from_idx, to_idx:
                                        z3.Implies(z3.And(
                                            z3.And(arr_range_from >= index_from, arr_range_from < index_from + copy_len), # (index_from <= from_idx < index_from + copy_len &&
                                            z3.And(arr_range_to >= index_to, arr_range_to < arr_range_to + copy_len)),    #  index_to <= to_idx < index_to + copy_len)  =>
                                        new_heap[array_to][arr_range_to] == state.heap[array_from][arr_range_from])))

                    # all other indexes of arg2 stay the same
                    self.solver.add(z3.ForAll([other_range],
                                        z3.Implies(z3.And(other_range < index_to, other_range >= index_to + copy_len),
                                        new_heap[array_to][other_range] == state.heap[array_to][other_range])))

                    # new heap is same as old heap for all other pointers
                    self.solver.add(z3.ForAll([p],
                                        z3.Implies(p != array_to, new_heap[p] == state.heap[p])))
                    state.heap = new_heap
                    self.arraycopyindex += 1
                else:
                    assert 0, "unsupported"
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
                self.solver_add(res == expr)

    def is_const(self, arg):
        return isinstance(arg, Const) or isinstance(arg, ConstPtr)

    def fresh_pointer(self, res):
        for box, var in self.box_to_z3.iteritems():
            if box.type == "r" and res is not var:
                self.solver_add(res != var)
        for const, z3var in self.constptr_to_z3.iteritems():
            self.solver_add(res != z3var)
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
            return self.convertarg(guard, 0) != self.nullpointer
        elif opname == "guard_isnull":
            return self.convertarg(guard, 0) == self.nullpointer
        else:
            assert 0, "unsupported " + opname

    def check_last(self, beforelast, state_before, afterlast, state_after):
        if beforelast.getopname() in ("jump", "finish"):
            assert beforelast.numargs() == afterlast.numargs()
            for i in range(beforelast.numargs()):
                beforearg = beforelast.getarg(i)
                if beforearg.type == 'r' and isinstance(beforearg, AbstractResOp):
                    if beforearg.opnum in (rop.NEW_WITH_VTABLE, rop.NEW, rop.NEW_ARRAY, rop.NEW_ARRAY_CLEAR):
                        continue # the pointer addresses might be different
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
        self.solver_add(cond_before)
        if afterlast:
            self.solver_add(cond_after)

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

def test_solver_add_false_protection():
    c = Checker(None, None, None, None)
    x = z3.BitVec('x', 64)
    c.solver_add(x == 1)
    with pytest.raises(AssertionError):
        c.solver_add(x != 1)

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


OPERATIONS = [op for op in OperationBuilder.OPERATIONS if not isinstance(op, GuardPtrOperation)] + [
        #CallIntPyModPyDiv(rop.CALL_PURE_I)] + [
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
    OPERATIONS.append(test_ll_random.NewArrayOperation(rop.NEW_ARRAY_CLEAR))
    OPERATIONS.append(test_ll_random.ArrayLenOperation(rop.ARRAYLEN_GC))

for i in range(2):
    OPERATIONS.append(test_ll_random.GuardClassOperation(rop.GUARD_CLASS))



class Z3OperationBuilder(test_ll_random.LLtypeOperationBuilder):
    produce_failing_guards = False
    OPERATIONS = OPERATIONS
    floatvars = []

class TestOptimizeIntBoundsZ3(BaseCheckZ3, TOptimizeIntBounds):
    def check_random_function_z3(self, cpu, r, num=None, max=None):
        t1 = time.time()
        output = io.BytesIO()
        loop = RandomLoop(cpu, Z3OperationBuilder, r, output=output)
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
        try:
            correct, timeout = check_z3(beforeinputargs, beforeops, info.inputargs, ops)
        except CheckError:
            print "to reproduce:"
            print "_" * 60
            print make_reproducer(output.getvalue())
            print "_" * 60
            raise
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
def DISABLED_test_random_loop_parses(r): # guard_class doesn't parse right now unfortunately
    cpu = LLGraphCPU(None)
    cpu.supports_floats = False
    cpu.setup_once()
    output = io.BytesIO()
    try:
        loop = RandomLoop(cpu, Z3OperationBuilder, Random(r), output=output)
    except Exception:
        raise
    s = output.getvalue()
    r = make_reproducer(s)
    try:
        check_via_reproducer_string(r)
    except Exception as e:
        print "error", e
        print "to reproduce"
        print "_" * 60
        print r
        print "_" * 60
        raise

def check_via_reproducer_string(r):
    d = {}
    exec r in d
    loop = d['loop']
    cpu = LLGraphCPU(None)
    cpu.supports_floats = False
    cpu.setup_once()
    t = TestOptimizeIntBoundsZ3()
    t.cls_attributes()
    trace = convert_loop_to_trace(loop, t.metainterp_sd)
    compile_data = compile.SimpleCompileData(
        trace, call_pure_results=None,
        enable_opts=t.enable_opts)
    compile_data.forget_optimization_info = lambda *args, **kwargs: None
    jitdriver_sd = FakeJitDriverStaticData()
    info, ops = compile_data.optimize_trace(t.metainterp_sd, jitdriver_sd, {})
    beforeinputargs, beforeops = trace.unpack()
    # check that the generated trace is correct
    correct, timeout = check_z3(beforeinputargs, beforeops, info.inputargs, ops)

@given(strategies.randoms())
def test_random_hypothesis(r):
    cpu = LLGraphCPU(None)
    cpu.supports_floats = False
    cpu.setup_once()
    t = TestOptimizeIntBoundsZ3()
    t.cls_attributes()
    t.check_random_function_z3(cpu, Random(r), 0)

def make_reproducer(s):
    lines = s.splitlines()
    assert "cpu.execute_token" in lines[-1]
    lines.pop()
    assert "loop_args =" in lines[-1]
    lines.pop()
    assert "cpu.compile_loop" in lines[-1]
    lines.pop()
    assert "looptoken =" in lines[-1]
    lines.pop()
    preamble = """\
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper import rclass
from rpython.jit.metainterp.resoperation import rop, ResOperation, \
     InputArgInt, InputArgRef, InputArgFloat
from rpython.jit.metainterp.history import TargetToken, TreeLoop
from rpython.jit.metainterp.history import BasicFailDescr, BasicFinalDescr
from rpython.jit.metainterp.history import ConstInt, ConstPtr
from rpython.jit.backend.llgraph.runner import LLGraphCPU as CPU
from rpython.jit.codewriter import heaptracker
if 1:
"""
    post = """
loop = TreeLoop('reproduce')
loop.inputargs = inputargs
loop.operations = operations
"""
    return preamble + "\n".join(lines) + post

class TestOptimizeHeapZ3(BaseCheckZ3, TOptimizeHeap):
    def dont_execute(self):
        pass # skip, can't work yet
    test_nonvirtual_later = dont_execute
    test_nonvirtual_write_null_fields_on_force = dont_execute
    test_nonvirtual_array_write_null_fields_on_force = dont_execute
    test_arraycopy_1 = dont_execute
    test_arraycopy_not_virtual = dont_execute
    test_arraycopy_invalidate_3 = dont_execute
    test_varray_negative_items_from_invalid_loop = dont_execute
    test_virtual_array_of_struct = dont_execute
    test_virtual_array_of_struct_forced = dont_execute
    test_virtual_array_of_struct_arraycopy = dont_execute
    test_nonvirtual_array_of_struct_arraycopy = dont_execute
    test_varray_struct_negative_items_from_invalid_loop = dont_execute
    test_varray_struct_too_large_items = dont_execute

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
    try:
        check_via_reproducer_string(ops)
    except CheckError as e:
        print e
        os._exit(0)
    except Exception as e:
        print e
        os._exit(-1)
    os._exit(-1)


