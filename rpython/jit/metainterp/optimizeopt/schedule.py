
from rpython.jit.metainterp.history import (VECTOR,FLOAT,INT,ConstInt,BoxVector,
        BoxFloat,BoxInt,ConstFloat,TargetToken,Box)
from rpython.jit.metainterp.resoperation import (rop, ResOperation, GuardResOp)
from rpython.jit.metainterp.optimizeopt.dependency import (DependencyGraph,
        MemoryRef, Node, IndexVar)
from rpython.jit.metainterp.optimizeopt.util import Renamer
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.jitexc import NotAProfitableLoop


class SchedulerData(object):
    pass
class Scheduler(object):
    def __init__(self, graph, sched_data):
        assert isinstance(sched_data, SchedulerData)
        self.graph = graph
        self.schedulable_nodes = self.graph.schedulable_nodes
        self.sched_data = sched_data
        self.oplist = None
        self.renamer = None

    def has_more(self):
        return len(self.schedulable_nodes) > 0

    def next_index(self, candidate_list):
        i = len(candidate_list)-1
        while i >= 0:
            candidate = candidate_list[i]
            if candidate.emitted:
                del candidate_list[i]
                i -= 1
                continue
            if self.schedulable(candidate):
                return i
            i -= 1
        return -1

    def schedulable(self, candidate):
        if candidate.pack:
            pack = candidate.pack
            if pack.is_accumulating():
                for node in pack.operations:
                    for dep in node.depends():
                        if dep.to.pack is not pack:
                            return False
                return True
            else:
                for node in candidate.pack.operations:
                    if node.depends_count() > 0:
                        return False
        return candidate.depends_count() == 0

    def scheduled(self, node):
        node.position = len(self.oplist)
        for dep in node.provides()[:]: # COPY
            to = dep.to
            node.remove_edge_to(to)
            nodes = self.schedulable_nodes
            if not to.emitted and to.depends_count() == 0:
                # sorts them by priority
                i = len(nodes)-1
                while i >= 0:
                    itnode = nodes[i]
                    c = (itnode.priority - to.priority)
                    if c < 0: # meaning itnode.priority < to.priority:
                        nodes.insert(i+1, to)
                        break
                    elif c == 0:
                        # if they have the same priority, sort them
                        # using the original position in the trace
                        if itnode.getindex() < to.getindex():
                            nodes.insert(i, to)
                            break
                    i -= 1
                else:
                    nodes.insert(0, to)
        node.clear_dependencies()
        node.emitted = True

    def emit_into(self, oplist, renamer, unpack=False):
        self.renamer = renamer
        self.oplist = oplist
        self.unpack = unpack

        while self.has_more():
            i = self.next_index(self.schedulable_nodes)
            if i >= 0:
                candidate = self.schedulable_nodes[i]
                del self.schedulable_nodes[i]
                self.sched_data.schedule_candidate(self, candidate)
                continue

            # it happens that packs can emit many nodes that have been
            # added to the scheuldable_nodes list, in this case it could
            # be that no next exists even though the list contains elements
            if not self.has_more():
                break

            raise AssertionError("schedule failed cannot continue. possible reason: cycle")

        jump_node = self.graph.nodes[-1]
        jump_op = jump_node.getoperation()
        renamer.rename(jump_op)
        assert jump_op.getopnum() == rop.JUMP
        self.sched_data.unpack_from_vector(jump_op, self)
        oplist.append(jump_op)

def vectorbox_outof_box(box, count=-1, size=-1, type='-'):
    if box.type not in (FLOAT, INT):
        raise AssertionError("cannot create vector box of type %s" % (box.type))
    signed = True
    if box.type == FLOAT:
        signed = False
    return BoxVector(box.type, 2, 8, signed)

def packtype_outof_box(box):
    if box.type == VECTOR:
        return PackType.of(box)
    else:
        if box.type == INT:
            return PackType(INT, 8, True, 2)
        elif box.type == FLOAT:
            return PackType(FLOAT, 8, False, 2)
    #
    raise AssertionError("box %s not supported" % (box,))

def vectorbox_clone_set(box, count=-1, size=-1, type='-', clone_signed=True, signed=False):
    if count == -1:
        count = box.getcount()
    if size == -1:
        size = box.getsize()
    if type == '-':
        type = box.gettype()
    if clone_signed:
        signed = box.getsigned()
    return BoxVector(type, count, size, signed)

def getpackopnum(type):
    if type == INT:
        return rop.VEC_INT_PACK
    elif type == FLOAT:
        return rop.VEC_FLOAT_PACK
    #
    raise AssertionError("getpackopnum type %s not supported" % (type,))

def getunpackopnum(type):
    if type == INT:
        return rop.VEC_INT_UNPACK
    elif type == FLOAT:
        return rop.VEC_FLOAT_UNPACK
    #
    raise AssertionError("getunpackopnum type %s not supported" % (type,))

def getexpandopnum(type):
    if type == INT:
        return rop.VEC_INT_EXPAND
    elif type == FLOAT:
        return rop.VEC_FLOAT_EXPAND
    #
    raise AssertionError("getexpandopnum type %s not supported" % (type,))

class PackType(object):
    """ Represents the type of an operation (either it's input or
    output).
    """
    UNKNOWN_TYPE = '-'

    @staticmethod
    def of(box, count=-1):
        assert isinstance(box, BoxVector)
        if count == -1:
            count = box.getcount()
        return PackType(box.gettype(), box.getsize(), box.getsigned(), count)

    @staticmethod
    def by_descr(descr, vec_reg_size):
        _t = INT
        signed = descr.is_item_signed()
        if descr.is_array_of_floats() or descr.concrete_type == FLOAT:
            _t = FLOAT
            signed = False
        size = descr.get_item_size_in_bytes()
        pt = PackType(_t, size, signed, vec_reg_size // size)
        return pt

    def __init__(self, type, size, signed, count=-1):
        assert type in (FLOAT, INT, PackType.UNKNOWN_TYPE)
        self.type = type
        self.size = size
        self.signed = signed
        self.count = count

    def clone(self):
        return PackType(self.type, self.size, self.signed, self.count)

    def new_vector_box(self, count = -1):
        if count == -1:
            count = self.count
        assert count > 1
        assert self.type in ('i','f')
        assert self.size > 0
        return BoxVector(self.type, count, self.size, self.signed)

    def combine(self, other):
        """ nothing to be done here """
        if not we_are_translated():
            assert self.type == other.type
            assert self.signed == other.signed

    def __repr__(self):
        return 'PackType(%s, %d, %d, #%d)' % (self.type, self.size, self.signed, self.count)

    def byte_size(self):
        return self.count * self.size

    def setsize(self, size):
        self.size = size

    def setcount(self, count):
        self.count = count

    def gettype(self):
        return self.type

    def getsize(self):
        return self.size

    def getcount(self):
        return self.count


PT_GENERIC = PackType(PackType.UNKNOWN_TYPE, -1, False)
PT_FLOAT_2 = PackType(FLOAT, 4, False, 2)
PT_DOUBLE_2 = PackType(FLOAT, 8, False, 2)
PT_FLOAT_GENERIC = PackType(INT, -1, False)
PT_INT64 = PackType(INT, 8, True)
PT_INT32_2 = PackType(INT, 4, True, 2)
PT_INT_GENERIC = PackType(INT, -1, True)

INT_RES = PT_INT_GENERIC
FLOAT_RES = PT_FLOAT_GENERIC

class OpToVectorOp(object):
    def __init__(self, arg_ptypes, result_ptype):
        self.arg_ptypes = [a for a in arg_ptypes] # do not use a tuple. rpython cannot union
        self.result_ptype = result_ptype
        self.vecops = None
        self.sched_data = None
        self.pack = None
        self.input_type = None
        self.output_type = None
        self.costmodel = None

    def as_vector_operation(self, pack, sched_data, scheduler, oplist):
        self.sched_data = sched_data
        self.vecops = oplist
        self.costmodel = sched_data.costmodel
        #
        self.input_type = pack.input_type
        self.output_type = pack.output_type
        #
        self.check_if_pack_supported(pack)

        #
        if self.must_be_full_but_is_not(pack):
            for op in pack.operations:
                operation = op.getoperation()
                self.sched_data.unpack_from_vector(operation, scheduler)
                self.vecops.append(operation)
        else:
            self.pack = pack
            self.transform_pack()
        #
        self.pack = None
        self.costmodel = None
        self.vecops = None
        self.sched_data = None
        self.input_type = None
        self.output_type = None

    def must_be_full_but_is_not(self, pack):
        return False

    def before_argument_transform(self, args):
        pass

    def check_if_pack_supported(self, pack):
        op0 = pack.operations[0].getoperation()
        if self.input_type is None:
            # must be a load/guard op
            return
        insize = self.input_type.getsize()
        if op0.casts_box():
            # prohibit the packing of signext calls that
            # cast to int16/int8.
            _, outsize = op0.cast_to()
            self.sched_data._prevent_signext(outsize, insize)
        if op0.getopnum() == rop.INT_MUL:
            if insize == 8 or insize == 1:
                # see assembler for comment why
                raise NotAProfitableLoop


    def transform_pack(self):
        op = self.pack.leftmost()
        args = op.getarglist()
        self.before_argument_transform(args)
        self.transform_arguments(args)
        #
        result = op.result
        result = self.transform_result(result)
        #
        vop = ResOperation(op.vector, args, result, op.getdescr())
        if op.is_guard():
            assert isinstance(op, GuardResOp)
            assert isinstance(vop, GuardResOp)
            vop.setfailargs(op.getfailargs())
            vop.rd_snapshot = op.rd_snapshot
        self.vecops.append(vop)
        self.costmodel.record_pack_savings(self.pack, self.pack.opcount())

    def transform_result(self, result):
        if result is None:
            return None
        vbox = self.new_result_vector_box()
        #
        # mark the position and the vbox in the hash
        for i, node in enumerate(self.getoperations()):
            if i >= vbox.getcount():
                break
            op = node.getoperation()
            self.sched_data.setvector_of_box(op.result, i, vbox)
        return vbox

    def new_result_vector_box(self):
        type = self.output_type.gettype()
        size = self.output_type.getsize()
        count = min(self.output_type.getcount(), len(self.pack.operations))
        signed = self.output_type.signed
        return BoxVector(type, count, size, signed)

    def getoperations(self):
        return self.pack.operations

    def transform_arguments(self, args):
        for i,arg in enumerate(args):
            if isinstance(arg, BoxVector):
                continue
            if not self.is_vector_arg(i):
                continue
            box_pos, vbox = self.sched_data.getvector_of_box(arg)
            if not vbox:
                # constant/variable expand this box
                vbox = self.expand(arg, i)
                self.sched_data.setvector_of_box(arg, 0, vbox)
                box_pos = 0
            # convert size i64 -> i32, i32 -> i64, ...
            if self.input_type.getsize() > 0 and \
               self.input_type.getsize() != vbox.getsize():
                vbox = self.extend(vbox, self.input_type)

            # use the input as an indicator for the pack type
            packable = self.input_type.getcount()
            packed = vbox.getcount()
            assert packed >= 0
            assert packable >= 0
            if packed > packable:
                # the argument has more items than the operation is able to process!
                # box_pos == 0 then it is already at the right place
                if box_pos != 0:
                    args[i] = self.unpack(vbox, box_pos, packed - box_pos, self.input_type)
                    self.update_arg_in_vector_pos(i, args[i])
                    #self.update_input_output(self.pack)
                    continue
                else:
                    assert vbox is not None
                    args[i] = vbox
                    continue
            vboxes = self.vector_boxes_for_args(i)
            if packed < packable and len(vboxes) > 1:
                # the argument is scattered along different vector boxes
                args[i] = self.gather(vboxes, packable)
                self.update_arg_in_vector_pos(i, args[i])
                continue
            if box_pos != 0:
                # The vector box is at a position != 0 but it
                # is required to be at position 0. Unpack it!
                args[i] = self.unpack(vbox, box_pos, packed - box_pos, self.input_type)
                self.update_arg_in_vector_pos(i, args[i])
                continue
                #self.update_input_output(self.pack)
            #
            assert vbox is not None
            args[i] = vbox

    def gather(self, vboxes, target_count): # packed < packable and packed < stride:
        (_, box) = vboxes[0]
        i = 1
        while i < len(vboxes):
            (box2_pos, box2) = vboxes[i]
            if box.getcount() + box2.getcount() <= target_count:
                box = self.package(box, box.getcount(),
                                   box2, box2_pos, box2.getcount())
            i += 1
        return box

    def update_arg_in_vector_pos(self, argidx, box):
        arguments = [op.getoperation().getarg(argidx) for op in self.getoperations()]
        for i,arg in enumerate(arguments):
            if i >= box.getcount():
                break
            self.sched_data.setvector_of_box(arg, i, box)

    def vector_boxes_for_args(self, index):
        args = [op.getoperation().getarg(index) for op in self.getoperations()]
        vboxes = []
        last_vbox = None
        for arg in args:
            pos, vbox = self.sched_data.getvector_of_box(arg)
            if vbox is not last_vbox and vbox is not None:
                vboxes.append((pos, vbox))
                last_vbox = vbox
        return vboxes


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

    def unpack(self, vbox, index, count, arg_ptype):
        assert index < vbox.getcount()
        assert index + count <= vbox.getcount()
        assert count > 0
        vbox_cloned = vectorbox_clone_set(vbox, count=count)
        opnum = getunpackopnum(vbox.gettype())
        op = ResOperation(opnum, [vbox, ConstInt(index), ConstInt(count)], vbox_cloned)
        self.costmodel.record_vector_unpack(vbox, index, count)
        self.vecops.append(op)
        #
        return vbox_cloned

    def package(self, tgt, tidx, src, sidx, scount):
        """ tgt = [1,2,3,4,_,_,_,_]
            src = [5,6,_,_]
            new_box = [1,2,3,4,5,6,_,_] after the operation, tidx=4, scount=2
        """
        assert sidx == 0 # restriction
        count = tgt.getcount() + src.getcount()
        new_box = vectorbox_clone_set(tgt, count=count)
        opnum = getpackopnum(tgt.gettype())
        op = ResOperation(opnum, [tgt, src, ConstInt(tidx), ConstInt(scount)], new_box)
        self.vecops.append(op)
        self.costmodel.record_vector_pack(src, sidx, scount)
        if not we_are_translated():
            self._check_vec_pack(op)
        return new_box

    def _check_vec_pack(self, op):
        result = op.result
        arg0 = op.getarg(0)
        arg1 = op.getarg(1)
        index = op.getarg(2)
        count = op.getarg(3)
        assert isinstance(result, BoxVector)
        assert isinstance(arg0, BoxVector)
        assert isinstance(index, ConstInt)
        assert isinstance(count, ConstInt)
        assert arg0.getsize() == result.getsize()
        if isinstance(arg1, BoxVector):
            assert arg1.getsize() == result.getsize()
        else:
            assert count.value == 1
        assert index.value < result.getcount()
        assert index.value + count.value <= result.getcount()
        assert result.getcount() > arg0.getcount()

    def expand(self, arg, argidx):
        elem_count = self.input_type.getcount()
        vbox = self.input_type.new_vector_box(elem_count)
        box_type = arg.type
        expanded_map = self.sched_data.expanded_map
        # note that heterogenous nodes are not yet tracked
        already_expanded = expanded_map.get(arg, None)
        if already_expanded:
            return already_expanded

        ops = self.sched_data.invariant_oplist
        variables = self.sched_data.invariant_vector_vars
        if isinstance(arg,Box) and arg not in self.sched_data.inputargs:
            ops = self.vecops
            variables = None
        if isinstance(arg, BoxVector):
            box_type = arg.gettype()

        for i, node in enumerate(self.getoperations()):
            op = node.getoperation()
            if not arg.same_box(op.getarg(argidx)):
                break
            i += 1
        else:
            expand_opnum = getexpandopnum(box_type)
            op = ResOperation(expand_opnum, [arg, ConstInt(vbox.item_count)], vbox)
            ops.append(op)
            if variables is not None:
                variables.append(vbox)
            expanded_map[arg] = vbox
            return vbox

        op = ResOperation(rop.VEC_BOX, [ConstInt(elem_count)], vbox)
        ops.append(op)
        opnum = getpackopnum(arg.type)
        for i,node in enumerate(self.getoperations()):
            op = node.getoperation()
            arg = op.getarg(argidx)
            new_box = vbox.clonebox()
            ci = ConstInt(i)
            c1 = ConstInt(1)
            op = ResOperation(opnum, [vbox,arg,ci,c1], new_box)
            vbox = new_box
            ops.append(op)

        if variables is not None:
            variables.append(vbox)
        return vbox

    def is_vector_arg(self, i):
        if i < 0 or i >= len(self.arg_ptypes):
            return False
        return self.arg_ptypes[i] is not None

    def get_output_type_given(self, input_type, op):
        return input_type

    def get_input_type_given(self, output_type, op):
        return output_type

    def force_input(self, ptype):
        """ Some operations require a specific count/size,
            they can force the input type here!
        """
        return ptype

class OpToVectorOpConv(OpToVectorOp):
    def __init__(self, intype, outtype):
        self.from_size = intype.getsize()
        self.to_size = outtype.getsize()
        OpToVectorOp.__init__(self, (intype, ), outtype)

    def new_result_vector_box(self):
        type = self.output_type.gettype()
        size = self.to_size
        count = self.output_type.getcount()
        vec_reg_size = self.sched_data.vec_reg_size
        if count * size > vec_reg_size:
            count = vec_reg_size // size
        signed = self.output_type.signed
        assert type in ('i','f')
        assert size > 0
        assert count > 1
        return BoxVector(type, count, size, signed)

    def get_output_type_given(self, input_type, op):
        return self.result_ptype

    def get_input_type_given(self, output_type, op):
        return self.arg_ptypes[0]

    def force_input(self, ptype):
        return self.arg_ptypes[0]

class SignExtToVectorOp(OpToVectorOp):
    def __init__(self, intype, outtype):
        OpToVectorOp.__init__(self, intype, outtype)
        self.size = -1

    def before_argument_transform(self, args):
        sizearg = args[1]
        assert isinstance(sizearg, ConstInt)
        self.size = sizearg.value

    def new_result_vector_box(self):
        type = self.output_type.gettype()
        count = self.input_type.getcount()
        vec_reg_size = self.sched_data.vec_reg_size
        if count * self.size > vec_reg_size:
            count = vec_reg_size // self.size
        signed = self.input_type.signed
        assert type in ('i','f')
        assert self.size > 0
        assert count > 1
        return BoxVector(type, count, self.size, signed)

    def get_output_type_given(self, input_type, op):
        sizearg = op.getarg(1)
        assert isinstance(sizearg, ConstInt)
        output_type = input_type.clone()
        output_type.setsize(sizearg.value)
        return output_type

    def get_input_type_given(self, output_type, op):
        raise AssertionError("can never infer input type!")

class LoadToVectorLoad(OpToVectorOp):
    def __init__(self):
        OpToVectorOp.__init__(self, (), PT_GENERIC)

    def before_argument_transform(self, args):
        count = min(self.output_type.getcount(), len(self.getoperations()))
        args.append(ConstInt(count))

    def get_output_type_given(self, input_type, op):
        return PackType.by_descr(op.getdescr(), self.sched_data.vec_reg_size)

    def get_input_type_given(self, output_type, op):
        return None

class StoreToVectorStore(OpToVectorOp):
    """
    Storing operations are special because they are not allowed
    to store to memory if the vector is not fully filled.
    Thus a modified split_pack function
    """
    def __init__(self):
        OpToVectorOp.__init__(self, (None, None, PT_GENERIC), None)
        self.has_descr = True

    def must_be_full_but_is_not(self, pack):
        vrs = self.sched_data.vec_reg_size
        it = pack.input_type
        return it.getsize() * it.getcount() < vrs

    def get_output_type_given(self, input_type, op):
        return None

    def get_input_type_given(self, output_type, op):
        return PackType.by_descr(op.getdescr(), self.sched_data.vec_reg_size)

class PassThroughOp(OpToVectorOp):
    """ This pass through is only applicable if the target
    operation is capable of handling vector operations.
    Guard true/false is such an example.
    """
    def __init__(self, args):
        OpToVectorOp.__init__(self, args, None)

    def get_output_type_given(self, input_type, op):
        return None

    def get_input_type_given(self, output_type, op):
        raise AssertionError("cannot infer input type from output type")

    # OLD
    def determine_output_type(self, op):
        return None

GUARD_TF = PassThroughOp((PT_INT_GENERIC,))
INT_OP_TO_VOP = OpToVectorOp((PT_INT_GENERIC, PT_INT_GENERIC), INT_RES)
FLOAT_OP_TO_VOP = OpToVectorOp((PT_FLOAT_GENERIC, PT_FLOAT_GENERIC), FLOAT_RES)
FLOAT_SINGLE_ARG_OP_TO_VOP = OpToVectorOp((PT_FLOAT_GENERIC,), FLOAT_RES)
LOAD_TRANS = LoadToVectorLoad()
STORE_TRANS = StoreToVectorStore()

# note that the following definition is x86 arch specific
ROP_ARG_RES_VECTOR = {
    rop.VEC_INT_ADD:     INT_OP_TO_VOP,
    rop.VEC_INT_SUB:     INT_OP_TO_VOP,
    rop.VEC_INT_MUL:     INT_OP_TO_VOP,
    rop.VEC_INT_AND:     INT_OP_TO_VOP,
    rop.VEC_INT_OR:      INT_OP_TO_VOP,
    rop.VEC_INT_XOR:     INT_OP_TO_VOP,

    rop.VEC_INT_EQ:      INT_OP_TO_VOP,
    rop.VEC_INT_NE:      INT_OP_TO_VOP,

    rop.VEC_INT_SIGNEXT: SignExtToVectorOp((PT_INT_GENERIC,), INT_RES),

    rop.VEC_FLOAT_ADD:   FLOAT_OP_TO_VOP,
    rop.VEC_FLOAT_SUB:   FLOAT_OP_TO_VOP,
    rop.VEC_FLOAT_MUL:   FLOAT_OP_TO_VOP,
    rop.VEC_FLOAT_TRUEDIV:   FLOAT_OP_TO_VOP,
    rop.VEC_FLOAT_ABS:   FLOAT_SINGLE_ARG_OP_TO_VOP,
    rop.VEC_FLOAT_NEG:   FLOAT_SINGLE_ARG_OP_TO_VOP,
    rop.VEC_FLOAT_EQ:    OpToVectorOp((PT_FLOAT_GENERIC,PT_FLOAT_GENERIC), INT_RES),
    rop.VEC_FLOAT_NE:    OpToVectorOp((PT_FLOAT_GENERIC,PT_FLOAT_GENERIC), INT_RES),
    rop.VEC_INT_IS_TRUE: OpToVectorOp((PT_INT_GENERIC,PT_INT_GENERIC), PT_INT_GENERIC),

    rop.VEC_RAW_LOAD:         LOAD_TRANS,
    rop.VEC_GETARRAYITEM_RAW: LOAD_TRANS,
    rop.VEC_GETARRAYITEM_GC: LOAD_TRANS,
    rop.VEC_RAW_STORE:        STORE_TRANS,
    rop.VEC_SETARRAYITEM_RAW: STORE_TRANS,
    rop.VEC_SETARRAYITEM_GC: STORE_TRANS,

    rop.VEC_CAST_FLOAT_TO_SINGLEFLOAT: OpToVectorOpConv(PT_DOUBLE_2, PT_FLOAT_2),
    rop.VEC_CAST_SINGLEFLOAT_TO_FLOAT: OpToVectorOpConv(PT_FLOAT_2, PT_DOUBLE_2),
    rop.VEC_CAST_FLOAT_TO_INT: OpToVectorOpConv(PT_DOUBLE_2, PT_INT32_2),
    rop.VEC_CAST_INT_TO_FLOAT: OpToVectorOpConv(PT_INT32_2, PT_DOUBLE_2),

    rop.GUARD_TRUE: GUARD_TF,
    rop.GUARD_FALSE: GUARD_TF,
}

def determine_input_output_types(pack, node, forward):
    """ This function is two fold. If moving forward, it
    gets an input type from the packs output type and returns
    the transformed packtype.

    Moving backward, the origins pack input type is the output
    type and the transformation of the packtype (in reverse direction)
    is the input
    """
    op = node.getoperation()
    op2vecop = determine_trans(op)
    if forward:
        input_type = op2vecop.force_input(pack.output_type)
        output_type = op2vecop.get_output_type_given(input_type, op)
        if output_type:
            output_type = output_type.clone()
    else:
        # going backwards, things are not that easy anymore
        output_type = pack.input_type
        input_type = op2vecop.get_input_type_given(output_type, op)
        if input_type:
            input_type = input_type.clone()

    return input_type, output_type

def determine_trans(op):
    op2vecop = ROP_ARG_RES_VECTOR.get(op.vector, None)
    if op2vecop is None:
        raise NotImplementedError("missing vecop for '%s'" % (op.getopname(),))
    return op2vecop

class VecScheduleData(SchedulerData):
    def __init__(self, vec_reg_size, costmodel, inputargs):
        self.box_to_vbox = {}
        self.vec_reg_size = vec_reg_size
        self.invariant_oplist = []
        self.invariant_vector_vars = []
        self.expanded_map = {}
        self.costmodel = costmodel
        self.inputargs = {}
        for arg in inputargs:
            self.inputargs[arg] = None
        self.seen = {}

    def schedule_candidate(self, scheduler, candidate):
        """ if you implement a scheduler this operations is called
        to emit the actual operation into the oplist of the scheduler
        """
        renamer = scheduler.renamer
        if candidate.pack:
            for node in candidate.pack.operations:
                renamer.rename(node.getoperation())
                scheduler.scheduled(node)
            self.as_vector_operation(scheduler, candidate.pack)
        else:
            op = candidate.getoperation()
            renamer.rename(op)
            self.unpack_from_vector(op, scheduler)
            scheduler.scheduled(candidate)
            op = candidate.getoperation()
            #
            # prevent some instructions in the resulting trace!
            if op.getopnum() in (rop.DEBUG_MERGE_POINT,
                                 rop.GUARD_EARLY_EXIT):
                return
            scheduler.oplist.append(op)

    def as_vector_operation(self, scheduler, pack):
        assert pack.opcount() > 1
        # properties that hold for the pack are:
        # + isomorphism (see func above)
        # + tightly packed (no room between vector elems)

        oplist = scheduler.oplist
        position = len(oplist)
        op = pack.operations[0].getoperation()
        determine_trans(op).as_vector_operation(pack, self, scheduler, oplist)
        #
        # XXX
        if pack.is_accumulating():
            box = oplist[position].result
            assert box is not None
            for node in pack.operations:
                op = node.getoperation()
                assert op.result is not None
                scheduler.renamer.start_renaming(op.result, box)

    def unpack_from_vector(self, op, scheduler):
        args = op.getarglist()

        # unpack for an immediate use
        for i, arg in enumerate(op.getarglist()):
            if isinstance(arg, Box):
                argument = self._unpack_from_vector(i, arg, scheduler)
                if arg is not argument:
                    op.setarg(i, argument)
        if op.result:
            self.seen[op.result] = None
        # unpack for a guard exit
        if op.is_guard():
            fail_args = op.getfailargs()
            for i, arg in enumerate(fail_args):
                if arg and isinstance(arg, Box):
                    argument = self._unpack_from_vector(i, arg, scheduler)
                    if arg is not argument:
                        fail_args[i] = argument

    def _unpack_from_vector(self, i, arg, scheduler):
        if arg in self.seen or arg.type == 'V':
            return arg
        (j, vbox) = self.getvector_of_box(arg)
        if vbox:
            if vbox in self.invariant_vector_vars:
                return arg
            arg_cloned = arg.clonebox()
            self.seen[arg_cloned] = None
            scheduler.renamer.start_renaming(arg, arg_cloned)
            self.setvector_of_box(arg_cloned, j, vbox)
            cj = ConstInt(j)
            ci = ConstInt(1)
            opnum = getunpackopnum(vbox.gettype())
            unpack_op = ResOperation(opnum, [vbox, cj, ci], arg_cloned)
            self.costmodel.record_vector_unpack(vbox, j, 1)
            scheduler.oplist.append(unpack_op)
            return arg_cloned
        return arg

    def _prevent_signext(self, outsize, insize):
        if insize != outsize:
            if outsize < 4 or insize < 4:
                raise NotAProfitableLoop

    def getvector_of_box(self, arg):
        return self.box_to_vbox.get(arg, (-1, None))

    def setvector_of_box(self, box, off, vector):
        assert off < vector.getcount()
        assert not isinstance(box, BoxVector)
        self.box_to_vbox[box] = (off, vector)

    def prepend_invariant_operations(self, oplist, orig_label_args):
        if len(self.invariant_oplist) > 0:
            label = oplist[0]
            assert label.getopnum() == rop.LABEL
            #
            jump = oplist[-1]
            assert jump.getopnum() == rop.JUMP
            #
            label_args = label.getarglist()[:]
            jump_args = jump.getarglist()
            for var in self.invariant_vector_vars:
                label_args.append(var)
                jump_args.append(var)
            #
            # in case of any invariant_vector_vars, the label is restored
            # and the invariant operations are added between the original label
            # and the new label
            descr = label.getdescr()
            assert isinstance(descr, TargetToken)
            token = TargetToken(descr.targeting_jitcell_token)
            oplist[0] = label.copy_and_change(label.getopnum(), args=label_args, descr=token)
            oplist[-1] = jump.copy_and_change(jump.getopnum(), args=jump_args, descr=token)
            #
            return [ResOperation(rop.LABEL, orig_label_args, None, descr)] + \
                   self.invariant_oplist + oplist
        #
        return oplist

class Pack(object):
    """ A pack is a set of n statements that are:
        * isomorphic
        * independent
    """
    def __init__(self, ops, input_type, output_type):
        self.operations = ops
        self.accum = None
        self.input_type = input_type
        self.output_type = output_type
        assert self.input_type is not None or self.output_type is not None
        self.update_pack_of_nodes()

    def opcount(self):
        return len(self.operations)

    def leftmost(self):
        return self.operations[0].getoperation()

    def is_full(self, vec_reg_size):
        """ if one input element times the opcount is equal
        to the vector register size, we are full!
        """
        ptype = self.input_type
        if self.input_type is None:
            # load does not have an input type, but only an output type
            ptype = self.output_type

        op = self.leftmost()
        if op.casts_box():
            cur_bytes = ptype.getsize() * self.opcount()
            max_bytes = self.input_type.byte_size()
            assert cur_bytes <= max_bytes
            return cur_bytes == max_bytes

        bytes = ptype.getsize() * len(self.operations)
        assert bytes <= vec_reg_size
        if bytes == vec_reg_size:
            return True
        if ptype.getcount() != -1:
            size = ptype.getcount() * ptype.getsize()
            assert bytes <= size
            return bytes == size
        return False

    def opnum(self):
        assert len(self.operations) > 0
        return self.operations[0].getoperation().getopnum()

    def clear(self):
        for node in self.operations:
            if node.pack is not self:
                node.pack = None
                node.pack_position = -1

    def update_pack_of_nodes(self):
        for i,node in enumerate(self.operations):
            node.pack = self
            node.pack_position = i

    def rightmost_match_leftmost(self, other):
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

    def __repr__(self):
        opname = self.operations[0].getoperation().getopname()
        return "Pack(%s,%r)" % (opname, self.operations)

    def is_accumulating(self):
        return self.accum is not None

class Pair(Pack):
    """ A special Pack object with only two statements. """
    def __init__(self, left, right, input_type, output_type):
        assert isinstance(left, Node)
        assert isinstance(right, Node)
        self.left = left
        self.right = right
        if input_type:
            input_type = input_type.clone()
        if output_type:
            output_type = output_type.clone()
        Pack.__init__(self, [left, right], input_type, output_type)

    def __eq__(self, other):
        if isinstance(other, Pair):
            return self.left is other.left and \
                   self.right is other.right

class AccumPair(Pair):
    def __init__(self, left, right, input_type, output_type, accum):
        assert isinstance(left, Node)
        assert isinstance(right, Node)
        Pair.__init__(self, left, right, input_type, output_type)
        self.left = left
        self.right = right
        self.accum = accum
