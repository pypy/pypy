import sys
import py
from rpython.jit.metainterp.compile import ResumeAtLoopHeaderDescr
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.metainterp.history import (ConstInt, VECTOR, BoxVector,
        TargetToken, JitCellToken)
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer, Optimization
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.optimizeopt.dependency import (DependencyGraph, 
        MemoryRef, Scheduler, SchedulerData, Node)
from rpython.jit.metainterp.resoperation import (rop, ResOperation)
from rpython.jit.metainterp.resume import Snapshot
from rpython.rlib.debug import debug_print, debug_start, debug_stop
from rpython.jit.metainterp.jitexc import JitException
from rpython.rlib.objectmodel import we_are_translated

class NotAVectorizeableLoop(JitException):
    def __str__(self):
        return 'NotAVectorizeableLoop()'

def dprint(*args):
    if not we_are_translated():
        for arg in args:
            print arg,
        print


def debug_print_operations(loop):
    if not we_are_translated():
        print('--- loop instr numbered ---')
        def ps(snap):
            if snap.prev is None:
                return []
            return ps(snap.prev) + snap.boxes[:]
        for i,op in enumerate(loop.operations):
            print "[",str(i).center(2," "),"]",op,
            if op.is_guard():
                if op.rd_snapshot is not None:
                    print ps(op.rd_snapshot)
                else:
                    print op.getfailargs()
            else:
                print ""

def optimize_vector(metainterp_sd, jitdriver_sd, loop, optimizations):
    opt = VectorizingOptimizer(metainterp_sd, jitdriver_sd, loop, optimizations)
    try:
        opt.propagate_all_forward()
        debug_print_operations(loop)
        def_opt = Optimizer(metainterp_sd, jitdriver_sd, loop, optimizations)
        def_opt.propagate_all_forward()
    except NotAVectorizeableLoop:
        # vectorization is not possible, propagate only normal optimizations
        def_opt = Optimizer(metainterp_sd, jitdriver_sd, loop, optimizations)
        def_opt.propagate_all_forward()

class VectorizingOptimizer(Optimizer):
    """ Try to unroll the loop and find instructions to group """

    def __init__(self, metainterp_sd, jitdriver_sd, loop, optimizations):
        Optimizer.__init__(self, metainterp_sd, jitdriver_sd, loop, optimizations)
        self.memory_refs = []
        self.dependency_graph = None
        self.first_debug_merge_point = False
        self.packset = None
        self.unroll_count = 0
        self.smallest_type_bytes = 0
        self.early_exit = None
        self.future_condition = None

    def propagate_all_forward(self):
        self.clear_newoperations()
        label = self.loop.operations[0]
        jump = self.loop.operations[-1]
        if jump.getopnum() != rop.LABEL:
            # compile_loop appends a additional label to all loops
            # we cannot optimize normal traces
            raise NotAVectorizeableLoop()

        self.linear_find_smallest_type(self.loop)
        byte_count = self.smallest_type_bytes
        if byte_count == 0 or label.getopnum() != rop.LABEL:
            # stop, there is no chance to vectorize this trace
            # we cannot optimize normal traces (if there is no label)
            raise NotAVectorizeableLoop()

        # unroll
        self.unroll_count = self.get_unroll_count()
        self.unroll_loop_iterations(self.loop, self.unroll_count)
        self.loop.operations = self.get_newoperations();
        self.clear_newoperations();

        # vectorize
        self.build_dependency_graph()
        self.find_adjacent_memory_refs()
        self.extend_packset()
        self.combine_packset()
        self.schedule()

    def emit_operation(self, op):
        if op.getopnum() == rop.GUARD_EARLY_EXIT:
            return
        self._last_emitted_op = op
        self._newoperations.append(op)

    def emit_unrolled_operation(self, op):
        self._last_emitted_op = op
        self._newoperations.append(op)

    def unroll_loop_iterations(self, loop, unroll_count):
        """ Unroll the loop X times. unroll_count is an integral how
        often to further unroll the loop.
        """
        op_count = len(loop.operations)

        label_op = loop.operations[0].clone()
        jump_op = loop.operations[op_count-1].clone()
        # use the target token of the label
        jump_op = ResOperation(rop.JUMP, jump_op.getarglist(), None, label_op.getdescr())
        assert label_op.getopnum() == rop.LABEL
        assert jump_op.is_final()

        self.emit_unrolled_operation(label_op)
        #guard_ee_op = ResOperation(rop.GUARD_EARLY_EXIT, [], None, ResumeAtLoopHeaderDescr())
        #guard_ee_op.rd_snapshot = Snapshot(None, loop.inputargs[:])
        #self.emit_unrolled_operation(guard_ee_op)

        operations = []
        for i in range(1,op_count-1):
            op = loop.operations[i].clone()
            if loop.operations[i].getopnum() == rop.GUARD_FUTURE_CONDITION:
                pass
            if loop.operations[i].getopnum() == rop.GUARD_EARLY_EXIT:
                self.future_condition = op
            operations.append(op)
            self.emit_unrolled_operation(op)

        orig_jump_args = jump_op.getarglist()[:]
        # it is assumed that #label_args == #jump_args
        label_arg_count = len(orig_jump_args)
        rename_map = {}
        for i in range(0, unroll_count):
            # fill the map with the renaming boxes. keys are boxes from the label
            for i in range(label_arg_count):
                la = label_op.getarg(i)
                ja = jump_op.getarg(i)
                if ja in rename_map:
                    ja = rename_map[ja]
                if la != ja:
                    rename_map[la] = ja
            #
            for op in operations:
                if op.getopnum() == rop.GUARD_FUTURE_CONDITION:
                    continue # do not unroll this operation twice
                if op.getopnum() == rop.GUARD_EARLY_EXIT:
                    continue # do not unroll this operation twice
                copied_op = op.clone()
                if copied_op.result is not None:
                    # every result assigns a new box, thus creates an entry
                    # to the rename map.
                    new_assigned_box = copied_op.result.clonebox()
                    rename_map[copied_op.result] = new_assigned_box
                    copied_op.result = new_assigned_box
                #
                args = copied_op.getarglist()
                for i, arg in enumerate(args):
                    try:
                        value = rename_map[arg]
                        copied_op.setarg(i, value)
                    except KeyError:
                        pass
                # not only the arguments, but also the fail args need
                # to be adjusted. rd_snapshot stores the live variables
                # that are needed to resume.
                if copied_op.is_guard():
                    snapshot = self.clone_snapshot(copied_op.rd_snapshot, rename_map)
                    copied_op.rd_snapshot = snapshot
                    if not we_are_translated():
                        # ensure that in a test case the renaming is correct
                        if copied_op.getfailargs():
                            args = copied_op.getfailargs()[:]
                            for i,arg in enumerate(args):
                                try:
                                    value = rename_map[arg]
                                    args[i] = value
                                except KeyError:
                                    pass
                            copied_op.setfailargs(args)
                #
                self.emit_unrolled_operation(copied_op)

        # the jump arguments have been changed
        # if label(iX) ... jump(i(X+1)) is called, at the next unrolled loop
        # must look like this: label(i(X+1)) ... jump(i(X+2))
        args = jump_op.getarglist()
        for i, arg in enumerate(args):
            try:
                value = rename_map[arg]
                jump_op.setarg(i, value)
            except KeyError:
                pass

        self.emit_unrolled_operation(jump_op)

    def clone_snapshot(self, snapshot, rename_map):
        # snapshots are nested like the MIFrames
        if snapshot is None:
            return None
        boxes = snapshot.boxes
        new_boxes = boxes[:]
        for i,box in enumerate(boxes):
            try:
                value = rename_map[box]
                new_boxes[i] = value
            except KeyError:
                pass

        snapshot = Snapshot(self.clone_snapshot(snapshot.prev, rename_map),
                            new_boxes)
        return snapshot

    def linear_find_smallest_type(self, loop):
        # O(#operations)
        for i,op in enumerate(loop.operations):
            if op.is_array_op():
                descr = op.getdescr()
                if not descr.is_array_of_pointers():
                    byte_count = descr.get_item_size_in_bytes()
                    if self.smallest_type_bytes == 0 \
                       or byte_count < self.smallest_type_bytes:
                        self.smallest_type_bytes = byte_count

    def get_unroll_count(self):
        """ This is an estimated number of further unrolls """
        # this optimization is not opaque, and needs info about the CPU
        byte_count = self.smallest_type_bytes
        if byte_count == 0:
            return 0
        simd_vec_reg_bytes = 16 # TODO get from cpu
        unroll_count = simd_vec_reg_bytes // byte_count
        return unroll_count-1 # it is already unrolled once

    def build_dependency_graph(self):
        self.dependency_graph = DependencyGraph(self.loop.operations)
        self.relax_index_guards()

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
                                self.unroll_count,
                                self.smallest_type_bytes)
        memory_refs = self.dependency_graph.memory_refs.items()
        # initialize the pack set
        for node_a,memref_a in memory_refs:
            for node_b,memref_b in memory_refs:
                # instead of compare every possible combination and
                # exclue a_opidx == b_opidx only consider the ones
                # that point forward:
                if node_a.is_before(node_b):
                    if memref_a.is_adjacent_to(memref_b):
                        if self.packset.can_be_packed(node_a, node_b):
                            self.packset.add_pair(node_a, node_b)

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
                if lnode.is_before(rnode) and self.packset.can_be_packed(lnode, rnode):
                    savings = self.packset.estimate_savings(lnode, rnode, pack, False)
                    if savings >= 0:
                        self.packset.add_pair(lnode, rnode)

    def follow_def_uses(self, pack):
        assert isinstance(pack, Pair)
        savings = -1
        candidate = (-1,-1)
        for ldep in pack.left.provides():
            for rdep in pack.right.provides():
                lnode = ldep.to
                rnode = rdep.to
                if lnode.is_before(rnode) and \
                   self.packset.can_be_packed(lnode, rnode):
                    est_savings = \
                        self.packset.estimate_savings(lnode, rnode, pack, True)
                    if est_savings > savings:
                        savings = est_savings
                        candidate = (lnode, rnode)
        #
        if savings >= 0:
            self.packset.add_pair(*candidate)

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

    def schedule(self):
        dprint(self.dependency_graph.as_dot())
        self.clear_newoperations()
        scheduler = Scheduler(self.dependency_graph, VecScheduleData())
        dprint("scheduling loop. scheduleable are: " + str(scheduler.schedulable_nodes))
        while scheduler.has_more():
            candidate = scheduler.next()
            dprint("  candidate", candidate, "has pack?", candidate.pack != None, "pack", candidate.pack)
            if candidate.pack:
                pack = candidate.pack
                if scheduler.schedulable(pack.operations):
                    vop = scheduler.sched_data.as_vector_operation(pack)
                    self.emit_operation(vop)
                    scheduler.schedule_all(pack.operations)
                else:
                    scheduler.schedule_later(0)
            else:
                self.emit_operation(candidate.getoperation())
                scheduler.schedule(0)

        self.loop.operations = self._newoperations[:]
        if not we_are_translated():
            for node in self.dependency_graph.nodes:
                assert node.emitted

    def relax_index_guards(self):
        label_idx = 0
        early_exit_idx = 1
        label = self.dependency_graph.getnode(label_idx)
        ee_guard = self.dependency_graph.getnode(early_exit_idx)
        if not ee_guard.is_guard_early_exit():
            return # cannot relax

        #self.early_exit = ee_guard

        for guard_node in self.dependency_graph.guards:
            if guard_node == ee_guard:
                continue
            if guard_node.getopnum() not in (rop.GUARD_TRUE,rop.GUARD_FALSE):
                continue
            del_deps = []
            pullup = []
            iterb = guard_node.iterate_paths(ee_guard, True)
            last_prev_node = None
            for path in iterb:
                prev_node = path.second()
                if fail_args_break_dependency(guard_node, prev_node, ee_guard):
                    if prev_node == last_prev_node:
                        continue
                    dprint("relax) ", prev_node, "=>", guard_node)
                    del_deps.append((prev_node,guard_node))
                else:
                    pullup.append(path)
                last_prev_node = prev_node
            for a,b in del_deps:
                a.remove_edge_to(b)
            for candidate in pullup:
                lbo = candidate.last_but_one()
                if candidate.has_no_side_effects(exclude_first=True, exclude_last=True):
                    ee_guard.remove_edge_to(lbo)
                    label.edge_to(lbo, label='pullup')
            guard_node.edge_to(ee_guard, label='pullup')
            label.remove_edge_to(ee_guard)

            guard_node.relax_guard_to(self.future_condition)

def must_unpack_result_to_exec(op, target_op):
    # TODO either move to resop or util
    if op.getoperation().vector != -1:
        return False
    return True

def prohibit_packing(op1, op2):
    if op1.is_array_op():
        if op1.getarg(1) == op2.result:
            dprint("prohibit)", op1, op2)
            return True
    return False

def fail_args_break_dependency(guard, prev_op, target_guard):
    failargs = guard.getfailarg_set()
    new_failargs = target_guard.getfailarg_set()

    op = prev_op.getoperation()
    if not op.is_always_pure(): # TODO has_no_side_effect():
        return True
    if op.result is not None:
        arg = op.result
        if arg not in failargs or \
               arg in failargs and arg in new_failargs:
            return False
    for arg in op.getarglist():
        if arg not in failargs or \
               arg in failargs and arg in new_failargs:
            return False
    # THINK about: increased index in fail arg, but normal index on arglist
    # this might be an indicator for edge removal
    return True

class VecScheduleData(SchedulerData):
    def __init__(self):
        self.box_to_vbox = {}

    def as_vector_operation(self, pack):
        op_count = pack.operations
        assert op_count > 1
        self.pack = pack
        # properties that hold for the pack are:
        # isomorphism (see func above)
        op0 = pack.operations[0].getoperation()
        assert op0.vector != -1
        args = op0.getarglist()[:]
        args.append(ConstInt(len(op_count)))
        vop = ResOperation(op0.vector, args, op0.result, op0.getdescr())
        self._inspect_operation(vop)
        return vop

    def get_vbox_for(self, arg):
        try:
            _, vbox = self.box_to_vbox[arg]
            return vbox
        except KeyError:
            # if this is not the case, then load operations must
            # be emitted
            assert False, "vector box MUST be defined before"

    def vector_result(self, vop): 
        ops = self.pack.operations
        op0 = ops[0].getoperation()
        result = op0.result
        vbox = BoxVector(result.type, 4, 0, True)
        vop.result = vbox
        i = 0
        vboxcount = vbox.item_count = len(ops)
        while i < vboxcount:
            op = ops[i].getoperation()
            self.box_to_vbox[result] = (i, vbox)
            i += 1

    def vector_arg(self, vop, argidx):
        ops = self.pack.operations
        op0 = ops[0].getoperation()
        vbox = self.get_vbox_for(op0.getarg(argidx))
        vop.setarg(argidx, vbox)

    bin_arith_trans = """
    def _vectorize_{name}(self, vop):
        self.vector_arg(vop, 0)
        self.vector_arg(vop, 1)
        self.vector_result(vop)
    """
    exec py.code.Source(bin_arith_trans.format(name='VEC_INT_ADD')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_INT_MUL')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_INT_SUB')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_FLOAT_ADD')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_FLOAT_MUL')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_FLOAT_SUB')).compile()
    del bin_arith_trans

    def _vectorize_VEC_INT_SIGNEXT(self, vop):
        self.vector_arg(vop, 0)
        # arg 1 is a constant
        self.vector_result(vop)

    def _vectorize_VEC_RAW_LOAD(self, vop):
        self.vector_result(vop)
    def _vectorize_VEC_GETARRAYITEM_RAW(self, vop):
        self.vector_result(vop)

    def _vectorize_VEC_RAW_STORE(self, vop):
        self.vector_arg(vop, 2)
    def _vectorize_VEC_SETARRAYITEM_RAW(self, vop):
        self.vector_arg(vop, 2)

VecScheduleData._inspect_operation = \
        make_dispatcher_method(VecScheduleData, '_vectorize_')

def isomorphic(l_op, r_op):
    """ Same instructions have the same operation name.
    TODO what about parameters?
    """
    if l_op.getopnum() == r_op.getopnum():
        return True

class PackSet(object):

    def __init__(self, dependency_graph, operations, unroll_count,
                 smallest_type_bytes):
        self.packs = []
        self.dependency_graph = dependency_graph
        self.operations = operations
        self.unroll_count = unroll_count
        self.smallest_type_bytes = smallest_type_bytes

    def pack_count(self):
        return len(self.packs)

    def add_pair(self, l, r):
        self.packs.append(Pair(l,r))

    def can_be_packed(self, lnode, rnode):
        if isomorphic(lnode.getoperation(), rnode.getoperation()):
            if lnode.independent(rnode):
                for pack in self.packs:
                    # TODO save pack on Node
                    if pack.left.getindex()== lnode.getindex() or \
                       pack.right.getindex() == rnode.getindex():
                        return False
                return True
        return False

    def estimate_savings(self, lnode, rnode, pack, expand_forward):
        """ Estimate the number of savings to add this pair.
        Zero is the minimum value returned. This should take
        into account the benefit of executing this instruction
        as SIMD instruction.
        """
        savings = -1

        lpacknode = pack.left
        if prohibit_packing(lpacknode.getoperation(), lnode.getoperation()):
            return -1
        rpacknode = pack.right
        if prohibit_packing(rpacknode.getoperation(), rnode.getoperation()):
            return -1

        if not expand_forward:
            if not must_unpack_result_to_exec(lpacknode, lnode) and \
               not must_unpack_result_to_exec(rpacknode, rnode):
                savings += 1
        else:
            if not must_unpack_result_to_exec(lpacknode, lnode) and \
               not must_unpack_result_to_exec(rpacknode, rnode):
                savings += 1
        if savings >= 0:
            dprint("estimated " + str(savings) + " for lpack,lnode", lpacknode, lnode)

        return savings

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
        self.packs[i] = Pack(operations)


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

    def pack_for_operation(self, node):
        for pack in self.packs:
            for node2 in pack.operations:
                if node == node2:
                    return pack
        return None

class Pack(object):
    """ A pack is a set of n statements that are:
        * isomorphic
        * independent
    """
    def __init__(self, ops):
        self.operations = ops
        self.savings = 0
        for node in self.operations:
            node.pack = self

    def clear(self):
        for node in self.operations:
            node.pack = None

    def rightmost_match_leftmost(self, other):
        assert isinstance(other, Pack)
        rightmost = self.operations[-1]
        leftmost = other.operations[0]
        return rightmost == leftmost

    def __repr__(self):
        return "Pack(%r)" % self.operations

class Pair(Pack):
    """ A special Pack object with only two statements. """
    def __init__(self, left, right):
        assert isinstance(left, Node)
        assert isinstance(right, Node)
        self.left = left
        self.right = right
        Pack.__init__(self, [left, right])

    def __eq__(self, other):
        if isinstance(other, Pair):
            return self.left == other.left and \
                   self.right == other.right
