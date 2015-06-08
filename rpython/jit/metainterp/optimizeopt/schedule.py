
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

    def next(self, position):
        i = self._next(self.schedulable_nodes)
        if i >= 0:
            candidate = self.schedulable_nodes[i]
            del self.schedulable_nodes[i]
            return self.schedule(candidate, position)

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
            for node in candidate.pack.operations:
                if node.depends_count() > 0:
                    return False
        return candidate.depends_count() == 0

    def schedule(self, candidate, position):
        if candidate.pack:
            pack = candidate.pack
            vops = self.sched_data.as_vector_operation(pack)
            for node in pack.operations:
                self.scheduled(node, position)
            return vops
        else:
            self.scheduled(candidate, position)
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

PT_FLOAT_2 = PackType(FLOAT, 4, False, 2)
PT_DOUBLE_2 = PackType(FLOAT, 8, False, 2)
PT_FLOAT_GENERIC = PackType(INT, -1, True)
PT_INT64 = PackType(INT, 8, True)
PT_INT32_2 = PackType(INT, 4, True, 2)
PT_INT_GENERIC = PackType(INT, -1, True)
PT_GENERIC = PackType(PackType.UNKNOWN_TYPE, -1, False)

INT_RES = PT_INT_GENERIC
FLOAT_RES = PT_FLOAT_GENERIC

class OpToVectorOpConv(OpToVectorOp):
    def __init__(self, intype, outtype):
        self.from_size = intype.getsize()
        self.to_size = outtype.getsize()
        OpToVectorOp.__init__(self, (intype, ), outtype)

    def determine_input_type(self, op):
        return self.arg_ptypes[0]

    def determine_output_type(self, op):
        return self.result_ptype

    def split_pack(self, pack):
        if self.from_size > self.to_size:
            # cast down
            return OpToVectorOp.split_pack(self, pack)
        op0 = pack.operations[0].getoperation()
        _, vbox = self.sched_data.getvector_of_box(op0.getarg(0))
        vec_reg_size = self.sched_data.vec_reg_size
        if vbox.getcount() * self.to_size > vec_reg_size:
            return vec_reg_size // self.to_size
        return len(pack.operations)

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

    def split_pack(self, pack):
        op0 = pack.operations[0].getoperation()
        sizearg = op0.getarg(1)
        assert isinstance(sizearg, ConstInt)
        self.size = sizearg.value
        if self.input_type.getsize() > self.size:
            # cast down
            return OpToVectorOp.split_pack(self, pack)
        _, vbox = self.sched_data.getvector_of_box(op0.getarg(0))
        vec_reg_size = self.sched_data.vec_reg_size
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

    def getsplitsize(self):
        return self.output_type.getsize()

    def new_result_vector_box(self):
        type = self.output_type.gettype()
        size = self.output_type.getsize()
        count = len(self.pack.operations)
        signed = self.output_type.signed
        return BoxVector(type, count, size, signed)

class StoreToVectorStore(OpToVectorOp):
    def __init__(self):
        OpToVectorOp.__init__(self, (None, None, PT_GENERIC), None)
        self.has_descr = True

    def determine_input_type(self, op):
        return PackType.by_descr(op.getdescr(), self.sched_data.vec_reg_size)

    def determine_output_type(self, op):
        return None

INT_OP_TO_VOP = OpToVectorOp((PT_INT_GENERIC, PT_INT_GENERIC), INT_RES)
FLOAT_OP_TO_VOP = OpToVectorOp((PT_FLOAT_GENERIC, PT_FLOAT_GENERIC), FLOAT_RES)
FLOAT_SINGLE_ARG_OP_TO_VOP = OpToVectorOp((PT_FLOAT_GENERIC,), FLOAT_RES)
LOAD_TRANS = LoadToVectorLoad()
STORE_TRANS = StoreToVectorStore()

# note that the following definition is x86 machine
# specific.
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
}

class VecScheduleData(SchedulerData):
    def __init__(self, vec_reg_size):
        self.box_to_vbox = {}
        self.vec_reg_size = vec_reg_size
        self.invariant_oplist = []
        self.invariant_vector_vars = []
        self.expanded_map = {}

    def as_vector_operation(self, pack):
        op_count = len(pack.operations)
        assert op_count > 1
        self.pack = pack
        # properties that hold for the pack are:
        # + isomorphism (see func above)
        # + tight packed (no room between vector elems)

        op0 = pack.operations[0].getoperation()
        tovector = ROP_ARG_RES_VECTOR.get(op0.vector, None)
        if tovector is None:
            raise NotImplementedError("missing vecop for '%s'" % (op0.getopname(),))
        oplist = []
        tovector.as_vector_operation(pack, self, oplist)
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

