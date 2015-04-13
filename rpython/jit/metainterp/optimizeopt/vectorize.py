import sys
import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.metainterp.history import ConstInt, VECTOR, BoxVector
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

def debug_print_operations(self, loop):
    # XXX
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

def must_unpack_result_to_exec(op, target_op):
    # TODO either move to resop or util
    if op.getoperation().vector != -1:
        return False
    return True

def prohibit_packing(op1, op2):
    if op2.is_array_op():
        if op2.getarg(1) == op1.result:
            return True
    return False

def optimize_vector(metainterp_sd, jitdriver_sd, loop, optimizations):
    opt = VectorizingOptimizer(metainterp_sd, jitdriver_sd, loop, optimizations)
    try:
        opt.propagate_all_forward()
        # XXX
        debug_print_operations(None, loop)
        # TODO
        def_opt = Optimizer(metainterp_sd, jitdriver_sd, loop, optimizations)
        def_opt.propagate_all_forward()
        # XXX
        debug_print_operations(None, loop)
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
        self.last_debug_merge_point = None
        self.packset = None
        self.unroll_count = 0
        self.smallest_type_bytes = 0

    def propagate_all_forward(self):
        self.clear_newoperations()
        self.linear_find_smallest_type(self.loop)
        byte_count = self.smallest_type_bytes
        if byte_count == 0:
            # stop, there is no chance to vectorize this trace
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
        self._last_emitted_op = op
        self._newoperations.append(op)

    def emit_unrolled_operation(self, op):
        if op.getopnum() == rop.DEBUG_MERGE_POINT:
            self.last_debug_merge_point = op
            if not self.first_debug_merge_point:
                self.first_debug_merge_point = True
            else:
                return False
        self._last_emitted_op = op
        self._newoperations.append(op)
        return True

    def unroll_loop_iterations(self, loop, unroll_count):
        """ Unroll the loop X times. unroll_count is an integral how
        often to further unroll the loop.
        """
        op_count = len(loop.operations)

        label_op = loop.operations[0]
        jump_op = loop.operations[op_count-1]
        assert label_op.getopnum() == rop.LABEL
        assert jump_op.is_final() or jump_op.getopnum() == rop.LABEL

        # XXX self.vec_info.track_memory_refs = True

        self.emit_unrolled_operation(label_op)

        # TODO use the new optimizer structure (branch of fijal)
        #label_op_args = [self.getvalue(box).get_key_box() for box in label_op.getarglist()]
        #values = [self.getvalue(box) for box in label_op.getarglist()]

        operations = []
        for i in range(1,op_count-1):
            if loop.operations[i].getopnum() == rop.GUARD_FUTURE_CONDITION:
                continue
            op = loop.operations[i].clone()
            operations.append(op)
            self.emit_unrolled_operation(op)
            #self.vec_info.index = len(self._newoperations)-1
            #self.vec_info.inspect_operation(op)

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
                if op.getopnum() in (rop.GUARD_NO_EARLY_EXIT, rop.GUARD_FUTURE_CONDITION):
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

        if self.last_debug_merge_point is not None:
            self._last_emitted_op = self.last_debug_merge_point
            self._newoperations.append(self.last_debug_merge_point)
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
        self.relax_guard_dependencies()

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
                    #print "point forward[", a_opidx, "]", memref_a, "[",b_opidx,"]", memref_b
                    if memref_a.is_adjacent_to(memref_b):
                        #print "  -> adjacent[", a_opidx, "]", memref_a, "[",b_opidx,"]", memref_b
                        if self.packset.can_be_packed(node_a, node_b):
                            #print "    =-=-> can be packed[", a_opidx, "]", memref_a, "[",b_opidx,"]", memref_b
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
        self.clear_newoperations()
        scheduler = Scheduler(self.dependency_graph, VecScheduleData())
        print "scheduling loop"
        while scheduler.has_more():
            candidate = scheduler.next()
            print "  candidate", candidate
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

    def relax_guard_dependencies(self):
        early_exit_idx = 1
        label_idx = 0
        label = self.dependency_graph.getnode(label_idx)
        ee_guard = self.dependency_graph.getnode(early_exit_idx)
        if not ee_guard.getopnum() == rop.GUARD_NO_EARLY_EXIT:
            return # cannot relax

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
                    print ">=XXX=> ", prev_node, "=>", guard_node
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

def fail_args_break_dependency(guard, prev_op, target_guard):
    failargs = set(guard.getoperation().getfailargs())
    new_failargs = set(target_guard.getoperation().getfailargs())

    op = prev_op.getoperation()
    if not op.has_no_side_effect():
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
        assert len(pack.operations) > 1
        self.pack = pack
        op0 = pack.operations[0].getoperation()
        assert op0.vector != -1
        args = op0.getarglist()[:]
        if op0.vector in (rop.VEC_RAW_LOAD, rop.VEC_RAW_STORE):
            args.append(ConstInt(0))
        vop = ResOperation(op0.vector, args,
                            op0.result, op0.getdescr())
        self._inspect_operation(vop) # op0 is for dispatch only
        #if op0.vector not in (rop.VEC_RAW_LOAD, rop.VEC_RAW_STORE):
        #    op_count = len(pack.operations)
        #    args.append(ConstInt(op_count))
        return vop

    def _pack_vector_arg(self, vop, op, i, vbox):
        arg = op.getarg(i)
        if vbox is None:
            try:
                _, vbox = self.box_to_vbox[arg]
            except KeyError:
                vbox = BoxVector(arg.type, 4, 0, True)
            vop.setarg(i, vbox)
        self.box_to_vbox[arg] = (i,vbox)
        return vbox

    def _pack_vector_result(self, vop, op, vbox):
        result = op.result
        if vbox is None:
            vbox = BoxVector(result.type, 4, 0, True)
            vop.result = vbox
        self.box_to_vbox[result] = (-1,vbox)
        return vbox

    bin_arith_trans = """
    def _vectorize_{name}(self, vop):
        vbox_arg_0 = None
        vbox_arg_1 = None
        vbox_result = None
        ops = self.pack.operations
        for i, node in enumerate(ops):
            op = node.getoperation()
            vbox_arg_0 = self._pack_vector_arg(vop, op, 0, vbox_arg_0)
            vbox_arg_1 = self._pack_vector_arg(vop, op, 1, vbox_arg_1)
            vbox_result= self._pack_vector_result(vop, op, vbox_result)
        vbox_arg_0.item_count = vbox_arg_1.item_count = \
                vbox_result.item_count = len(ops)
    """
    exec py.code.Source(bin_arith_trans.format(name='VEC_INT_ADD')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_INT_MUL')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_INT_SUB')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_FLOAT_ADD')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_FLOAT_MUL')).compile()
    exec py.code.Source(bin_arith_trans.format(name='VEC_FLOAT_SUB')).compile()
    del bin_arith_trans

    def _vectorize_VEC_RAW_LOAD(self, vop):
        vbox_result = None
        ops = self.pack.operations
        for i, node in enumerate(ops):
            op = node.getoperation()
            vbox_result= self._pack_vector_result(vop, op, vbox_result)
        vbox_result.item_count = len(ops)
        vop.setarg(vop.numargs()-1,ConstInt(len(ops)))

    def _vectorize_VEC_RAW_STORE(self, vop):
        vbox_arg_2 = None
        ops = self.pack.operations
        for i, node in enumerate(ops):
            op = node.getoperation()
            vbox_arg_2 = self._pack_vector_arg(vop, op, 2, vbox_arg_2)
        vbox_arg_2.item_count = len(ops)
        vop.setarg(vop.numargs()-1,ConstInt(len(ops)))

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

        # without loss of generatlity: only check 'left' operation
        lpacknode = pack.left
        if prohibit_packing(lnode.getoperation(), lpacknode.getoperation()):
            return -1

        if not expand_forward:
            #print " backward savings", savings
            if not must_unpack_result_to_exec(lpacknode, lnode):
                savings += 1
            #print " => backward savings", savings
        else:
            #print " forward savings", savings
            if not must_unpack_result_to_exec(lpacknode, lnode):
                savings += 1
            #print " => forward savings", savings

        return savings

    def combine(self, i, j):
        """ combine two packs. it is assumed that the attribute self.packs
        is not iterated when calling this method. """
        pack_i = self.packs[i]
        pack_j = self.packs[j]
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
