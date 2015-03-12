import sys

from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer, Optimization
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.optimizeopt.dependency import DependencyGraph
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.resume import Snapshot
from rpython.rlib.debug import debug_print, debug_start, debug_stop

def optimize_vector(metainterp_sd, jitdriver_sd, loop, optimizations):
    opt = OptVectorize(metainterp_sd, jitdriver_sd, loop, optimizations)
    opt_loop = opt.propagate_all_forward()
    if not opt.vectorized:
        # vectorization is not possible, propagate only normal optimizations
        def_opt = Optimizer(metainterp_sd, jitdriver_sd, loop, optimizations)
        def_opt.propagate_all_forward()

class VectorizeOptimizer(Optimizer):
    def setup(self):
        pass

class OptVectorize(Optimization):
    """ Try to unroll the loop and find instructions to group """

    def __init__(self, metainterp_sd, jitdriver_sd, loop, optimizations):
        self.optimizer = VectorizeOptimizer(metainterp_sd, jitdriver_sd,
                                             loop, optimizations)
        self.vec_info = LoopVectorizeInfo()
        self.memory_refs = []
        self.vectorized = False
        self.dependency_graph = None

    def _rename_arguments_ssa(self, rename_map, label_args, jump_args):
        # fill the map with the renaming boxes. keys are boxes from the label
        # values are the target boxes.

        # it is assumed that #label_args == #jump_args
        for i in range(len(label_args)):
            la = label_args[i]
            ja = jump_args[i]
            if la != ja:
                rename_map[la] = ja

    def unroll_loop_iterations(self, loop, unroll_factor):
        label_op = loop.operations[0]
        jump_op = loop.operations[-1]
        operations = [loop.operations[i].clone() for i in range(1,len(loop.operations)-1)]
        loop.operations = []

        op_index = len(operations) + 1

        iterations = [operations]
        label_op_args = [self.getvalue(box).get_key_box() for box in label_op.getarglist()]
        values = [self.getvalue(box) for box in label_op.getarglist()]
        #values[0].make_nonnull(self.optimizer)

        jump_op_args = jump_op.getarglist()

        rename_map = {}
        for unroll_i in range(2, unroll_factor+1):
            # for each unrolling factor the boxes are renamed.
            self._rename_arguments_ssa(rename_map, label_op_args, jump_op_args)
            iteration_ops = []
            for op in operations:
                copied_op = op.clone()

                if copied_op.result is not None:
                    # every result assigns a new box, thus creates an entry
                    # to the rename map.
                    new_assigned_box = copied_op.result.clonebox()
                    rename_map[copied_op.result] = new_assigned_box
                    copied_op.result = new_assigned_box

                args = copied_op.getarglist()
                for i, arg in enumerate(args):
                    try:
                        value = rename_map[arg]
                        copied_op.setarg(i, value)
                    except KeyError:
                        pass

                self.vec_info._op_index = op_index
                iteration_ops.append(copied_op)
                op_index += 1
                self.vec_info.inspect_operation(copied_op)

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
            # map will be rebuilt, the jump operation has been updated already
            rename_map.clear()

            iterations.append(iteration_ops)

        # unwrap the loop nesting.
        loop.operations.append(label_op)
        for iteration in iterations:
            for op in iteration:
                loop.operations.append(op)
        loop.operations.append(jump_op)

    def _gather_trace_information(self, loop):
        for i,op in enumerate(loop.operations):
            self.vec_info._op_index = i
            self.vec_info.inspect_operation(op)

    def get_estimated_unroll_factor(self, force_reg_bytes = -1):
        """ force_reg_bytes used for testing """
        # this optimization is not opaque, and needs info about the CPU
        byte_count = self.vec_info.smallest_type_bytes
        if byte_count == 0:
            return 0
        simd_vec_reg_bytes = 16 # TODO get from cpu
        if force_reg_bytes > 0:
            simd_vec_reg_bytes = force_reg_bytes
        unroll_factor = simd_vec_reg_bytes // byte_count
        return unroll_factor

    def propagate_all_forward(self):

        loop = self.optimizer.loop
        self.optimizer.clear_newoperations()

        self._gather_trace_information(loop)

        byte_count = self.vec_info.smallest_type_bytes
        if byte_count == 0:
            # stop, there is no chance to vectorize this trace
            return loop

        unroll_factor = self.get_estimated_unroll_factor()

        self.unroll_loop_iterations(loop, unroll_factor)

        self.build_dependencies()

        self.vectorized = True

    def build_dependency_graph(self):
        self.dependency_graph = DependencyGraph(self.optimizer,
                                                self.optimizer.loop)

    def find_adjacent_memory_refs(self):
        """ the pre pass already builds a hash of memory references and the
        operations. Since it is in SSA form there is no array index. Indices
        are flattend. If there are two array accesses in the unrolled loop
        i0,i1 and i1 = int_add(i0,c), then i0 = i0 + 0, i1 = i0 + 1 """
        considered_vars = []
        for opidx,memref in self.vec_info.memory_refs.items():
            considered_vars.append(memref.origin)

    def vectorize_trace(self, loop):
        """ Implementation of the algorithm introduced by Larsen. Refer to
              '''Exploiting Superword Level Parallelism
                 with Multimedia Instruction Sets'''
            for more details.
        """

        for i,operation in enumerate(loop.operations):

            if operation.getopnum() == rop.RAW_LOAD:
                # TODO while the loop is unrolled, build memory accesses
                pass


        # was not able to vectorize
        return False

class LoopVectorizeInfo(object):

    def __init__(self):
        self.smallest_type_bytes = 0
        self._op_index = 0
        self.memory_refs = {}
        self.label_op = None

    def operation_LABEL(self, op):
        self.label = op

    def operation_RAW_LOAD(self, op):
        descr = op.getdescr()
        self.memory_refs[self._op_index] = \
                MemoryRef(op.getarg(0), op.getarg(1))
        if not descr.is_array_of_pointers():
            byte_count = descr.get_item_size_in_bytes()
            if self.smallest_type_bytes == 0 \
               or byte_count < self.smallest_type_bytes:
                self.smallest_type_bytes = byte_count

    def default_operation(self, operation):
        pass
dispatch_opt = make_dispatcher_method(LoopVectorizeInfo, 'operation_',
        default=LoopVectorizeInfo.default_operation)
LoopVectorizeInfo.inspect_operation = dispatch_opt

class Pack(object):
    """ A pack is a set of n statements that are:
        * isomorphic
        * independant
        Statements are named operations in the code.
    """
    def __init__(self, ops):
        self.operations = ops

class Pair(Pack):
    """ A special Pack object with only two statements. """
    def __init__(self, left_op, right_op):
        assert isinstance(left_op, rop.ResOperation)
        assert isinstance(right_op, rop.ResOperation)
        self.left_op = left_op
        self.right_op = right_op
        Pack.__init__(self, [left_op, right_op])


class MemoryRef(object):
    def __init__(self, array, origin):
        self.array = array
        self.origin = origin
        self.offset = None

    def is_adjacent_to(self, mem_acc):
        """ this is a symmetric relation """
        return False
        if self.array == mem_acc.array:
            # TODO
            return self.offset == mem_acc.offset


