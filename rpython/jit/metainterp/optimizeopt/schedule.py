from rpython.jit.metainterp.history import (VECTOR, FLOAT, INT,
        ConstInt, ConstFloat, TargetToken)
from rpython.jit.metainterp.resoperation import (rop, ResOperation,
        GuardResOp, VecOperation, OpHelpers, VecOperationNew)
from rpython.jit.metainterp.optimizeopt.dependency import (DependencyGraph,
        MemoryRef, Node, IndexVar)
from rpython.jit.metainterp.optimizeopt.renamer import Renamer
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.jitexc import NotAProfitableLoop
from rpython.rlib.objectmodel import specialize, always_inline


class SchedulerState(object):
    def __init__(self, graph):
        self.renamer = Renamer()
        self.graph = graph
        self.oplist = []
        self.worklist = []
        self.invariant_oplist = []
        self.invariant_vector_vars = []
        self.seen = {}

    def post_schedule(self):
        loop = self.graph.loop
        self.renamer.rename(loop.jump)
        loop.operations = self.oplist
        loop.prefix = self.invariant_oplist
        if len(self.invariant_vector_vars) > 0:
            # TODO, accum?
            args = loop.label.getarglist_copy() + self.invariant_vector_vars
            opnum = loop.label.getopnum()
            # TODO descr?
            loop.prefix_label = loop.label.copy_and_change(opnum, args)

    def profitable(self):
        return True

    def prepare(self):
        for node in self.graph.nodes:
            if node.depends_count() == 0:
                self.worklist.insert(0, node)

    def emit(self, node, scheduler):
        # implement me in subclass. e.g. as in VecScheduleState
        return False

    def delay(self, node):
        return False

    def has_more(self):
        return len(self.worklist) > 0

    def ensure_args_unpacked(self, op):
        pass

    def post_emit(self, op):
        pass


class Scheduler(object):
    """ Create an instance of this class to (re)schedule a vector trace. """
    def __init__(self):
        pass

    def next(self, state):
        """ select the next candidate node to be emitted, or None """
        worklist = state.worklist
        visited = 0
        while len(worklist) > 0:
            if visited == len(worklist):
                return None
            node = worklist.pop()
            if node.emitted:
                continue
            if not self.delay(node, state):
                return node
            worklist.insert(0, node)
            visited += 1
        return None

    def delay(self, node, state):
        """ Delay this operation?
            Only if any dependency has not been resolved """
        if state.delay(node):
            return True
        return node.depends_count() != 0

    def mark_emitted(self, node, state, unpack=True):
        """ An operation has been emitted, adds new operations to the worklist
            whenever their dependency count drops to zero.
            Keeps worklist sorted (see priority) """
        worklist = state.worklist
        provides = node.provides()[:]
        for dep in provides: # COPY
            target = dep.to
            node.remove_edge_to(target)
            if not target.emitted and target.depends_count() == 0:
                # sorts them by priority
                i = len(worklist)-1
                while i >= 0:
                    cur = worklist[i]
                    c = (cur.priority - target.priority)
                    if c < 0: # meaning itnode.priority < target.priority:
                        worklist.insert(i+1, target)
                        break
                    elif c == 0:
                        # if they have the same priority, sort them
                        # using the original position in the trace
                        if target.getindex() < cur.getindex():
                            worklist.insert(i+1, target)
                            break
                    i -= 1
                else:
                    print "insert at 0", target
                    worklist.insert(0, target)
        node.clear_dependencies()
        node.emitted = True
        if not node.is_imaginary():
            op = node.getoperation()
            state.renamer.rename(op)
            if unpack:
                state.ensure_args_unpacked(op)
            state.post_emit(node.getoperation())

    def walk_and_emit(self, state):
        """ Emit all the operations into the oplist parameter.
            Initiates the scheduling. """
        assert isinstance(state, SchedulerState)
        while state.has_more():
            node = self.next(state)
            if node:
                if not state.emit(node, self):
                    if not node.emitted:
                        self.mark_emitted(node, state)
                        if not node.is_imaginary():
                            op = node.getoperation()
                            state.seen[op] = None
                            state.oplist.append(op)
                continue

            # it happens that packs can emit many nodes that have been
            # added to the scheuldable_nodes list, in this case it could
            # be that no next exists even though the list contains elements
            if not state.has_more():
                break

            raise AssertionError("schedule failed cannot continue. possible reason: cycle")

        if not we_are_translated():
            for node in state.graph.nodes:
                assert node.emitted

class TypeRestrict(object):
    ANY_TYPE = '\x00'
    ANY_SIZE = -1
    ANY_SIGN = -1
    ANY_COUNT = -1
    SIGNED = 1
    UNSIGNED = 0

    def __init__(self,
                 type=ANY_TYPE,
                 bytesize=ANY_SIZE,
                 count=ANY_SIGN,
                 sign=ANY_COUNT):
        self.type = type
        self.bytesize = bytesize
        self.sign = sign
        self.count = count

    @always_inline
    def any_size(self):
        return self.bytesize == TypeRestrict.ANY_SIZE

    def check(self, value):
        assert value.datatype != '\x00'
        if self.type != TypeRestrict.ANY_TYPE:
            if self.type != value.datatype:
                assert 0, "type mismatch"

        assert value.bytesize > 0
        if not self.any_size():
            if self.bytesize != value.bytesize:
                assert 0, "size mismatch"

        assert value.count > 0
        if self.count != TypeRestrict.ANY_COUNT:
            if self.count != value.count:
                assert 0, "count mismatch"

        if self.sign != TypeRestrict.ANY_SIGN:
            if bool(self.sign) != value.sign:
                assert 0, "sign mismatch"

    def max_input_count(self, count):
        """ How many """
        if self.count != TypeRestrict.ANY_COUNT:
            return self.count
        return count

class trans(object):

    TR_ANY = TypeRestrict()
    TR_ANY_FLOAT = TypeRestrict(FLOAT)
    TR_ANY_INTEGER = TypeRestrict(INT)
    TR_FLOAT_2 = TypeRestrict(FLOAT, 4, 2)
    TR_DOUBLE_2 = TypeRestrict(FLOAT, 8, 2)
    TR_LONG = TypeRestrict(INT, 8, 2)
    TR_INT_2 = TypeRestrict(INT, 4, 2)

    # note that the following definition is x86 arch specific
    MAPPING = {
        rop.VEC_INT_ADD:            [TR_ANY_INTEGER, TR_ANY_INTEGER],
        rop.VEC_INT_SUB:            [TR_ANY_INTEGER, TR_ANY_INTEGER],
        rop.VEC_INT_MUL:            [TR_ANY_INTEGER, TR_ANY_INTEGER],
        rop.VEC_INT_AND:            [TR_ANY_INTEGER, TR_ANY_INTEGER],
        rop.VEC_INT_OR:             [TR_ANY_INTEGER, TR_ANY_INTEGER],
        rop.VEC_INT_XOR:            [TR_ANY_INTEGER, TR_ANY_INTEGER],
        rop.VEC_INT_EQ:             [TR_ANY_INTEGER, TR_ANY_INTEGER],
        rop.VEC_INT_NE:             [TR_ANY_INTEGER, TR_ANY_INTEGER],

        rop.VEC_FLOAT_ADD:          [TR_ANY_FLOAT, TR_ANY_FLOAT],
        rop.VEC_FLOAT_SUB:          [TR_ANY_FLOAT, TR_ANY_FLOAT],
        rop.VEC_FLOAT_MUL:          [TR_ANY_FLOAT, TR_ANY_FLOAT],
        rop.VEC_FLOAT_TRUEDIV:      [TR_ANY_FLOAT, TR_ANY_FLOAT],
        rop.VEC_FLOAT_ABS:          [TR_ANY_FLOAT],
        rop.VEC_FLOAT_NEG:          [TR_ANY_FLOAT],

        rop.VEC_RAW_STORE:          [None, None, TR_ANY],
        rop.VEC_SETARRAYITEM_RAW:   [None, None, TR_ANY],
        rop.VEC_SETARRAYITEM_GC:    [None, None, TR_ANY],

        rop.GUARD_TRUE:             [TR_ANY_INTEGER],
        rop.GUARD_FALSE:            [TR_ANY_INTEGER],

        ## irregular
        rop.VEC_INT_SIGNEXT:        [TR_ANY_INTEGER],

        rop.VEC_CAST_FLOAT_TO_SINGLEFLOAT:  [TR_DOUBLE_2],
        rop.VEC_CAST_SINGLEFLOAT_TO_FLOAT:  [TR_FLOAT_2],
        rop.VEC_CAST_FLOAT_TO_INT:          [TR_DOUBLE_2],
        rop.VEC_CAST_INT_TO_FLOAT:          [TR_INT_2],

        rop.VEC_FLOAT_EQ:           [TR_ANY_FLOAT,TR_ANY_FLOAT],
        rop.VEC_FLOAT_NE:           [TR_ANY_FLOAT,TR_ANY_FLOAT],
        rop.VEC_INT_IS_TRUE:        [TR_ANY_INTEGER,TR_ANY_INTEGER],
    }

def turn_into_vector(state, pack):
    """ Turn a pack into a vector instruction """
    check_if_pack_supported(state, pack)
    state.costmodel.record_pack_savings(pack, pack.numops())
    left = pack.leftmost()
    args = left.getarglist_copy()
    prepare_arguments(state, pack, args)
    vecop = VecOperation(left.vector, args, left,
                         pack.numops(), left.getdescr())
    state.oplist.append(vecop)
    for i,node in enumerate(pack.operations):
        op = node.getoperation()
        state.setvector_of_box(op,i,vecop)
    if op.is_guard():
        assert isinstance(op, GuardResOp)
        assert isinstance(vecop, GuardResOp)
        vecop.setfailargs(op.getfailargs())
        vecop.rd_snapshot = op.rd_snapshot
    if pack.is_accumulating():
        for i,node in enumerate(pack.operations):
            op = node.getoperation()
            state.accumulation[op] = pack


def prepare_arguments(state, pack, args):
    # Transforming one argument to a vector box argument
    # The following cases can occur:
    # 1) argument is present in the box_to_vbox map.
    #    a) vector can be reused immediatly (simple case)
    #    b) the size of the input is mismatching (crop the vector)
    #    c) values are scattered in differnt registers
    #    d) the operand is not at the right position in the vector
    # 2) argument is not known to reside in a vector
    #    a) expand vars/consts before the label and add as argument
    #    b) expand vars created in the loop body
    #
    restrictions = trans.MAPPING.get(pack.leftmost().vector, [])
    if not restrictions:
        return
    for i,arg in enumerate(args):
        if i >= len(restrictions) or restrictions[i] is None:
            # ignore this argument
            continue
        restrict = restrictions[i]
        if arg.returns_vector():
            restrict.check(arg)
            continue
        pos, vecop = state.getvector_of_box(arg)
        if not vecop:
            # 2) constant/variable expand this box
            expand(state, pack, args, arg, i)
            restrict.check(args[i])
            continue
        # 1)
        args[i] = vecop # a)
        assemble_scattered_values(state, pack, args, i) # c)
        crop_vector(state, restrict, pack, args, i) # b)
        position_values(state, restrict, pack, args, i, pos) # d)
        restrict.check(args[i])

@always_inline
def crop_vector(state, restrict, pack, args, i):
    # convert size i64 -> i32, i32 -> i64, ...
    arg = args[i]
    newsize, size = restrict.bytesize, arg.bytesize
    if not restrict.any_size() and newsize != size:
        assert arg.type == 'i'
        state._prevent_signext(newsize, size)
        count = arg.count
        vecop = VecOperationNew(rop.VEC_INT_SIGNEXT, [arg, ConstInt(newsize)],
                                'i', newsize, arg.signed, count)
        state.oplist.append(vecop)
        state.costmodel.record_cast_int(size, newsize, count)
        args[i] = vecop

@always_inline
def assemble_scattered_values(state, pack, args, index):
    args_at_index = [node.getoperation().getarg(index) for node in pack.operations]
    args_at_index[0] = args[index]
    vectors = pack.argument_vectors(state, pack, index, args_at_index)
    if len(vectors) > 1:
        # the argument is scattered along different vector boxes
        args[index] = gather(state, vectors, pack.numops())
        state.remember_args_in_vector(pack, index, args[index])

@always_inline
def gather(state, vectors, count): # packed < packable and packed < stride:
    (_, arg) = vectors[0]
    i = 1
    while i < len(vectors):
        (newarg_pos, newarg) = vectors[i]
        if arg.count + newarg.count <= count:
            arg = pack_into_vector(state, arg, arg.count, newarg, newarg_pos, newarg.count)
        i += 1
    return arg

@always_inline
def position_values(state, restrict, pack, args, index, position):
    if position != 0:
        # The vector box is at a position != 0 but it
        # is required to be at position 0. Unpack it!
        arg = args[index]
        count = restrict.max_input_count(arg.count)
        args[index] = unpack_from_vector(state, arg, position, count)
        state.remember_args_in_vector(pack, index, args[index])

def check_if_pack_supported(state, pack):
    left = pack.leftmost()
    insize = left.bytesize
    if left.is_typecast():
        # prohibit the packing of signext calls that
        # cast to int16/int8.
        state._prevent_signext(left.cast_to_bytesize(),
                               left.cast_from_bytesize())
    if left.getopnum() == rop.INT_MUL:
        if insize == 8 or insize == 1:
            # see assembler for comment why
            raise NotAProfitableLoop

def unpack_from_vector(state, arg, index, count):
    """ Extract parts of the vector box into another vector box """
    #print "unpack i", index, "c", count, "v", arg
    assert count > 0
    assert index + count <= arg.count
    args = [arg, ConstInt(index), ConstInt(count)]
    vecop = OpHelpers.create_vec_unpack(arg.type, args, arg.bytesize,
                                        arg.signed, count)
    state.costmodel.record_vector_unpack(arg, index, count)
    state.oplist.append(vecop)
    return vecop

def pack_into_vector(state, tgt, tidx, src, sidx, scount):
    """ tgt = [1,2,3,4,_,_,_,_]
        src = [5,6,_,_]
        new_box = [1,2,3,4,5,6,_,_] after the operation, tidx=4, scount=2
    """
    assert sidx == 0 # restriction
    newcount = tgt.count + scount
    args = [tgt, src, ConstInt(tidx), ConstInt(scount)]
    vecop = OpHelpers.create_vec_pack(tgt.type, args, tgt.bytesize, tgt.signed, newcount)
    state.oplist.append(vecop)
    state.costmodel.record_vector_pack(src, sidx, scount)
    if not we_are_translated():
        _check_vec_pack(vecop)
    return vecop

def _check_vec_pack(op):
    arg0 = op.getarg(0)
    arg1 = op.getarg(1)
    index = op.getarg(2)
    count = op.getarg(3)
    assert op.is_vector()
    assert arg0.is_vector()
    assert index.is_constant()
    assert isinstance(count, ConstInt)
    assert arg0.bytesize == op.bytesize
    if arg1.is_vector():
        assert arg1.bytesize == op.bytesize
    else:
        assert count.value == 1
    assert index.value < op.count
    assert index.value + count.value <= op.count
    assert op.count > arg0.count

def expand(state, pack, args, arg, index):
    """ Expand a value into a vector box. useful for arith metic
        of one vector with a scalar (either constant/varialbe)
    """
    left = pack.leftmost()
    box_type = arg.type
    expanded_map = state.expanded_map

    ops = state.invariant_oplist
    variables = state.invariant_vector_vars
    if not arg.is_constant() and arg not in state.inputargs:
        # cannot be created before the loop, expand inline
        ops = state.oplist
        variables = None

    for i, node in enumerate(pack.operations):
        op = node.getoperation()
        if not arg.same_box(op.getarg(index)):
            break
        i += 1
    else:
        # note that heterogenous nodes are not yet tracked
        vecop = state.find_expanded([arg])
        if vecop:
            args[index] = vecop
            return vecop
        vecop = OpHelpers.create_vec_expand(arg, op.bytesize, op.signed, pack.numops())
        ops.append(vecop)
        if variables is not None:
            variables.append(vecop)
        state.expand([arg], vecop)
        args[index] = vecop
        return vecop

    # quick search if it has already been expanded
    expandargs = [op.getoperation().getarg(index) for op in pack.operations]
    vecop = state.find_expanded(expandargs)
    if vecop:
        args[index] = vecop
        return vecop

    vecop = OpHelpers.create_vec(arg.type, left.bytesize, left.signed)
    ops.append(vecop)
    for i,node in enumerate(pack.operations):
        op = node.getoperation()
        arg = op.getarg(index)
        arguments = [vecop, arg, ConstInt(i), ConstInt(1)]
        vecop = OpHelpers.create_vec_pack(arg.type, arguments, left.bytesize,
                                          left.signed, vecop.count+1)
        ops.append(vecop)
    state.expand(expandargs, vecop)

    if variables is not None:
        variables.append(vecop)
    args[index] = vecop

class VecScheduleState(SchedulerState):
    def __init__(self, graph, packset, cpu, costmodel):
        SchedulerState.__init__(self, graph)
        self.box_to_vbox = {}
        self.cpu = cpu
        self.vec_reg_size = cpu.vector_register_size
        self.expanded_map = {}
        self.costmodel = costmodel
        self.inputargs = {}
        self.packset = packset
        for arg in graph.loop.inputargs:
            self.inputargs[arg] = None
        self.accumulation = {}

    def expand(self, args, vecop):
        index = 0
        if len(args) == 1:
            # loop is executed once, thus sets -1 as index
            index = -1
        for arg in args:
            self.expanded_map.setdefault(arg, []).append((vecop, index))
            index += 1

    def find_expanded(self, args):
        if len(args) == 1:
            candidates = self.expanded_map.get(args[0], [])
            for (vecop, index) in candidates:
                if index == -1:
                    # found an expanded variable/constant
                    return vecop
            return None
        possible = {}
        for i, arg in enumerate(args):
            expansions = self.expanded_map.get(arg, [])
            candidates = [vecop for (vecop, index) in expansions \
                          if i == index and possible.get(vecop,True)]
            for vecop in candidates:
                for key in possible.keys():
                    if key not in candidates:
                        # delete every not possible key,value
                        possible[key] = False
                # found a candidate, append it if not yet present
                possible[vecop] = True

            if not possible:
                # no possibility left, this combination is not expanded
                return None
        for vecop,valid in possible.items():
            if valid:
                return vecop
        return None

    def post_emit(self, op):
        if op.is_guard():
            # add accumulation info to the descriptor
            # TODO for version in self.loop.versions:
            #    # this needs to be done for renamed (accum arguments)
            #    version.renamed_inputargs = [ renamer.rename_map.get(arg,arg) for arg in version.inputargs ]
            #self.appendedvar_pos_arg_count = len(sched_data.invariant_vector_vars)
            failargs = op.getfailargs()
            descr = op.getdescr()
            for i,arg in enumerate(failargs):
                if arg is None:
                    continue
                accum = self.accumulation.get(arg, None)
                if accum:
                    assert isinstance(accum, AccumPack)
                    accum.attach_accum_info(descr.rd_accum_list, i)

    def post_schedule(self):
        loop = self.graph.loop
        self.ensure_args_unpacked(loop.jump)
        SchedulerState.post_schedule(self)

    def profitable(self):
        return self.costmodel.profitable()

    def prepare(self):
        SchedulerState.prepare(self)
        self.packset.accumulate_prepare(self)
        for arg in self.graph.loop.label.getarglist():
            self.seen[arg] = None

    def emit(self, node, scheduler):
        """ If you implement a scheduler this operations is called
            to emit the actual operation into the oplist of the scheduler.
        """
        if node.pack:
            assert node.pack.numops() > 1
            for node in node.pack.operations:
                scheduler.mark_emitted(node, self, unpack=False)
            turn_into_vector(self, node.pack)
            return True
        return False

    def delay(self, node):
        if node.pack:
            pack = node.pack
            if pack.is_accumulating():
                for node in pack.operations:
                    for dep in node.depends():
                        if dep.to.pack is not pack:
                            return True
            else:
                for node in pack.operations:
                    if node.depends_count() > 0:
                        return True
        return False

    def ensure_args_unpacked(self, op):
        """ If a box is needed that is currently stored within a vector
            box, this utility creates a unpacking instruction.
        """
        # unpack for an immediate use
        for i, argument in enumerate(op.getarglist()):
            if not argument.is_constant():
                arg = self.ensure_unpacked(i, argument)
                if argument is not arg:
                    op.setarg(i, arg)
        # unpack for a guard exit
        if op.is_guard():
            # could be moved to the guard exit
            fail_args = op.getfailargs()
            for i, argument in enumerate(fail_args):
                if argument and not argument.is_constant():
                    arg = self.ensure_unpacked(i, argument)
                    if argument is not arg:
                        fail_args[i] = arg

    def ensure_unpacked(self, index, arg):
        if arg in self.seen or arg.is_vector():
            return arg
        (pos, var) = self.getvector_of_box(arg)
        if var:
            if var in self.invariant_vector_vars:
                return arg
            args = [var, ConstInt(pos), ConstInt(1)]
            vecop = OpHelpers.create_vec_unpack(var.type, args, var.bytesize,
                                                var.signed, 1)
            self.renamer.start_renaming(arg, vecop)
            self.seen[vecop] = None
            self.costmodel.record_vector_unpack(var, pos, 1)
            self.oplist.append(vecop)
            return vecop
        return arg

    def _prevent_signext(self, outsize, insize):
        if insize != outsize:
            if outsize < 4 or insize < 4:
                raise NotAProfitableLoop

    def getvector_of_box(self, arg):
        return self.box_to_vbox.get(arg, (-1, None))

    def setvector_of_box(self, var, off, vector):
        assert off < vector.count
        assert not var.is_vector()
        self.box_to_vbox[var] = (off, vector)

    def remember_args_in_vector(self, pack, index, box):
        arguments = [op.getoperation().getarg(index) for op in pack.operations]
        for i,arg in enumerate(arguments):
            if i >= box.count:
                break
            self.setvector_of_box(arg, i, box)

def opcount_filling_vector_register(pack, vec_reg_size):
    """ How many operations of that kind can one execute
        with a machine instruction of register size X?
    """
    op = pack.leftmost()
    if op.returns_void():
        assert op.is_primitive_store()
        arg = op.getarg(2)
        return vec_reg_size // arg.bytesize

    if op.is_typecast():
        if op.casts_down():
            size = op.cast_input_bytesize(vec_reg_size)
            return size // op.cast_from_bytesize()
        else:
            return vec_reg_size // op.cast_to_bytesize()
    return  vec_reg_size // op.bytesize

class Pack(object):
    """ A pack is a set of n statements that are:
        * isomorphic
        * independent
    """
    FULL = 0
    _attrs_ = ('operations', 'accumulator', 'operator', 'position')

    operator = '\x00'
    position = -1
    accumulator = None

    def __init__(self, ops):
        self.operations = ops
        self.update_pack_of_nodes()

    def numops(self):
        return len(self.operations)

    @specialize.arg(1)
    def leftmost(self, node=False):
        if node:
            return self.operations[0]
        return self.operations[0].getoperation()

    @specialize.arg(1)
    def rightmost(self, node=False):
        if node:
            return self.operations[-1]
        return self.operations[-1].getoperation()

    def pack_type(self):
        ptype = self.input_type
        if self.input_type is None:
            # load does not have an input type, but only an output type
            ptype = self.output_type
        return ptype

    def input_byte_size(self):
        """ The amount of bytes the operations need with the current
            entries in self.operations. E.g. cast_singlefloat_to_float
            takes only #2 operations.
        """
        return self._byte_size(self.input_type)

    def output_byte_size(self):
        """ The amount of bytes the operations need with the current
            entries in self.operations. E.g. vec_load(..., descr=short) 
            with 10 operations returns 20
        """
        return self._byte_size(self.output_type)

    def pack_load(self, vec_reg_size):
        """ Returns the load of the pack a vector register would hold
            just after executing the operation.
            returns: < 0 - empty, nearly empty
                     = 0 - full
                     > 0 - overloaded
        """
        left = self.leftmost()
        if left.returns_void():
            if left.is_primitive_store():
                # make this case more general if it turns out this is
                # not the only case where packs need to be trashed
                indexarg = left.getarg(2)
                return indexarg.bytesize * self.numops() - vec_reg_size
            return 0
        if self.numops() == 0:
            return -1
        if left.is_typecast():
            # casting is special, often only takes a half full vector
            if left.casts_down():
                # size is reduced
                size = left.cast_input_bytesize(vec_reg_size)
                return left.cast_from_bytesize() * self.numops() - size
            else:
                # size is increased
                #size = left.cast_input_bytesize(vec_reg_size)
                return left.cast_to_bytesize() * self.numops() - vec_reg_size
        return left.bytesize * self.numops() - vec_reg_size

    def is_full(self, vec_reg_size):
        """ If one input element times the opcount is equal
            to the vector register size, we are full!
        """
        return self.pack_load(vec_reg_size) == Pack.FULL

    def opnum(self):
        assert len(self.operations) > 0
        return self.operations[0].getoperation().getopnum()

    def clear(self):
        for node in self.operations:
            node.pack = None
            node.pack_position = -1

    def update_pack_of_nodes(self):
        for i,node in enumerate(self.operations):
            node.pack = self
            node.pack_position = i

    def split(self, packlist, vec_reg_size):
        """ Combination phase creates the biggest packs that are possible.
            In this step the pack is reduced in size to fit into an
            vector register.
        """
        before_count = len(packlist)
        #print "splitting pack", self
        pack = self
        while pack.pack_load(vec_reg_size) > Pack.FULL:
            pack.clear()
            oplist, newoplist = pack.slice_operations(vec_reg_size)
            #print "  split of %dx, left: %d" % (len(oplist), len(newoplist))
            pack.operations = oplist
            pack.update_pack_of_nodes()
            if not pack.leftmost().is_typecast():
                assert pack.is_full(vec_reg_size)
            #
            newpack = pack.clone(newoplist)
            load = newpack.pack_load(vec_reg_size)
            if load >= Pack.FULL:
                pack.update_pack_of_nodes()
                pack = newpack
                packlist.append(newpack)
            else:
                newpack.clear()
                newpack.operations = []
                break
        #print "  => %dx packs out of %d operations" % (-before_count + len(packlist) + 1, sum([pack.numops() for pack in packlist[before_count:]]))
        pack.update_pack_of_nodes()

    def slice_operations(self, vec_reg_size):
        count = opcount_filling_vector_register(self, vec_reg_size)
        assert count > 0
        newoplist = self.operations[count:]
        oplist = self.operations[:count]
        assert len(newoplist) + len(oplist) == len(self.operations)
        assert len(newoplist) != 0
        return oplist, newoplist

    def rightmost_match_leftmost(self, other):
        """ Check if pack A can be combined with pack B """
        assert isinstance(other, Pack)
        rightmost = self.operations[-1]
        leftmost = other.operations[0]
        # if it is not accumulating it is valid
        if self.is_accumulating():
            if not other.is_accumulating():
                return False
            elif self.position != other.position:
                return False
        return rightmost is leftmost

    def argument_vectors(self, state, pack, index, pack_args_index):
        vectors = []
        last = None
        for arg in pack_args_index:
            pos, vecop = state.getvector_of_box(arg)
            if vecop is not last and vecop is not None:
                vectors.append((pos, vecop))
                last = vecop
        return vectors

    def __repr__(self):
        if len(self.operations) == 0:
            return "Pack(empty)"
        return "Pack(%dx %s)" % (self.numops(), self.operations)

    def is_accumulating(self):
        return False

    def clone(self, oplist):
        return Pack(oplist)

class Pair(Pack):
    """ A special Pack object with only two statements. """
    def __init__(self, left, right):
        assert isinstance(left, Node)
        assert isinstance(right, Node)
        Pack.__init__(self, [left, right])

    def __eq__(self, other):
        if isinstance(other, Pair):
            return self.left is other.left and \
                   self.right is other.right

class AccumPack(Pack):
    SUPPORTED = { rop.FLOAT_ADD: '+',
                  rop.INT_ADD: '+',
                  rop.FLOAT_MUL: '*',
                }

    def __init__(self, nodes, operator, accum, position):
        Pack.__init__(self, [left, right])
        self.accumulator = accum
        self.operator = operator
        self.position = position

    def getdatatype(self):
        return self.accumulator.datatype

    def getbytesize(self):
        return self.accumulator.bytesize

    def getseed(self):
        """ The accumulatoriable holding the seed value """
        return self.accumulator

    def attach_accum_info(self, descr, position, scalar):
        descr.rd_accum_list = AccumInfo(descr.rd_accum_list,
                                        position, self.operator,
                                        self.scalar, None)

    def is_accumulating(self):
        return True

    def clone(self):
        return AccumPack(operations, self.operator,
                         self.accumulator, self.position)

