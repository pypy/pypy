
from rpython.jit.metainterp.history import (VECTOR,FLOAT,INT,ConstInt,BoxVector,
        BoxFloat,BoxInt,ConstFloat)
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

    def has_more(self):
        return len(self.schedulable_nodes) > 0

    def next(self, renamer, position):
        i = self._next(self.schedulable_nodes)
        if i >= 0:
            candidate = self.schedulable_nodes[i]
            del self.schedulable_nodes[i]
            return self.schedule(candidate, renamer, position)

        raise AssertionError("schedule failed cannot continue. possible reason: cycle")

    def _next(self, candidate_list):
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

    def schedule(self, candidate, renamer, position):
        if candidate.pack:
            pack = candidate.pack
            for node in pack.operations:
                renamer.rename(node.getoperation())
            vops = self.sched_data.as_vector_operation(pack, renamer)
            for node in pack.operations:
                self.scheduled(node, position)
            return vops
        else:
            self.scheduled(candidate, position)
            renamer.rename(candidate.getoperation())
            return [candidate.getoperation()]

    def scheduled(self, node, position):
        node.position = position
        for dep in node.provides()[:]: # COPY
            to = dep.to
            node.remove_edge_to(to)
            if not to.emitted and to.depends_count() == 0:
                # sorts them by priority
                nodes = self.schedulable_nodes
                i = len(nodes)-1
                while i >= 0:
                    itnode = nodes[i]
                    if itnode.priority < to.priority:
                        nodes.insert(i+1, to)
                        break
                    i -= 1
                else:
                    nodes.insert(0, to)
        node.clear_dependencies()
        node.emitted = True

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
        count = box.item_count
    if size == -1:
        size = box.item_size
    if type == '-':
        type = box.item_type
    if clone_signed:
        signed = box.item_signed
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
    # TODO merge with vector box? the save the same fields
    # difference: this is more of a type specification
    UNKNOWN_TYPE = '-'

    def __init__(self, type, size, signed, count=-1):
        assert type in (FLOAT, INT, PackType.UNKNOWN_TYPE)
        self.type = type
        self.size = size
        self.signed = signed
        self.count = count

    def gettype(self):
        return self.type

    def getsize(self):
        return self.size

    def getsigned(self):
        return self.signed

    def get_byte_size(self):
        return self.size

    def getcount(self):
        return self.count

    @staticmethod
    def by_descr(descr, vec_reg_size):
        _t = INT
        if descr.is_array_of_floats() or descr.concrete_type == FLOAT:
            _t = FLOAT
        size = descr.get_item_size_in_bytes()
        pt = PackType(_t, size, descr.is_item_signed(), vec_reg_size // size)
        return pt

    def is_valid(self):
        return self.type != PackType.UNKNOWN_TYPE and self.size > 0

    def new_vector_box(self, count = -1):
        if count == -1:
            count = self.count
        return BoxVector(self.type, count, self.size, self.signed)

    def __repr__(self):
        return 'PackType(%s, %d, %d, #%d)' % (self.type, self.size, self.signed, self.count)

    @staticmethod
    def of(box, count=-1):
        assert isinstance(box, BoxVector)
        if count == -1:
            count = box.item_count
        return PackType(box.item_type, box.item_size, box.item_signed, count)

    def clone(self):
        return PackType(self.type, self.size, self.signed, self.count)


PT_FLOAT_2 = PackType(FLOAT, 4, False, 2)
PT_DOUBLE_2 = PackType(FLOAT, 8, False, 2)
PT_FLOAT_GENERIC = PackType(INT, -1, True)
PT_INT64 = PackType(INT, 8, True)
PT_INT32_2 = PackType(INT, 4, True, 2)
PT_INT_GENERIC = PackType(INT, -1, True)
PT_GENERIC = PackType(PackType.UNKNOWN_TYPE, -1, False)

INT_RES = PT_INT_GENERIC
FLOAT_RES = PT_FLOAT_GENERIC

class OpToVectorOp(object):
    def __init__(self, arg_ptypes, result_ptype):
        self.arg_ptypes = [a for a in arg_ptypes] # do not use a tuple. rpython cannot union
        self.result_ptype = result_ptype
        self.preamble_ops = None
        self.sched_data = None
        self.pack = None
        self.input_type = None
        self.output_type = None
        self.costmodel = None

    def determine_input_type(self, op):
        arg = op.getarg(0)
        _, vbox = self.sched_data.getvector_of_box(arg)
        return packtype_outof_box(vbox or arg)

    def determine_output_type(self, op):
        return self.determine_input_type(op)

    def update_input_output(self, pack):
        op0 = pack.operations[0].getoperation()
        self.input_type = self.determine_input_type(op0)
        self.output_type = self.determine_output_type(op0)

    def check_if_pack_supported(self, pack):
        op0 = pack.operations[0].getoperation()
        if self.input_type is None:
            # must be a load operation
            assert op0.is_raw_load()
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

    def as_vector_operation(self, pack, sched_data, oplist):
        self.sched_data = sched_data
        self.preamble_ops = oplist
        self.costmodel = sched_data.costmodel
        self.update_input_output(pack)
        #
        self.check_if_pack_supported(pack)
        #
        off = 0
        stride = self.split_pack(pack, self.sched_data.vec_reg_size)
        left = len(pack.operations)
        assert stride > 0
        while off < len(pack.operations):
            print left, "<", stride
            if stride == 1:
                op = pack.operations[off].getoperation()
                self.preamble_ops.append(op)
                off += 1
                continue
            ops = pack.operations[off:off+stride]
            self.pack = Pack(ops, pack.input_type, pack.output_type)
            self.costmodel.record_pack_savings(self.pack)
            self.transform_pack(ops, off, stride)
            off += stride
            left -= stride

        self.pack = None
        self.costmodel = None
        self.preamble_ops = None
        self.sched_data = None
        self.input_type = None
        self.output_type = None

    def split_pack(self, pack, vec_reg_size):
        """ Returns how many items of the pack should be
            emitted as vector operation. """
        bytes = pack.opcount() * self.getscalarsize()
        if bytes > vec_reg_size:
            # too many bytes. does not fit into the vector register
            return vec_reg_size // self.getscalarsize()
        return pack.opcount()

    def getscalarsize(self):
        """ return how many bytes a scalar operation processes """
        return self.input_type.getsize()

    def before_argument_transform(self, args):
        pass

    def transform_pack(self, ops, off, stride):
        op = self.pack.operations[0].getoperation()
        args = op.getarglist()
        #
        self.before_argument_transform(args)
        #
        for i,arg in enumerate(args):
            if isinstance(arg, BoxVector):
                continue
            if self.is_vector_arg(i):
                args[i] = self.transform_argument(args[i], i, off, stride)
        #
        result = op.result
        result = self.transform_result(result, off)
        #
        vop = ResOperation(op.vector, args, result, op.getdescr())
        if op.is_guard():
            assert isinstance(op, GuardResOp)
            vop.setfailargs(op.getfailargs())
            vop.rd_snapshot = op.rd_snapshot
        self.preamble_ops.append(vop)

    def transform_result(self, result, off):
        if result is None:
            return None
        vbox = self.new_result_vector_box()
        #
        # mark the position and the vbox in the hash
        for i, node in enumerate(self.pack.operations):
            op = node.getoperation()
            self.sched_data.setvector_of_box(op.result, i, vbox)
        return vbox

    def new_result_vector_box(self):
        type = self.output_type.gettype()
        size = self.output_type.getsize()
        count = min(self.output_type.getcount(), len(self.pack.operations))
        signed = self.output_type.signed
        return BoxVector(type, count, size, signed)

    def transform_argument(self, arg, argidx, off, stride):
        ops = self.pack.operations
        box_pos, vbox = self.sched_data.getvector_of_box(arg)
        if not vbox:
            # constant/variable expand this box
            vbox = self.expand(ops, arg, argidx)
            box_pos = 0
        # convert size i64 -> i32, i32 -> i64, ...
        if self.input_type.getsize() > 0 and \
           self.input_type.getsize() != vbox.getsize():
            vbox = self.extend(vbox, self.input_type)

        # use the input as an indicator for the pack type
        packable = self.input_type.getcount()
        packed = vbox.item_count
        assert packed >= 0
        assert packable >= 0
        vboxes = self.vector_boxes_for_args(argidx)
        if len(vboxes) > 1: # packed < packable and packed < stride:
            # the argument is scattered along different vector boxes
            args = [op.getoperation().getarg(argidx) for op in ops]
            vbox = self._pack(vbox, packed, args, packable)
            self.update_input_output(self.pack)
            box_pos = 0
        elif packed > packable:
            # box_pos == 0 then it is already at the right place
            # the argument has more items than the operation is able to process!
            args = [op.getoperation().getarg(argidx) for op in ops]
            vbox = self.unpack(vbox, args, off, packable, self.input_type)
            self.update_input_output(self.pack)
            box_pos = 0
        elif off != 0 and box_pos != 0:
            import py; py.test.set_trace()
            # The original box is at a position != 0 but it
            # is required to be at position 0. Unpack it!
            args = [op.getoperation().getarg(argidx) for op in ops]
            vbox = self.unpack(vbox, args, off, len(ops), self.input_type)
            self.update_input_output(self.pack)
        #
        assert vbox is not None
        return vbox

    def vector_boxes_for_args(self, index):
        args = [op.getoperation().getarg(index) for op in self.pack.operations]
        vboxes = []
        last_vbox = None
        for arg in args:
            pos, vbox = self.sched_data.getvector_of_box(arg)
            if vbox != last_vbox and vbox is not None:
                vboxes.append(vbox)
        return vboxes


    def extend(self, vbox, newtype):
        assert vbox.gettype() == newtype.gettype()
        if vbox.gettype() == INT:
            return self.extend_int(vbox, newtype)
        else:
            raise NotImplementedError("cannot yet extend float")

    def extend_int(self, vbox, newtype):
        vbox_cloned = newtype.new_vector_box(vbox.item_count)
        self.sched_data._prevent_signext(newtype.getsize(), vbox.getsize())
        op = ResOperation(rop.VEC_INT_SIGNEXT, 
                          [vbox, ConstInt(newtype.getsize())],
                          vbox_cloned)
        self.costmodel.record_cast_int(vbox.getsize(), newtype.getsize(), vbox.getcount())
        self.preamble_ops.append(op)
        return vbox_cloned

    def unpack(self, vbox, args, index, count, arg_ptype):
        vbox_cloned = vectorbox_clone_set(vbox, count=count)
        opnum = getunpackopnum(vbox.item_type)
        op = ResOperation(opnum, [vbox, ConstInt(index), ConstInt(count)], vbox_cloned)
        self.costmodel.record_vector_unpack(vbox, index, count)
        self.preamble_ops.append(op)
        #
        for i,arg in enumerate(args):
            self.sched_data.setvector_of_box(arg, i, vbox_cloned)
        #
        return vbox_cloned

    def _pack(self, tgt_box, index, args, packable):
        """ If there are two vector boxes:
          v1 = [<empty>,<emtpy>,X,Y]
          v2 = [A,B,<empty>,<empty>]
          this function creates a box pack instruction to merge them to:
          v1/2 = [A,B,X,Y]
        """
        opnum = getpackopnum(tgt_box.item_type)
        arg_count = len(args)
        i = index
        while i < arg_count and tgt_box.item_count < packable:
            arg = args[i]
            pos, src_box = self.sched_data.getvector_of_box(arg)
            if pos == -1:
                i += 1
                continue
            count = tgt_box.item_count + src_box.item_count
            new_box = vectorbox_clone_set(tgt_box, count=count)
            op = ResOperation(opnum, [tgt_box, src_box, ConstInt(i),
                                      ConstInt(src_box.item_count)], new_box)
            self.preamble_ops.append(op)
            self.costmodel.record_vector_pack(src_box, i, src_box.item_count)
            if not we_are_translated():
                self._check_vec_pack(op)
            i += src_box.item_count

            # overwrite the new positions, arguments now live in new_box
            # at a new position
            for j in range(i):
                arg = args[j]
                self.sched_data.setvector_of_box(arg, j, new_box)
            tgt_box = new_box
        _, vbox = self.sched_data.getvector_of_box(args[0])
        assert vbox is not None
        return vbox

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
        assert arg0.item_size == result.item_size
        if isinstance(arg1, BoxVector):
            assert arg1.item_size == result.item_size
        else:
            assert count.value == 1
        assert index.value < result.item_count
        assert index.value + count.value <= result.item_count
        assert result.item_count > arg0.item_count

    def expand(self, nodes, arg, argidx):
        vbox = self.input_type.new_vector_box(len(nodes))
        box_type = arg.type
        expanded_map = self.sched_data.expanded_map
        invariant_ops = self.sched_data.invariant_oplist
        invariant_vars = self.sched_data.invariant_vector_vars
        if isinstance(arg, BoxVector):
            box_type = arg.item_type

        # note that heterogenous nodes are not yet tracked
        already_expanded = expanded_map.get(arg, None)
        if already_expanded:
            return already_expanded

        for i, node in enumerate(nodes):
            op = node.getoperation()
            if not arg.same_box(op.getarg(argidx)):
                break
            i += 1
        else:
            expand_opnum = getexpandopnum(box_type)
            op = ResOperation(expand_opnum, [arg], vbox)
            invariant_ops.append(op)
            invariant_vars.append(vbox)
            expanded_map[arg] = vbox
            return vbox

        op = ResOperation(rop.VEC_BOX, [ConstInt(len(nodes))], vbox)
        invariant_ops.append(op)
        opnum = getpackopnum(arg.type)
        for i,node in enumerate(nodes):
            op = node.getoperation()
            arg = op.getarg(argidx)
            new_box = vbox.clonebox()
            ci = ConstInt(i)
            c1 = ConstInt(1)
            op = ResOperation(opnum, [vbox,arg,ci,c1], new_box)
            vbox = new_box
            invariant_ops.append(op)

        invariant_vars.append(vbox)
        return vbox

    def is_vector_arg(self, i):
        if i < 0 or i >= len(self.arg_ptypes):
            return False
        return self.arg_ptypes[i] is not None

class OpToVectorOpConv(OpToVectorOp):
    def __init__(self, intype, outtype):
        self.from_size = intype.getsize()
        self.to_size = outtype.getsize()
        OpToVectorOp.__init__(self, (intype, ), outtype)

    def determine_input_type(self, op):
        return self.arg_ptypes[0]

    def determine_output_type(self, op):
        return self.result_ptype

    def split_pack(self, pack, vec_reg_size):
        count = self.arg_ptypes[0].getcount()
        bytes = pack.opcount() * self.getscalarsize()
        if bytes > count * self.from_size:
            return bytes // (count * self.from_size)
        return pack.opcount()

    def new_result_vector_box(self):
        type = self.output_type.gettype()
        size = self.to_size
        count = self.output_type.getcount()
        vec_reg_size = self.sched_data.vec_reg_size
        if count * size > vec_reg_size:
            count = vec_reg_size // size
        signed = self.output_type.signed
        return BoxVector(type, count, size, signed)

class SignExtToVectorOp(OpToVectorOp):
    def __init__(self, intype, outtype):
        OpToVectorOp.__init__(self, intype, outtype)
        self.size = -1

    def split_pack(self, pack, vec_reg_size):
        op0 = pack.operations[0].getoperation()
        sizearg = op0.getarg(1)
        assert isinstance(sizearg, ConstInt)
        self.size = sizearg.value
        _, vbox = self.sched_data.getvector_of_box(op0.getarg(0))
        if vbox.getcount() * self.size > vec_reg_size:
            return vec_reg_size // self.size
        return vbox.getcount()

    def new_result_vector_box(self):
        type = self.output_type.gettype()
        count = self.input_type.getcount()
        vec_reg_size = self.sched_data.vec_reg_size
        if count * self.size > vec_reg_size:
            count = vec_reg_size // self.size
        signed = self.input_type.signed
        return BoxVector(type, count, self.size, signed)

class LoadToVectorLoad(OpToVectorOp):
    def __init__(self):
        OpToVectorOp.__init__(self, (), PT_GENERIC)

    def determine_input_type(self, op):
        return None

    def determine_output_type(self, op):
        return PackType.by_descr(op.getdescr(), self.sched_data.vec_reg_size)

    def before_argument_transform(self, args):
        args.append(ConstInt(len(self.pack.operations)))

    def getscalarsize(self):
        return self.output_type.getsize()

    def new_result_vector_box(self):
        type = self.output_type.gettype()
        size = self.output_type.getsize()
        count = len(self.pack.operations)
        signed = self.output_type.signed
        return BoxVector(type, count, size, signed)

class StoreToVectorStore(OpToVectorOp):
    """
    Storing operations are special because they are not allowed
    to store to memory if the vector is not fully filled.
    Thus a modified split_pack function
    """
    def __init__(self):
        OpToVectorOp.__init__(self, (None, None, PT_GENERIC), None)
        self.has_descr = True

    def determine_input_type(self, op):
        return PackType.by_descr(op.getdescr(), self.sched_data.vec_reg_size)

    def determine_output_type(self, op):
        return None

    def split_pack(self, pack, vec_reg_size):
        """ Returns how many items of the pack should be
            emitted as vector operation. """
        bytes = pack.opcount() * self.getscalarsize()
        if bytes > vec_reg_size:
            # too many bytes. does not fit into the vector register
            return vec_reg_size // self.getscalarsize()
        if bytes < vec_reg_size:
            # special case for store, even though load is allowed
            # to load more, store is not!
            # not enough to fill the vector register
            return 1
        return pack.opcount()

class PassThroughOp(OpToVectorOp):
    """ This pass through is only applicable if the target
    operation is capable of handling vector operations.
    Guard true/false is such an example.
    """
    def __init__(self, args):
        OpToVectorOp.__init__(self, args, None)

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

    rop.VEC_INT_SIGNEXT: SignExtToVectorOp((PT_INT_GENERIC,), INT_RES),

    rop.VEC_FLOAT_ADD:   FLOAT_OP_TO_VOP,
    rop.VEC_FLOAT_SUB:   FLOAT_OP_TO_VOP,
    rop.VEC_FLOAT_MUL:   FLOAT_OP_TO_VOP,
    rop.VEC_FLOAT_TRUEDIV:   FLOAT_OP_TO_VOP,
    rop.VEC_FLOAT_ABS:   FLOAT_SINGLE_ARG_OP_TO_VOP,
    rop.VEC_FLOAT_NEG:   FLOAT_SINGLE_ARG_OP_TO_VOP,
    rop.VEC_FLOAT_EQ:    OpToVectorOp((PT_FLOAT_GENERIC,PT_FLOAT_GENERIC), INT_RES),

    rop.VEC_RAW_LOAD:         LOAD_TRANS,
    rop.VEC_GETARRAYITEM_RAW: LOAD_TRANS,
    rop.VEC_RAW_STORE:        STORE_TRANS,
    rop.VEC_SETARRAYITEM_RAW: STORE_TRANS,

    rop.VEC_CAST_FLOAT_TO_SINGLEFLOAT: OpToVectorOpConv(PT_DOUBLE_2, PT_FLOAT_2),
    rop.VEC_CAST_SINGLEFLOAT_TO_FLOAT: OpToVectorOpConv(PT_FLOAT_2, PT_DOUBLE_2),
    rop.VEC_CAST_FLOAT_TO_INT: OpToVectorOpConv(PT_DOUBLE_2, PT_INT32_2),
    rop.VEC_CAST_INT_TO_FLOAT: OpToVectorOpConv(PT_INT32_2, PT_DOUBLE_2),

    rop.GUARD_TRUE: GUARD_TF,
    rop.GUARD_FALSE: GUARD_TF,
}

def determine_output_type(node, input_type):
    op = node.getoperation()
    op2vecop = determine_trans(op)
    if isinstance(op2vecop, OpToVectorOpConv):
        return op2vecop.determine_output_type(op)
    return input_type

def determine_trans(op):
    op2vecop = ROP_ARG_RES_VECTOR.get(op.vector, None)
    if op2vecop is None:
        raise NotImplementedError("missing vecop for '%s'" % (op.getopname(),))
    return op2vecop

class VecScheduleData(SchedulerData):
    def __init__(self, vec_reg_size, costmodel):
        self.box_to_vbox = {}
        self.vec_reg_size = vec_reg_size
        self.invariant_oplist = []
        self.invariant_vector_vars = []
        self.expanded_map = {}
        self.costmodel = costmodel

    def _prevent_signext(self, outsize, insize):
        if outsize < 4 and insize != outsize:
            raise NotAProfitableLoop

    def as_vector_operation(self, pack, preproc_renamer):
        assert pack.opcount() > 1
        # properties that hold for the pack are:
        # + isomorphism (see func above)
        # + tightly packed (no room between vector elems)

        oplist = []
        op = pack.operations[0].getoperation()
        determine_trans(op).as_vector_operation(pack, self, oplist)
        #
        if pack.is_accumulating():
            box = oplist[0].result
            assert box is not None
            for node in pack.operations:
                op = node.getoperation()
                assert op.result is not None
                preproc_renamer.start_renaming(op.result, box)
        #
        return oplist

    def getvector_of_box(self, arg):
        return self.box_to_vbox.get(arg, (-1, None))

    def setvector_of_box(self, box, off, vector):
        self.box_to_vbox[box] = (off, vector)

    def prepend_invariant_operations(self, oplist):
        if len(self.invariant_oplist) > 0:
            label = oplist[0]
            assert label.getopnum() == rop.LABEL
            jump = oplist[-1]
            assert jump.getopnum() == rop.JUMP

            label_args = label.getarglist()
            jump_args = jump.getarglist()
            for var in self.invariant_vector_vars:
                label_args.append(var)
                jump_args.append(var)

            oplist[0] = label.copy_and_change(label.getopnum(), label_args, None, label.getdescr())
            oplist[-1] = jump.copy_and_change(jump.getopnum(), jump_args, None, jump.getdescr())

            return self.invariant_oplist + oplist

        return oplist

class Accum(object):
    PLUS = '+'

    def __init__(self, var=None, pos=-1, operator=PLUS):
        self.var = var
        self.pos = pos
        self.operator = operator

class Pack(object):
    """ A pack is a set of n statements that are:
        * isomorphic
        * independent
    """
    def __init__(self, ops, input_type, output_type):
        self.operations = ops
        for i,node in enumerate(self.operations):
            node.pack = self
            node.pack_position = i
        self.accum = None
        self.input_type = input_type
        self.output_type = output_type

    def opcount(self):
        return len(self.operations)

    def opnum(self):
        assert len(self.operations) > 0
        return self.operations[0].getoperation().getopnum()

    def clear(self):
        for node in self.operations:
            node.pack = None
            node.pack_position = -1

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
        return "Pack(%r)" % self.operations

    def is_accumulating(self):
        return self.accum is not None

class Pair(Pack):
    """ A special Pack object with only two statements. """
    def __init__(self, left, right, input_type, output_type):
        assert isinstance(left, Node)
        assert isinstance(right, Node)
        self.left = left
        self.right = right
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
