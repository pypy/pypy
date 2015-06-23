"""
This is the core of the vec. optimization. It combines dependency.py and schedule.py
to rewrite a loop in vectorized form.

See the rpython doc for more high level details.
"""

import py

from rpython.jit.metainterp.resume import Snapshot
from rpython.jit.metainterp.jitexc import JitException
from rpython.jit.metainterp.optimizeopt.unroll import optimize_unroll
from rpython.jit.metainterp.compile import ResumeAtLoopHeaderDescr, invent_fail_descr_for_op
from rpython.jit.metainterp.history import (ConstInt, VECTOR, FLOAT, INT,
        BoxVector, BoxFloat, BoxInt, ConstFloat, TargetToken, JitCellToken, Box,
        BoxVectorAccum)
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer, Optimization
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method, Renamer
from rpython.jit.metainterp.optimizeopt.dependency import (DependencyGraph,
        MemoryRef, Node, IndexVar)
from rpython.jit.metainterp.optimizeopt.schedule import (VecScheduleData,
        Scheduler, Pack, Pair, AccumPair, Accum, vectorbox_outof_box, getpackopnum,
        getunpackopnum, PackType, determine_output_type, determine_trans)
from rpython.jit.metainterp.optimizeopt.guard import GuardStrengthenOpt
from rpython.jit.metainterp.resoperation import (rop, ResOperation, GuardResOp)
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.debug import debug_print, debug_start, debug_stop
from rpython.rlib.jit import Counters
from rpython.rtyper.lltypesystem import lltype, rffi

class NotAVectorizeableLoop(JitException):
    def __str__(self):
        return 'NotAVectorizeableLoop()'

class NotAProfitableLoop(JitException):
    def __str__(self):
        return 'NotAProfitableLoop()'

def debug_print_operations(loop):
    """ NOT_RPYTHON """
    if not we_are_translated():
        print('--- loop instr numbered ---')
        def ps(snap):
            if snap.prev is None:
                return []
            return ps(snap.prev) + snap.boxes[:]
        for i,op in enumerate(loop.operations):
            print "[",str(i).center(2," "),"]",op,
            if op.is_guard():
                print op.getfailargs()
            else:
                print ""

def optimize_vector(metainterp_sd, jitdriver_sd, loop, optimizations,
                    inline_short_preamble, start_state, cost_threshold):
    optimize_unroll(metainterp_sd, jitdriver_sd, loop, optimizations,
                    inline_short_preamble, start_state, False)
    orig_ops = loop.operations
    try:
        debug_start("vec-opt-loop")
        metainterp_sd.logger_noopt.log_loop(loop.inputargs, loop.operations, -2, None, None, "pre vectorize")
        metainterp_sd.profiler.count(Counters.OPT_VECTORIZE_TRY)
        opt = VectorizingOptimizer(metainterp_sd, jitdriver_sd, loop, cost_threshold)
        opt.propagate_all_forward()
        metainterp_sd.profiler.count(Counters.OPT_VECTORIZED)
        metainterp_sd.logger_noopt.log_loop(loop.inputargs, loop.operations, -2, None, None, "post vectorize")
    except NotAVectorizeableLoop:
        # vectorization is not possible
        loop.operations = orig_ops
    except NotAProfitableLoop:
        # cost model says to skip this loop
        loop.operations = orig_ops
    except Exception as e:
        loop.operations = orig_ops
        debug_print("failed to vectorize loop. THIS IS A FATAL ERROR!")
        if we_are_translated():
            from rpython.rtyper.lltypesystem import lltype
            from rpython.rtyper.lltypesystem.lloperation import llop
            llop.debug_print_traceback(lltype.Void)
        else:
            raise
    finally:
        debug_stop("vec-opt-loop")

class VectorizingOptimizer(Optimizer):
    """ Try to unroll the loop and find instructions to group """

    def __init__(self, metainterp_sd, jitdriver_sd, loop, cost_threshold=0):
        Optimizer.__init__(self, metainterp_sd, jitdriver_sd, loop, [])
        self.dependency_graph = None
        self.packset = None
        self.unroll_count = 0
        self.smallest_type_bytes = 0
        self.early_exit_idx = -1
        self.sched_data = None
        self.cpu = metainterp_sd.cpu
        self.costmodel = X86_CostModel(cost_threshold, self.cpu.vector_register_size)

    def propagate_all_forward(self, clear=True):
        self.clear_newoperations()
        label = self.loop.operations[0]
        jump = self.loop.operations[-1]
        if jump.getopnum() not in (rop.LABEL, rop.JUMP) or \
           label.getopnum() != rop.LABEL:
            raise NotAVectorizeableLoop()
        if jump.numargs() != label.numargs():
            raise NotAVectorizeableLoop()

        self.linear_find_smallest_type(self.loop)
        byte_count = self.smallest_type_bytes
        vsize = self.cpu.vector_register_size
        if vsize == 0 or byte_count == 0 or label.getopnum() != rop.LABEL:
            # stop, there is no chance to vectorize this trace
            # we cannot optimize normal traces (if there is no label)
            raise NotAVectorizeableLoop()

        # find index guards and move to the earliest position
        self.analyse_index_calculations()
        if self.dependency_graph is not None:
            self.schedule(False) # reorder the trace

        # unroll
        self.unroll_count = self.get_unroll_count(vsize)
        self.unroll_loop_iterations(self.loop, self.unroll_count)
        self.loop.operations = self.get_newoperations();
        self.clear_newoperations();

        # vectorize
        self.build_dependency_graph()
        self.find_adjacent_memory_refs()
        self.extend_packset()
        self.combine_packset()
        self.costmodel.reset_savings()
        self.schedule(True)
        if not self.costmodel.profitable():
            raise NotAProfitableLoop()

        gso = GuardStrengthenOpt(self.dependency_graph.index_vars)
        gso.propagate_all_forward(self.loop)

    def emit_operation(self, op):
        if op.getopnum() == rop.DEBUG_MERGE_POINT:
            return
        self._last_emitted_op = op
        self._newoperations.append(op)

    def emit_unrolled_operation(self, op):
        self._last_emitted_op = op
        self._newoperations.append(op)

    def unroll_loop_iterations(self, loop, unroll_count):
        """ Unroll the loop X times. unroll_count + 1 = unroll_factor """
        op_count = len(loop.operations)

        label_op = loop.operations[0].clone()
        assert label_op.getopnum() == rop.LABEL
        jump_op = loop.operations[op_count-1]
        # use the target token of the label
        assert jump_op.getopnum() in (rop.LABEL, rop.JUMP)
        target_token = label_op.getdescr()
        if not we_are_translated():
            target_token.assumed_classes = {}
        if jump_op.getopnum() == rop.LABEL:
            jump_op = ResOperation(rop.JUMP, jump_op.getarglist(), None, target_token)
        else:
            jump_op = jump_op.clone()
            jump_op.setdescr(target_token)
        assert jump_op.is_final()

        self.emit_unrolled_operation(label_op)

        renamer = Renamer()
        oi = 0
        pure = True
        operations = []
        ee_pos = -1
        ee_guard = None
        for i in range(1,op_count-1):
            op = loop.operations[i].clone()
            opnum = op.getopnum()
            if opnum == rop.GUARD_EARLY_EXIT:
                ee_pos = i
                ee_guard = op

            if op.is_guard():
                assert isinstance(op, GuardResOp)
                failargs = renamer.rename_failargs(op, clone=True)
                snapshot = renamer.rename_rd_snapshot(op.rd_snapshot, clone=True)
                op.setfailargs(failargs)
                op.rd_snapshot = snapshot
            operations.append(op)
            self.emit_unrolled_operation(op)

        prohibit_opnums = (rop.GUARD_FUTURE_CONDITION, rop.GUARD_EARLY_EXIT,
                           rop.GUARD_NOT_INVALIDATED)

        orig_jump_args = jump_op.getarglist()[:]
        # it is assumed that #label_args == #jump_args
        label_arg_count = len(orig_jump_args)
        for i in range(0, unroll_count):
            # fill the map with the renaming boxes. keys are boxes from the label
            for i in range(label_arg_count):
                la = label_op.getarg(i)
                ja = jump_op.getarg(i)
                ja = renamer.rename_box(ja)
                if la != ja:
                    renamer.start_renaming(la, ja)
            #
            for oi, op in enumerate(operations):
                if op.getopnum() in prohibit_opnums:
                    continue # do not unroll this operation twice
                copied_op = op.clone()
                if copied_op.result is not None:
                    # every result assigns a new box, thus creates an entry
                    # to the rename map.
                    new_assigned_box = copied_op.result.clonebox()
                    renamer.start_renaming(copied_op.result, new_assigned_box)
                    copied_op.result = new_assigned_box
                #
                args = copied_op.getarglist()
                for i, arg in enumerate(args):
                    value = renamer.rename_box(arg)
                    copied_op.setarg(i, value)
                # not only the arguments, but also the fail args need
                # to be adjusted. rd_snapshot stores the live variables
                # that are needed to resume.
                if copied_op.is_guard():
                    assert isinstance(copied_op, GuardResOp)
                    target_guard = copied_op
                    # do not overwrite resume at loop header
                    if not isinstance(target_guard.getdescr(), ResumeAtLoopHeaderDescr):
                        descr = invent_fail_descr_for_op(copied_op.getopnum(), self)
                        olddescr = copied_op.getdescr()
                        if olddescr:
                            descr.copy_all_attributes_from(olddescr)
                        copied_op.setdescr(descr)

                    if oi < ee_pos:
                        # do not clone the arguments, it is already an early exit
                        pass
                    else:
                        copied_op.rd_snapshot = \
                          renamer.rename_rd_snapshot(copied_op.rd_snapshot,
                                                     clone=True)
                        renamed_failargs = \
                            renamer.rename_failargs(copied_op,
                                                    clone=True)
                        copied_op.setfailargs(renamed_failargs)
                #
                self.emit_unrolled_operation(copied_op)

        # the jump arguments have been changed
        # if label(iX) ... jump(i(X+1)) is called, at the next unrolled loop
        # must look like this: label(i(X+1)) ... jump(i(X+2))
        args = jump_op.getarglist()
        for i, arg in enumerate(args):
            value = renamer.rename_box(arg)
            jump_op.setarg(i, value)

        self.emit_unrolled_operation(jump_op)

    def linear_find_smallest_type(self, loop):
        # O(#operations)
        for i,op in enumerate(loop.operations):
            if op.getopnum() == rop.GUARD_EARLY_EXIT:
                self.early_exit_idx = i
            if op.is_raw_array_access():
                descr = op.getdescr()
                if not descr.is_array_of_pointers():
                    byte_count = descr.get_item_size_in_bytes()
                    if self.smallest_type_bytes == 0 \
                       or byte_count < self.smallest_type_bytes:
                        self.smallest_type_bytes = byte_count

    def get_unroll_count(self, simd_vec_reg_bytes):
        """ This is an estimated number of further unrolls """
        # this optimization is not opaque, and needs info about the CPU
        byte_count = self.smallest_type_bytes
        if byte_count == 0:
            return 0
        unroll_count = simd_vec_reg_bytes // byte_count
        return unroll_count-1 # it is already unrolled once

    def build_dependency_graph(self):
        self.dependency_graph = DependencyGraph(self.loop)

    def find_adjacent_memory_refs(self):
        """ the pre pass already builds a hash of memory references and the
        operations. Since it is in SSA form there are no array indices.
        If there are two array accesses in the unrolled loop
        i0,i1 and i1 = int_add(i0,c), then i0 = i0 + 0, i1 = i0 + 1.
        They are represented as a linear combination: i*c/d + e, i is a variable,
        all others are integers that are calculated in reverse direction"""
        loop = self.loop
        operations = loop.operations

        self.packset = PackSet(self.dependency_graph, operations,
                               self.unroll_count, self.smallest_type_bytes,
                               self.cpu)
        graph = self.dependency_graph
        memory_refs = graph.memory_refs.items()
        # initialize the pack set
        for node_a,memref_a in memory_refs:
            for node_b,memref_b in memory_refs:
                if memref_a is memref_b:
                    continue
                # instead of compare every possible combination and
                # exclue a_opidx == b_opidx only consider the ones
                # that point forward:
                if node_a.is_before(node_b):
                    if memref_a.is_adjacent_to(memref_b):
                        pair = self.packset.can_be_packed(node_a, node_b, None, False)
                        if pair:
                            self.packset.add_pack(pair)

    def extend_packset(self):
        pack_count = self.packset.pack_count()
        while True:
            for pack in self.packset.packs:
                self.follow_use_defs(pack)
                self.follow_def_uses(pack)
            if pack_count == self.packset.pack_count():
                break
            pack_count = self.packset.pack_count()

    def follow_use_defs(self, pack):
        assert isinstance(pack, Pair)
        for ldep in pack.left.depends():
            for rdep in pack.right.depends():
                lnode = ldep.to
                rnode = rdep.to
                isomorph = isomorphic(lnode.getoperation(), rnode.getoperation())
                if isomorph and lnode.is_before(rnode):
                    pair = self.packset.can_be_packed(lnode, rnode, pack, False)
                    if pair:
                        self.packset.add_pack(pair)

    def follow_def_uses(self, pack):
        assert isinstance(pack, Pair)
        for ldep in pack.left.provides():
            for rdep in pack.right.provides():
                lnode = ldep.to
                rnode = rdep.to
                isomorph = isomorphic(lnode.getoperation(), rnode.getoperation())
                if isomorph and lnode.is_before(rnode):
                    pair = self.packset.can_be_packed(lnode, rnode, pack, True)
                    if pair:
                        self.packset.add_pack(pair)

    def combine_packset(self):
        if len(self.packset.packs) == 0:
            raise NotAVectorizeableLoop()
        i = 0
        j = 0
        end_ij = len(self.packset.packs)
        while True:
            len_before = len(self.packset.packs)
            i = 0
            while i < end_ij:
                while j < end_ij and i < end_ij:
                    if i == j:
                        j += 1
                        continue
                    pack1 = self.packset.packs[i]
                    pack2 = self.packset.packs[j]
                    if pack1.rightmost_match_leftmost(pack2):
                        end_ij = self.packset.combine(i,j)
                    elif pack2.rightmost_match_leftmost(pack1):
                        end_ij = self.packset.combine(j,i)
                    j += 1
                j = 0
                i += 1
            if len_before == len(self.packset.packs):
                break

        if not we_are_translated():
            # some test cases check the accumulation variables
            self.packset.accum_vars = {}
            print "packs:"
            for pack in self.packset.packs:
                accum = pack.accum
                if accum:
                    self.packset.accum_vars[accum.var] = accum.pos

                print " %dx %s (accum? %d) " % (len(pack.operations),
                                                pack.operations[0].op.getopname(),
                                                accum is not None)

    def schedule(self, vector=False):
        self.guard_early_exit = -1
        self.clear_newoperations()
        sched_data = VecScheduleData(self.cpu.vector_register_size, self.costmodel)
        scheduler = Scheduler(self.dependency_graph, sched_data)
        renamer = Renamer()
        #
        if vector:
            self.packset.accumulate_prepare(sched_data, renamer)
        #
        while scheduler.has_more():
            position = len(self._newoperations)
            ops = scheduler.next(renamer, position)
            for op in ops:
                if vector:
                    self.unpack_from_vector(op, sched_data, renamer)
                self.emit_operation(op)
        #
        if not we_are_translated():
            for node in self.dependency_graph.nodes:
                assert node.emitted
        if vector and not self.costmodel.profitable():
            return
        self.loop.operations = \
            sched_data.prepend_invariant_operations(self._newoperations)
        self.clear_newoperations()

    def unpack_from_vector(self, op, sched_data, renamer):
        renamer.rename(op)
        args = op.getarglist()
        # unpack for an immediate use
        for i, arg in enumerate(op.getarglist()):
            if isinstance(arg, Box):
                argument = self._unpack_from_vector(i, arg, sched_data, renamer)
                if arg is not argument:
                    op.setarg(i, argument)
        # unpack for a guard exit
        if op.is_guard():
            fail_args = op.getfailargs()
            for i, arg in enumerate(fail_args):
                if arg and isinstance(arg, Box):
                    argument = self._unpack_from_vector(i, arg, sched_data, renamer)
                    if arg is not argument:
                        fail_args[i] = argument

    def _unpack_from_vector(self, i, arg, sched_data, renamer):
        (j, vbox) = sched_data.box_to_vbox.get(arg, (-1, None))
        if vbox:
            arg_cloned = arg.clonebox()
            renamer.start_renaming(arg, arg_cloned)
            cj = ConstInt(j)
            ci = ConstInt(1)
            opnum = getunpackopnum(vbox.item_type)
            unpack_op = ResOperation(opnum, [vbox, cj, ci], arg_cloned)
            self.costmodel.record_vector_unpack(vbox, j, 1)
            self.emit_operation(unpack_op)
            return arg_cloned
        return arg

    def analyse_index_calculations(self):
        if len(self.loop.operations) <= 1 or self.early_exit_idx == -1:
            return
        self.dependency_graph = graph = DependencyGraph(self.loop)
        label_node = graph.getnode(0)
        ee_guard_node = graph.getnode(self.early_exit_idx)
        guards = graph.guards
        for guard_node in guards:
            if guard_node is ee_guard_node:
                continue
            modify_later = []
            last_prev_node = None
            for path in guard_node.iterate_paths(ee_guard_node, True):
                prev_node = path.second()
                dep = prev_node.depends_on(guard_node)
                if dep.is_failarg():
                    # this dependency we are able to break because it is soley
                    # relevant due to one or multiple fail args
                    if prev_node == last_prev_node:
                        #  ...
                        #  o  o
                        #  \ /
                        #  (a)
                        #   |
                        #  (g)
                        # this graph yields 2 paths from (g), thus (a) is
                        # remembered and skipped the second time visited
                        continue
                    modify_later.append((prev_node, guard_node))
                else:
                    if path.has_no_side_effects(exclude_first=True, exclude_last=True):
                        path.set_schedule_priority(10)
                        modify_later.append((path.last_but_one(), None))
                    else:
                        # transformation is invalid.
                        # exit and do not enter else branch!
                        break
                last_prev_node = prev_node
            else:
                # transformation is valid, modify the graph and execute
                # this guard earlier
                for a,b in modify_later:
                    if b is not None:
                        a.remove_edge_to(b)
                    else:
                        last_but_one = a
                        if last_but_one is ee_guard_node:
                            continue
                        ee_guard_node.remove_edge_to(last_but_one)
                        label_node.edge_to(last_but_one, label='pullup')
                # only the last guard needs a connection
                guard_node.edge_to(ee_guard_node, label='pullup-last-guard')
                guard_node.relax_guard_to(ee_guard_node)

class CostModel(object):
    def __init__(self, threshold, vec_reg_size):
        self.threshold = threshold
        self.vec_reg_size = vec_reg_size
        self.savings = 0

    def reset_savings(self):
        self.savings = 0

    def record_cast_int(self, op):
        raise NotImplementedError

    def record_pack_savings(self, pack):
        raise NotImplementedError

    def record_vector_pack(self, box, index, count):
        raise NotImplementedError

    def record_vector_unpack(self, box, index, count):
        raise NotImplementedError

    def unpack_cost(self, op, index, count):
        raise NotImplementedError

    def savings_for_pack(self, pack, times):
        raise NotImplementedError

    def profitable(self):
        return self.savings >= 0

class X86_CostModel(CostModel):

    def record_pack_savings(self, pack):
        times = pack.opcount()
        cost, benefit_factor = (1,1)
        node = pack.operations[0]
        op = node.getoperation()
        if op.getopnum() == rop.INT_SIGNEXT:
            cost, benefit_factor = self.cb_signext(pack)
        #
        self.savings += benefit_factor * times - cost

    def cb_signext(self, pack):
        op0 = pack.operations[0].getoperation()
        size = op0.getarg(1).getint()
        if pack.output_type is None:
            return 1,0
        orig_size = pack.output_type.getsize()
        if size == orig_size:
            return 0,0
        # no benefit for this operation! needs many x86 instrs
        return 1,0

    def record_cast_int(self, fromsize, tosize, count):
        # for each move there is 1 instruction
        self.savings += -count

    def record_vector_pack(self, src, index, count):
        if src.gettype() == FLOAT:
            if index == 1 and count == 1:
                self.savings -= 2
                return
        self.savings -= count

    def record_vector_unpack(self, src, index, count):
        self.record_vector_pack(src, index, count)

def isomorphic(l_op, r_op):
    """ Subject of definition """
    if l_op.getopnum() == r_op.getopnum():
        return True
    return False

class PackSet(object):
    def __init__(self, dependency_graph, operations, unroll_count,
                 smallest_type_bytes, cpu):
        self.packs = []
        self.dependency_graph = dependency_graph
        self.operations = operations
        self.unroll_count = unroll_count
        self.smallest_type_bytes = smallest_type_bytes
        self.cpu = cpu
        self.vec_reg_size = self.cpu.vector_register_size

    def pack_count(self):
        return len(self.packs)

    def add_pack(self, pack):
        self.packs.append(pack)

    def can_be_packed(self, lnode, rnode, origin_pack, forward):
        if isomorphic(lnode.getoperation(), rnode.getoperation()):
            if lnode.independent(rnode):
                if forward and isinstance(origin_pack, AccumPair):
                    # in this case the splitted accumulator must
                    # be combined. This case is not supported
                    raise NotAVectorizeableLoop()
                #
                if self.contains_pair(lnode, rnode):
                    return None
                #
                if origin_pack is None:
                    descr = lnode.getoperation().getdescr()
                    ptype = PackType.by_descr(descr, self.vec_reg_size)
                    if lnode.getoperation().is_raw_load():
                        # load outputs value, no input
                        return Pair(lnode, rnode, None, ptype)
                    else:
                        # store only has an input
                        return Pair(lnode, rnode, ptype, None)
                if self.profitable_pack(lnode, rnode, origin_pack):
                    input_type = origin_pack.output_type
                    output_type = determine_output_type(lnode, input_type)
                    return Pair(lnode, rnode, input_type, output_type)
            else:
                if self.contains_pair(lnode, rnode):
                    return None
                if origin_pack is not None:
                    return self.accumulates_pair(lnode, rnode, origin_pack)
        return None

    def contains_pair(self, lnode, rnode):
        for pack in self.packs:
            if pack.left is lnode or pack.right is rnode:
                return True
        return False

    def profitable_pack(self, lnode, rnode, origin_pack):
        lpacknode = origin_pack.left
        if self.prohibit_packing(lpacknode.getoperation(), lnode.getoperation()):
            return False
        rpacknode = origin_pack.right
        if self.prohibit_packing(rpacknode.getoperation(), rnode.getoperation()):
            return False

        return True

    def prohibit_packing(self, packed, inquestion):
        """ Blocks the packing of some operations """
        if inquestion.vector == -1:
            return True
        if packed.is_raw_array_access():
            if packed.getarg(1) == inquestion.result:
                return True
        return False

    def combine(self, i, j):
        """ combine two packs. it is assumed that the attribute self.packs
        is not iterated when calling this method. """
        pack_i = self.packs[i]
        pack_j = self.packs[j]
        pack_i.clear()
        pack_j.clear()
        operations = pack_i.operations
        for op in pack_j.operations[1:]:
            operations.append(op)
        pack = Pack(operations, pack_i.input_type, pack_i.output_type)
        self.packs[i] = pack
        # preserve the accum variable (if present) of the
        # left most pack, that is the pack with the earliest
        # operation at index 0 in the trace
        pack.accum = pack_i.accum
        pack_i.accum = pack_j.accum = None

        # instead of deleting an item in the center of pack array,
        # the last element is assigned to position j and
        # the last slot is freed. Order of packs doesn't matter
        last_pos = len(self.packs) - 1
        if j == last_pos:
            del self.packs[j]
        else:
            self.packs[j] = self.packs[last_pos]
            del self.packs[last_pos]
        return last_pos

    def accumulates_pair(self, lnode, rnode, origin_pack):
        # lnode and rnode are isomorphic and dependent
        assert isinstance(origin_pack, Pair)
        lop = lnode.getoperation()
        opnum = lop.getopnum()

        if opnum in (rop.FLOAT_ADD, rop.INT_ADD):
            roper = rnode.getoperation()
            assert lop.numargs() == 2 and lop.result is not None
            accum_var, accum_pos = self.getaccumulator_variable(lop, roper, origin_pack)
            if not accum_var:
                return None
            # the dependency exists only because of the result of lnode
            for dep in lnode.provides():
                if dep.to is rnode:
                    if not dep.because_of(accum_var):
                        # not quite ... this is not handlable
                        return None
            # get the original variable
            accum_var = lop.getarg(accum_pos)

            # in either of the two cases the arguments are mixed,
            # which is not handled currently
            var_pos = (accum_pos + 1) % 2
            plop = origin_pack.left.getoperation()
            if lop.getarg(var_pos) is not plop.result:
                return None
            prop = origin_pack.right.getoperation()
            if roper.getarg(var_pos) is not prop.result:
                return None

            # this can be handled by accumulation
            ptype = origin_pack.output_type
            if ptype.getsize() != 8:
                # do not support if if the type size is smaller
                # than the cpu word size.
                # WHY?
                # to ensure accum is done on the right size, the dependencies
                # of leading/preceding signext/floatcast instructions needs to be
                # considered. => tree pattern matching problem.
                return None
            accum = Accum(accum_var, accum_pos, Accum.PLUS)
            return AccumPair(lnode, rnode, ptype, ptype, accum)

        return None

    def getaccumulator_variable(self, lop, rop, origin_pack):
        args = rop.getarglist()
        for i, arg in enumerate(args):
            if arg is lop.result:
                return arg, i
        #
        return None, -1

    def accumulate_prepare(self, sched_data, renamer):
        vec_reg_size = sched_data.vec_reg_size
        for pack in self.packs:
            if not pack.is_accumulating():
                continue
            accum = pack.accum
            # create a new vector box for the parameters
            box = pack.input_type.new_vector_box()
            size = vec_reg_size // pack.input_type.getsize()
            op = ResOperation(rop.VEC_BOX, [ConstInt(size)], box)
            sched_data.invariant_oplist.append(op)
            result = box.clonebox()
            # clear the box to zero TODO might not be zero for every reduction?
            op = ResOperation(rop.VEC_INT_XOR, [box, box], result)
            sched_data.invariant_oplist.append(op)
            box = result
            result = BoxVectorAccum(box, accum.var, '+')
            # pack the scalar value
            op = ResOperation(getpackopnum(box.item_type),
                              [box, accum.var, ConstInt(0), ConstInt(1)], result)
            sched_data.invariant_oplist.append(op)
            # rename the variable with the box
            renamer.start_renaming(accum.var, result)

