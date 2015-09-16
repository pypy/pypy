from rpython.jit.metainterp.history import (VECTOR, FLOAT, INT,
        ConstInt, ConstFloat, TargetToken)
from rpython.jit.metainterp.resoperation import (rop, ResOperation,
        GuardResOp, VecOperation, OpHelpers)
from rpython.jit.metainterp.optimizeopt.dependency import (DependencyGraph,
        MemoryRef, Node, IndexVar)
from rpython.jit.metainterp.optimizeopt.renamer import Renamer
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.jitexc import NotAProfitableLoop


class SchedulerState(object):
    def __init__(self, graph):
        self.renamer = Renamer()
        self.graph = graph
        self.oplist = []
        self.worklist = []
        self.invariant_oplist = []
        self.invariant_vector_vars = []

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
        return self.costmodel.profitable()

    def prepare(self):
        pass

    def delay(self):
        return False

    def has_more(self):
        return len(self.worklist) > 0

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
        op = node.getoperation()
        state.renamer.rename(op)
        if unpack:
            state.ensure_args_unpacked(op)
        node.position = len(state.oplist)
        worklist = state.worklist
        for dep in node.provides()[:]: # COPY
            to = dep.to
            node.remove_edge_to(to)
            if not to.emitted and to.depends_count() == 0:
                # sorts them by priority
                i = len(worklist)-1
                while i >= 0:
                    itnode = worklist[i]
                    c = (itnode.priority - to.priority)
                    if c < 0: # meaning itnode.priority < to.priority:
                        worklist.insert(i+1, to)
                        break
                    elif c == 0:
                        # if they have the same priority, sort them
                        # using the original position in the trace
                        if itnode.getindex() < to.getindex():
                            worklist.insert(i, to)
                            break
                    i -= 1
                else:
                    worklist.insert(0, to)
        node.clear_dependencies()
        node.emitted = True

    def walk_and_emit(self, state):
        """ Emit all the operations into the oplist parameter.
            Initiates the scheduling. """
        assert isinstance(state, SchedulerState)
        while state.has_more():
            node = self.next(state)
            if node:
                if not state.emit(node, self):
                    if not node.emitted:
                        op = node.getoperation()
                        self.mark_emitted(node, state)
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

#UNSIGNED_OPS = (rop.UINT_FLOORDIV, rop.UINT_RSHIFT,
#                rop.UINT_LT, rop.UINT_LE,
#                rop.UINT_GT, rop.UINT_GE)

#class Type(object):
#    """ The type of one operation. Saves type, size and sign. """
#    @staticmethod
#    def of(op):
#        descr = op.getdescr()
#        if descr:
#            type = INT
#            if descr.is_array_of_floats() or descr.concrete_type == FLOAT:
#                type = FLOAT
#            size = descr.get_item_size_in_bytes()
#            sign = descr.is_item_signed()
#            return Type(type, size, sign)
#        else:
#            size = 8
#            sign = True
#            if op.type == 'f' or op.getopnum() in UNSIGNED_OPS:
#                sign = False
#            return Type(op.type, size, sign)
#
#    def __init__(self, type, size, signed):
#        assert type in (FLOAT, INT)
#        self.type = type
#        self.size = size
#        self.signed = signed
#
#    def bytecount(self):
#        return self.size
#
#    def clone(self):
#        return Type(self.type, self.size, self.signed)
#
#    def __repr__(self):
#        sign = '-'
#        if not self.signed:
#            sign = '+'
#        return 'Type(%s%s, %d)' % (sign, self.type, self.size)
#
    #UNKNOWN_TYPE = '-'

    #@staticmethod
    #def of(box, count=-1):
    #    assert box.type == 'V'
    #    if count == -1:
    #        count = box.getcount()
    #    return Type(box.gettype(), box.getsize(), box.getsigned(), count)

    #@staticmethod
    #def by_descr(descr, vec_reg_size):
    #    _t = INT
    #    signed = descr.is_item_signed()
    #    if descr.is_array_of_floats() or descr.concrete_type == FLOAT:
    #        _t = FLOAT
    #        signed = False
    #    size = descr.get_item_size_in_bytes()
    #    pt = Type(_t, size, signed, vec_reg_size // size)
    #    return pt

    #def clone(self):
    #    return Type(self.type, self.size, self.signed, self.count)

    #def new_vector_box(self, count = -1):
    #    if count == -1:
    #        count = self.count
    #    assert count > 1
    #    assert self.type in ('i','f')
    #    assert self.size > 0
    #    xxx
    #    return BoxVector(self.type, count, self.size, self.signed)

    #def combine(self, other):
    #    """ nothing to be done here """
    #    if not we_are_translated():
    #        assert self.type == other.type
    #        assert self.signed == other.signed


    #def byte_size(self):
    #    return self.count * self.size

    #def setsize(self, size):
    #    self.size = size

    #def setcount(self, count):
    #    self.count = count

    #def gettype(self):
    #    return self.type

    #def getsize(self):
    #    return self.size

    #def getcount(self):
    #    return self.count



class TypeOutput(object):
    def __init__(self, type, count):
        self.type = type
        self.count = count


    def bytecount(self):
        return self.count * self.type.bytecount()

class TypeRestrict(object):
    ANY_TYPE = -1
    ANY_SIZE = -1
    ANY_SIGN = -1
    ANY_COUNT = -1
    SIGNED = 1
    UNSIGNED = 0

    def __init__(self, type=-1, bytesize=-1, count=-1, sign=-1):
        self.type = type
        self.bytesize = bytesize
        self.sign = sign
        self.count = count

    def allows(self, type, count):
        if self.type != ANY_TYPE:
            if self.type != type.type:
                return False

        # TODO

        return True

class trans(object):

    TR_ANY = TypeRestrict()
    TR_ANY_FLOAT = TypeRestrict(FLOAT)
    TR_ANY_INTEGER = TypeRestrict(INT)
    TR_FLOAT_2 = TypeRestrict(FLOAT, 4, 2)
    TR_DOUBLE_2 = TypeRestrict(FLOAT, 8, 2)
    TR_LONG = TypeRestrict(INT, 8, 2)
    TR_INT_2 = TypeRestrict(INT, 4, 2)

    #INT = OpToVectorOp((TR_ANY_INTEGER, TR_ANY_INTEGER), DT_PASS)
    #FLOAT = OpToVectorOp((TR_ANY_FLOAT, TR_ANY_FLOAT), DT_PASS)
    #FLOAT_UNARY = OpToVectorOp((TR_ANY_FLOAT,), DT_PASS)
    #LOAD = LoadToVectorLoad()
    #STORE = StoreToVectorStore()
    #GUARD = PassThroughOp((TR_ANY_INTEGER,))

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

    # TODO?
    UNSIGNED_OPS = (rop.UINT_FLOORDIV, rop.UINT_RSHIFT,
                    rop.UINT_LT, rop.UINT_LE,
                    rop.UINT_GT, rop.UINT_GE)

def turn_into_vector(state, pack):
    """ Turn a pack into a vector instruction """
    #
    # TODO self.check_if_pack_supported(pack)
    op = pack.leftmost()
    args = op.getarglist()
    prepare_arguments(state, pack, args)
    vop = VecOperation(op.vector, args, op, pack.numops(), op.getdescr())
    for i,node in enumerate(pack.operations):
        op = node.getoperation()
        state.setvector_of_box(op,i,vop)
    #
    if op.is_guard():
        assert isinstance(op, GuardResOp)
        assert isinstance(vop, GuardResOp)
        vop.setfailargs(op.getfailargs())
        vop.rd_snapshot = op.rd_snapshot
    state.costmodel.record_pack_savings(pack, pack.numops())
    #
    if pack.is_accumulating():
        box = oplist[position].result
        assert box is not None
        for node in pack.operations:
            op = node.getoperation()
            assert not op.returns_void()
            state.renamer.start_renaming(op, box)
    #
    state.oplist.append(vop)


def prepare_arguments(state, pack, args):
    # Transforming one argument to a vector box argument
    # The following cases can occur:
    # 1) argument is present in the box_to_vbox map.
    #    a) vector can be reused immediatly (simple case)
    #    b) an operation forces the unpacking of a vector
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
        if arg.returns_vector():
            continue
        pos, vecop = state.getvector_of_box(arg)
        if not vecop:
            # 2) constant/variable expand this box
            expand(state, pack, args, arg, i)
            continue
        args[i] = vecop
        assemble_scattered_values(state, pack, args, i)
        position_values(state, pack, args, i, pos)

def assemble_scattered_values(state, pack, args, index):
    vectors = pack.argument_vectors(state, pack, index)
    if len(vectors) > 1:
        # the argument is scattered along different vector boxes
        args[index] = gather(state, vectors, pack.numops())
        state.remember_args_in_vector(pack, index, args[index])

def gather(state, vectors, count): # packed < packable and packed < stride:
    (_, arg) = vectors[0]
    i = 1
    while i < len(vectors):
        (newarg_pos, newarg) = vectors[i]
        if arg.count + newarg.count <= count:
            arg = pack_into_vector(state, arg, arg.count, newarg, newarg_pos, newarg.count)
        i += 1
    return arg

def position_values(state, pack, args, index, position):
    if position != 0:
        # The vector box is at a position != 0 but it
        # is required to be at position 0. Unpack it!
        arg = args[index]
        args[index] = unpack_from_vector(state, arg, position, arg.count - position)
        state.remember_args_in_vector(pack, index, args[index])

        # convert size i64 -> i32, i32 -> i64, ...
        # TODO if self.bytesize > 0:
        #   determine_trans(
        #   self.input_type.getsize() != vecop.getsize():
        #    vecop = self.extend(vecop, self.input_type)

        # use the input as an indicator for the pack type
        #packable = vecop.maximum_numops()
        #packed = vecop.count
        #assert packed >= 0
        #assert packable >= 0
        #if packed > packable:
        #    # the argument has more items than the operation is able to process!
        #    # pos == 0 then it is already at the right place
        #    if pos != 0:
        #        args[i] = self.unpack(vecop, pos, packed - pos, self.input_type)
        #        state.remember_args_in_vector(i, args[i])
        #        #self.update_input_output(self.pack)
        #        continue
        #    else:
        #        assert vecop is not None
        #        args[i] = vecop
        #        continue
        #vboxes = self.vector_boxes_for_args(i)
        #if packed < packable and len(vboxes) > 1:
        #    # the argument is scattered along different vector boxes
        #    args[i] = self.gather(vboxes, packable)
        #    state.remember_args_in_vector(i, args[i])
        #    continue
        #if pos != 0:
        #    # The vector box is at a position != 0 but it
        #    # is required to be at position 0. Unpack it!
        #    args[i] = self.unpack(vecop, pos, packed - pos, self.input_type)
        #    state.remember_args_in_vector(i, args[i])
        #    continue
        ##
        #assert vecop is not None
        #args[i] = vecop

def check_if_pack_supported(self, pack):
    op0 = pack.operations[0].getoperation()
    if self.input_type is None:
        # must be a load/guard op
        return
    insize = self.input_type.getsize()
    if op0.is_typecast():
        # prohibit the packing of signext calls that
        # cast to int16/int8.
        _, outsize = op0.cast_to()
        self.sched_data._prevent_signext(outsize, insize)
    if op0.getopnum() == rop.INT_MUL:
        if insize == 8 or insize == 1:
            # see assembler for comment why
            raise NotAProfitableLoop

def extend(self, vbox, newtype):
    assert vbox.gettype() == newtype.gettype()
    if vbox.gettype() == INT:
        return self.extend_int(vbox, newtype)
    else:
        raise NotImplementedError("cannot yet extend float")

def extend_int(self, vbox, newtype):
    vbox_cloned = newtype.new_vector_box(vbox.getcount())
    self.sched_data._prevent_signext(newtype.getsize(), vbox.getsize())
    newsize = newtype.getsize()
    assert newsize > 0
    op = ResOperation(rop.VEC_INT_SIGNEXT, 
                      [vbox, ConstInt(newsize)],
                      vbox_cloned)
    self.costmodel.record_cast_int(vbox.getsize(), newtype.getsize(), vbox.getcount())
    self.vecops.append(op)
    return vbox_cloned

def unpack_from_vector(state, arg, index, count):
    """ Extract parts of the vector box into another vector box """
    print "unpack i", index, "c", count, "v", arg
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
        #expanded_map.setdefault(arg,[]).append((vecop, -1))
        #for i in range(vecop.count):
        #    state.setvector_of_box(arg, i, vecop)
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
        self.seen = {}

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

    def post_schedule(self):
        loop = self.graph.loop
        self.ensure_args_unpacked(loop.jump)
        SchedulerState.post_schedule(self)

        # add accumulation info to the descriptor
        #for version in self.loop.versions:
        #    # this needs to be done for renamed (accum arguments)
        #    version.renamed_inputargs = [ renamer.rename_map.get(arg,arg) for arg in version.inputargs ]
        #self.appended_arg_count = len(sched_data.invariant_vector_vars)
        ##for guard_node in graph.guards:
        ##    op = guard_node.getoperation()
        ##    failargs = op.getfailargs()
        ##    for i,arg in enumerate(failargs):
        ##        if arg is None:
        ##            continue
        ##        accum = arg.getaccum()
        ##        if accum:
        ##            pass
        ##            #accum.save_to_descr(op.getdescr(),i)
        #self.has_two_labels = len(sched_data.invariant_oplist) > 0
        #self.loop.operations = self.prepend_invariant_operations(sched_data)


    def profitable(self):
        return self.costmodel.profitable()

    def prepare(self):
        SchedulerState.prepare(self)
        for node in self.graph.nodes:
            if node.depends_count() == 0:
                self.worklist.insert(0, node)

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
                        fail_arguments[i] = arg

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
    """ how many operations of that kind can one execute
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

    def __init__(self, ops):
        self.operations = ops
        self.accum = None
        self.update_pack_of_nodes()

    def numops(self):
        return len(self.operations)

    def leftmost(self):
        return self.operations[0].getoperation()

    def rightmost(self):
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
        print "splitting pack", self
        pack = self
        while pack.pack_load(vec_reg_size) > Pack.FULL:
            pack.clear()
            oplist, newoplist = pack.slice_operations(vec_reg_size)
            print "  split of %dx, left: %d" % (len(oplist), len(newoplist))
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
        print "  => %dx packs out of %d operations" % (-before_count + len(packlist) + 1, sum([pack.numops() for pack in packlist[before_count:]]))
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
        accum = True
        if self.is_accumulating():
            if not other.is_accumulating():
                accum = False
            elif self.accum.pos != other.accum.pos:
                accum = False
        return rightmost is leftmost and accum

    def argument_vectors(self, state, pack, index):
        args = [node.getoperation().getarg(index) for node in pack.operations]
        vectors = []
        last = None
        for arg in args:
            pos, vecop = state.getvector_of_box(arg)
            if vecop is not last and vecop is not None:
                vectors.append((pos, vecop))
                last = vecop
        return vectors

    def __repr__(self):
        if len(self.operations) == 0:
            return "Pack(empty)"
        return "Pack(%dx %s)" % (self.numops(), self.operations[0])

    def is_accumulating(self):
        return self.accum is not None

    def clone(self, oplist):
        cloned = Pack(oplist)
        cloned.accum = self.accum
        return cloned


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
            return self.left is other.left and \
                   self.right is other.right

class AccumPair(Pair):
    """ A pair that keeps track of an accumulation value """
    def __init__(self, left, right, input_type, output_type, accum):
        assert isinstance(left, Node)
        assert isinstance(right, Node)
        Pair.__init__(self, left, right, input_type, output_type)
        self.left = left
        self.right = right
        self.accum = accum

#class OpToVectorOp(object):
#    def __init__(self): #, restrictargs, typeoutput):
#        pass
#        #self.args = list(restrictargs) # do not use a tuple. rpython cannot union
#        #self.out = typeoutput
#
#class OpToVectorOpConv(OpToVectorOp):
#    def __init__(self, intype, outtype):
#        #self.from_size = intype.getsize()
#        #self.to_size = outtype.getsize()
#        #OpToVectorOp.__init__(self, (intype, ), outtype)
#        pass
#
#    def new_result_vector_box(self):
#        type = self.output_type.gettype()
#        size = self.to_size
#        count = self.output_type.getcount()
#        vec_reg_size = self.sched_data.vec_reg_size
#        if count * size > vec_reg_size:
#            count = vec_reg_size // size
#        signed = self.output_type.signed
#        assert type in ('i','f')
#        assert size > 0
#        assert count > 1
#        return BoxVector(type, count, size, signed)
#
#    def get_output_type_given(self, input_type, op):
#        return self.result_ptype
#
#    def get_input_type_given(self, output_type, op):
#        return self.arg_ptypes[0]
#
#    def force_input(self, ptype):
#        return self.arg_ptypes[0]
#
#class SignExtToVectorOp(OpToVectorOp):
#    def __init__(self, intype, outtype):
#        OpToVectorOp.__init__(self, intype, outtype)
#        self.size = -1
#
#    def before_argument_transform(self, args):
#        sizearg = args[1]
#        assert isinstance(sizearg, ConstInt)
#        self.size = sizearg.value
#
#    def new_result_vector_box(self):
#        type = self.output_type.gettype()
#        count = self.input_type.getcount()
#        vec_reg_size = self.sched_data.vec_reg_size
#        if count * self.size > vec_reg_size:
#            count = vec_reg_size // self.size
#        signed = self.input_type.signed
#        assert type in ('i','f')
#        assert self.size > 0
#        assert count > 1
#        return BoxVector(type, count, self.size, signed)
#
#    def get_output_type_given(self, input_type, op):
#        sizearg = op.getarg(1)
#        assert isinstance(sizearg, ConstInt)
#        output_type = input_type.clone()
#        output_type.setsize(sizearg.value)
#        return output_type
#
#    def get_input_type_given(self, output_type, op):
#        raise AssertionError("can never infer input type!")
#
#class LoadToVectorLoad(OpToVectorOp):
#    def __init__(self):
#        OpToVectorOp.__init__(self, (), TypeRestrict())
#
#    # OLD def before_argument_transform(self, args):
#        #count = min(self.output_type.getcount(), len(self.getoperations()))
#        #args.append(ConstInt(count))
#
#    def get_output_type_given(self, input_type, op):
#        return xxx#Type.by_descr(op.getdescr(), self.sched_data.vec_reg_size)
#
#    def get_input_type_given(self, output_type, op):
#        return None
#
#class StoreToVectorStore(OpToVectorOp):
#    """ Storing operations are special because they are not allowed
#        to store to memory if the vector is not fully filled.
#        Thus a modified split_pack function.
#    """
#    def __init__(self):
#        OpToVectorOp.__init__(self, (None, None, TypeRestrict()), None)
#        self.has_descr = True
#
#    def must_be_full_but_is_not(self, pack):
#        vrs = self.sched_data.vec_reg_size
#        it = pack.input_type
#        return it.getsize() * it.getcount() < vrs
#
#    def get_output_type_given(self, input_type, op):
#        return None
#
#    def get_input_type_given(self, output_type, op):
#        return xxx#Type.by_descr(op.getdescr(), self.sched_data.vec_reg_size)
#
#class PassThroughOp(OpToVectorOp):
#    """ This pass through is only applicable if the target
#        operation is capable of handling vector operations.
#        Guard true/false is such an example.
#    """
#    def __init__(self, args):
#        OpToVectorOp.__init__(self, args, None)
#
#    def get_output_type_given(self, input_type, op):
#        return None
#
#    def get_input_type_given(self, output_type, op):
#        raise AssertionError("cannot infer input type from output type")
#
#
#
##def determine_input_output_types(pack, node, forward):
##    """ This function is two fold. If moving forward, it
##        gets an input type from the packs output type and returns
##        the transformed packtype.
##
##        Moving backward, the origins pack input type is the output
##        type and the transformation of the packtype (in reverse direction)
##        is the input
##    """
##    op = node.getoperation()
##    op2vecop = determine_trans(op)
##    if forward:
##        input_type = op2vecop.force_input(pack.output_type)
##        output_type = op2vecop.get_output_type_given(input_type, op)
##        if output_type:
##            output_type = output_type.clone()
##    else:
##        # going backwards, things are not that easy anymore
##        output_type = pack.input_type
##        input_type = op2vecop.get_input_type_given(output_type, op)
##        if input_type:
##            input_type = input_type.clone()
##
##    return input_type, output_type
#
#def determine_trans(op):
#    op2vecop = trans.MAPPING.get(op.vector, None)
#    if op2vecop is None:
#        raise NotImplementedError("missing vecop for '%s'" % (op.getopname(),))
#    return op2vecop


#def before_argument_transform(self, args):
#    pass

#def transform_result(self, result):
#    if result is None:
#        return None
#    vbox = self.new_result_vector_box()
#    #
#    # mark the position and the vbox in the hash
#    for i, node in enumerate(self.getoperations()):
#        if i >= vbox.getcount():
#            break
#        op = node.getoperation()
#        self.sched_data.setvector_of_box(op, i, vbox)
#    return vbox

#def new_result_vector_box(self):
#    type = self.output_type.gettype()
#    size = self.output_type.getsize()
#    count = min(self.output_type.getcount(), len(self.pack.operations))
#    signed = self.output_type.signed
#    return BoxVector(type, count, size, signed)

#def getoperations(self):
#    return self.pack.operations

#def transform_arguments(self, args):
#    """ Transforming one argument to a vector box argument
#        The following cases can occur:
#        1) argument is present in the box_to_vbox map.
#           a) vector can be reused immediatly (simple case)
#           b) vector is to big
#           c) vector is to small
#        2) argument is not known to reside in a vector
#           a) expand vars/consts before the label and add as argument
#           b) expand vars created in the loop body
#    """
#    for i,arg in enumerate(args):
#        if arg.returns_vector():
#            continue
#        if not self.is_vector_arg(i):
#            continue
#        box_pos, vbox = self.sched_data.getvector_of_box(arg)
#        if not vbox:
#            # constant/variable expand this box
#            vbox = self.expand(arg, i)
#            self.sched_data.setvector_of_box(arg, 0, vbox)
#            box_pos = 0
#        # convert size i64 -> i32, i32 -> i64, ...
#        if self.input_type.getsize() > 0 and \
#           self.input_type.getsize() != vbox.getsize():
#            vbox = self.extend(vbox, self.input_type)

#        # use the input as an indicator for the pack type
#        packable = self.input_type.getcount()
#        packed = vbox.getcount()
#        assert packed >= 0
#        assert packable >= 0
#        if packed > packable:
#            # the argument has more items than the operation is able to process!
#            # box_pos == 0 then it is already at the right place
#            if box_pos != 0:
#                args[i] = self.unpack(vbox, box_pos, packed - box_pos, self.input_type)
#                remember_args_in_vector(i, args[i])
#                #self.update_input_output(self.pack)
#                continue
#            else:
#                assert vbox is not None
#                args[i] = vbox
#                continue
#        vboxes = self.vector_boxes_for_args(i)
#        if packed < packable and len(vboxes) > 1:
#            # the argument is scattered along different vector boxes
#            args[i] = self.gather(vboxes, packable)
#            remember_args_in_vector(i, args[i])
#            continue
#        if box_pos != 0:
#            # The vector box is at a position != 0 but it
#            # is required to be at position 0. Unpack it!
#            args[i] = self.unpack(vbox, box_pos, packed - box_pos, self.input_type)
#            remember_args_in_vector(i, args[i])
#            continue
#            #self.update_input_output(self.pack)
#        #
#        assert vbox is not None
#        args[i] = vbox
