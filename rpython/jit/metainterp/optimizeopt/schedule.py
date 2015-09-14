from rpython.jit.metainterp.history import (VECTOR, FLOAT, INT,
        ConstInt, ConstFloat, TargetToken)
from rpython.jit.metainterp.resoperation import (rop, ResOperation,
        GuardResOp, VecOperation)
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

    def post_schedule(self):
        loop = self.graph.loop
        self.renamer.rename(loop.jump)

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

    def mark_emitted(self, node, state):
        """ An operation has been emitted, adds new operations to the worklist
            whenever their dependency count drops to zero.
            Keeps worklist sorted (see priority) """
        op = node.getoperation()
        state.renamer.rename(op)
        state.unpack_from_vector(op)
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

    def walk_and_emit(self, state): # TODO oplist, renamer, unpack=False):
        """ Emit all the operations into the oplist parameter.
            Initiates the scheduling. """
        assert isinstance(state, SchedulerState)
        import pdb; pdb.set_trace()
        while state.has_more():
            node = self.next(state)
            if node:
                if not state.emit(node, self):
                    if not node.emitted:
                        op = node.getoperation()
                        self.mark_emitted(node, state)
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

def vectorbox_outof_box(box, count=-1, size=-1, type='-'):
    if box.type not in (FLOAT, INT):
        raise AssertionError("cannot create vector box of type %s" % (box.type))
    signed = True
    if box.type == FLOAT:
        signed = False
    return BoxVector(box.type, 2, 8, signed)

def packtype_outof_box(box):
    if box.type == VECTOR:
        return Type.of(box)
    else:
        if box.type == INT:
            return Type(INT, 8, True, 2)
        elif box.type == FLOAT:
            return Type(FLOAT, 8, False, 2)
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

UNSIGNED_OPS = (rop.UINT_FLOORDIV, rop.UINT_RSHIFT,
                rop.UINT_LT, rop.UINT_LE,
                rop.UINT_GT, rop.UINT_GE)

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

class TypeOutput(object):
    def __init__(self, type, count):
        self.type = type
        self.count = count


    def bytecount(self):
        return self.count * self.type.bytecount()

class DataTyper(object):

    def infer_type(self, op):
        # default action, pass through: find the first arg
        # the output is the same as the first argument!
        if op.returns_void() or op.argcount() == 0:
            return
        arg0 = op.getarg(0)
        op.setdatatype(arg0.datatype, arg0.bytesize, arg0.signed)

class PassFirstArg(TypeOutput):
    def __init__(self):
        pass

class OpToVectorOp(object):
    def __init__(self, restrictargs, typeoutput):
        self.args = list(restrictargs) # do not use a tuple. rpython cannot union
        self.out = typeoutput

    def as_vector_operation(self, state, pack):
        #
        # TODO self.check_if_pack_supported(pack)
        op = pack.leftmost()
        args = op.getarglist()
        self.prepare_arguments(state, op.getarglist())
        vop = VecOperation(op.vector, args, op, pack.numops(), op.getdescr())
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
                scheduler.renamer.start_renaming(op, box)
        #
        state.oplist.append(vop)

    def prepare_arguments(self, state, args):
        self.before_argument_transform(args)
        # Transforming one argument to a vector box argument
        # The following cases can occur:
        # 1) argument is present in the box_to_vbox map.
        #    a) vector can be reused immediatly (simple case)
        #    b) vector is to big
        #    c) vector is to small
        # 2) argument is not known to reside in a vector
        #    a) expand vars/consts before the label and add as argument
        #    b) expand vars created in the loop body
        #
        for i,arg in enumerate(args):
            if arg.returns_vector():
                continue
            if not self.transform_arg_at(i):
                continue
            box_pos, vbox = state.getvector_of_box(arg)
            if not vbox:
                # 2) constant/variable expand this box
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
            self.sched_data.setvector_of_box(op, i, vbox)
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
        """ Transforming one argument to a vector box argument
            The following cases can occur:
            1) argument is present in the box_to_vbox map.
               a) vector can be reused immediatly (simple case)
               b) vector is to big
               c) vector is to small
            2) argument is not known to reside in a vector
               a) expand vars/consts before the label and add as argument
               b) expand vars created in the loop body
        """
        for i,arg in enumerate(args):
            if arg.returns_vector():
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
        """ Extract parts of the vector box into another vector box """
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
        result = op
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
        """ Expand a value into a vector box. useful for arith metic
            of one vector with a scalar (either constant/varialbe)
        """
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

    def transform_arg_at(self, i):
        if i < 0 or i >= len(self.args):
            return False
        return self.args[i] is not None

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
        #self.from_size = intype.getsize()
        #self.to_size = outtype.getsize()
        #OpToVectorOp.__init__(self, (intype, ), outtype)
        pass

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
        OpToVectorOp.__init__(self, (), TypeRestrict())

    # OLD def before_argument_transform(self, args):
        #count = min(self.output_type.getcount(), len(self.getoperations()))
        #args.append(ConstInt(count))

    def get_output_type_given(self, input_type, op):
        return xxx#Type.by_descr(op.getdescr(), self.sched_data.vec_reg_size)

    def get_input_type_given(self, output_type, op):
        return None

class StoreToVectorStore(OpToVectorOp):
    """ Storing operations are special because they are not allowed
        to store to memory if the vector is not fully filled.
        Thus a modified split_pack function.
    """
    def __init__(self):
        OpToVectorOp.__init__(self, (None, None, TypeRestrict()), None)
        self.has_descr = True

    def must_be_full_but_is_not(self, pack):
        vrs = self.sched_data.vec_reg_size
        it = pack.input_type
        return it.getsize() * it.getcount() < vrs

    def get_output_type_given(self, input_type, op):
        return None

    def get_input_type_given(self, output_type, op):
        return xxx#Type.by_descr(op.getdescr(), self.sched_data.vec_reg_size)

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


class trans(object):
    DT_PASS = DataTyper()

    TR_ANY_FLOAT = TypeRestrict(FLOAT)
    TR_ANY_INTEGER = TypeRestrict(INT)
    TR_FLOAT_2 = TypeRestrict(FLOAT, 4, 2)
    TR_DOUBLE_2 = TypeRestrict(FLOAT, 8, 2)
    TR_LONG = TypeRestrict(INT, 8, 2)
    TR_INT_2 = TypeRestrict(INT, 4, 2)

    INT = OpToVectorOp((TR_ANY_INTEGER, TR_ANY_INTEGER), DT_PASS)
    FLOAT = OpToVectorOp((TR_ANY_FLOAT, TR_ANY_FLOAT), DT_PASS)
    FLOAT_UNARY = OpToVectorOp((TR_ANY_FLOAT,), DT_PASS)
    LOAD = LoadToVectorLoad()
    STORE = StoreToVectorStore()
    GUARD = PassThroughOp((TR_ANY_INTEGER,))

    # note that the following definition is x86 arch specific
    MAPPING = {
        rop.VEC_INT_ADD:            INT,
        rop.VEC_INT_SUB:            INT,
        rop.VEC_INT_MUL:            INT,
        rop.VEC_INT_AND:            INT,
        rop.VEC_INT_OR:             INT,
        rop.VEC_INT_XOR:            INT,
        rop.VEC_INT_EQ:             INT,
        rop.VEC_INT_NE:             INT,

        rop.VEC_FLOAT_ADD:          FLOAT,
        rop.VEC_FLOAT_SUB:          FLOAT,
        rop.VEC_FLOAT_MUL:          FLOAT,
        rop.VEC_FLOAT_TRUEDIV:      FLOAT,
        rop.VEC_FLOAT_ABS:          FLOAT_UNARY,
        rop.VEC_FLOAT_NEG:          FLOAT_UNARY,

        rop.VEC_RAW_LOAD_I:         LOAD,
        rop.VEC_RAW_LOAD_F:         LOAD,
        rop.VEC_GETARRAYITEM_RAW_I: LOAD,
        rop.VEC_GETARRAYITEM_RAW_F: LOAD,
        rop.VEC_GETARRAYITEM_GC_I:  LOAD,
        rop.VEC_GETARRAYITEM_GC_F:  LOAD,

        rop.VEC_RAW_STORE:          STORE,
        rop.VEC_SETARRAYITEM_RAW:   STORE,
        rop.VEC_SETARRAYITEM_GC:    STORE,

        rop.GUARD_TRUE: GUARD,
        rop.GUARD_FALSE: GUARD,

        # irregular
        rop.VEC_INT_SIGNEXT: SignExtToVectorOp((TR_ANY_INTEGER,), None),

        rop.VEC_CAST_FLOAT_TO_SINGLEFLOAT: OpToVectorOpConv(TR_DOUBLE_2, None), #RESTRICT_2_FLOAT),
        rop.VEC_CAST_SINGLEFLOAT_TO_FLOAT: OpToVectorOpConv(TR_FLOAT_2, None), #RESTRICT_2_DOUBLE),
        rop.VEC_CAST_FLOAT_TO_INT: OpToVectorOpConv(TR_DOUBLE_2, None), #RESTRICT_2_INT),
        rop.VEC_CAST_INT_TO_FLOAT: OpToVectorOpConv(TR_INT_2, None), #RESTRICT_2_DOUBLE),

        rop.VEC_FLOAT_EQ:    OpToVectorOp((TR_ANY_FLOAT,TR_ANY_FLOAT), None),
        rop.VEC_FLOAT_NE:    OpToVectorOp((TR_ANY_FLOAT,TR_ANY_FLOAT), None),
        rop.VEC_INT_IS_TRUE: OpToVectorOp((TR_ANY_INTEGER,TR_ANY_INTEGER), None), # TR_ANY_INTEGER),
    }

    # TODO?
    UNSIGNED_OPS = (rop.UINT_FLOORDIV, rop.UINT_RSHIFT,
                    rop.UINT_LT, rop.UINT_LE,
                    rop.UINT_GT, rop.UINT_GE)

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
    op2vecop = trans.MAPPING.get(op.vector, None)
    if op2vecop is None:
        raise NotImplementedError("missing vecop for '%s'" % (op.getopname(),))
    return op2vecop

class VecScheduleState(SchedulerState):
    def __init__(self, graph, packset, cpu, costmodel):
        SchedulerState.__init__(self, graph)
        self.box_to_vbox = {}
        self.cpu = cpu
        self.vec_reg_size = cpu.vector_register_size
        self.invariant_oplist = []
        self.invariant_vector_vars = []
        self.expanded_map = {}
        self.costmodel = costmodel
        self.inputargs = {}
        self.packset = packset
        for arg in graph.loop.inputargs:
            self.inputargs[arg] = None
        self.seen = {}

    def post_schedule(self):
        loop = self.graph.loop
        self.unpack_from_vector(loop.jump)
        SchedulerState.post_schedule(self)

        self.graph.loop.operations = self.oplist

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
                scheduler.mark_emitted(node, self)
            op2vecop = determine_trans(node.pack.leftmost())
            op2vecop.as_vector_operation(self, node.pack)
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

    def unpack_from_vector(self, op):
        """ If a box is needed that is currently stored within a vector
            box, this utility creates a unpacking instruction.
        """
        args = op.getarglist()

        # unpack for an immediate use
        for i, arg in enumerate(op.getarglist()):
            if not arg.is_constant():
                argument = self._unpack_from_vector(i, arg)
                if arg is not argument:
                    op.setarg(i, argument)
        if not op.returns_void():
            self.seen[op] = None
        # unpack for a guard exit
        if op.is_guard():
            fail_args = op.getfailargs()
            for i, arg in enumerate(fail_args):
                if arg and not arg.is_constant():
                    argument = self._unpack_from_vector(i, arg)
                    if arg is not argument:
                        fail_args[i] = argument

    def _unpack_from_vector(self, i, arg):
        if arg in self.seen or arg.type == 'V':
            return arg
        (j, vbox) = self.getvector_of_box(arg)
        if vbox:
            if vbox in self.invariant_vector_vars:
                return arg
            arg_cloned = arg.clonebox()
            self.seen[arg_cloned] = None
            self.renamer.start_renaming(arg, arg_cloned)
            self.setvector_of_box(arg_cloned, j, vbox)
            cj = ConstInt(j)
            ci = ConstInt(1)
            opnum = getunpackopnum(vbox.gettype())
            unpack_op = ResOperation(opnum, [vbox, cj, ci], arg_cloned)
            self.costmodel.record_vector_unpack(vbox, j, 1)
            self.oplist.append(unpack_op)
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
        assert box.type != 'V'
        self.box_to_vbox[box] = (off, vector)

def opcount_filling_vector_register(pack, vec_reg_size):
    """ how many operations of that kind can one execute
        with a machine instruction of register size X?
    """
    pack_type = pack.input_type
    if pack_type is None:
        pack_type = pack.output_type # load operations

    op = pack.leftmost()
    if op.casts_box():
        count = pack_type.getcount()
        return count
    count = vec_reg_size // pack_type.getsize()
    return count

def maximum_byte_size(pack, vec_reg_size):
    """ The maxmum size in bytes the operation is able to
        process with the hardware register and the operation
        semantics.
    """
    op = pack.leftmost()
    if op.casts_box():
        # casting is special, often only takes a half full vector
        pack_type = pack.input_type
        if pack_type is None:
            pack_type = pack.output_type # load operations
        return pack_type.byte_size()
    return vec_reg_size

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
        # initializes the type
        # TODO
        #input_type, output_type = \
        #    determine_input_output_types(origin_pack, lnode, forward)
        #self.input_type = input_type
        #self.output_type = output_type
        #assert self.input_type is not None or self.output_type is not None

    def numops(self):
        return len(self.operations)

    def leftmost(self):
        return self.operations[0].getoperation()

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
            return 0
        if self.numops() == 0:
            return -1
        size = maximum_byte_size(self, vec_reg_size)
        return left.bytesize * self.numops() - size
        #if self.input_type is None:
            # e.g. load operations
        #    return self.output_type.bytecount(self) - size
        # default only consider the input type
        # e.g. store operations, int_add, ...
        #return self.input_type.bytecount(self) - size

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
        pack = self
        while pack.pack_load(vec_reg_size) > Pack.FULL:
            pack.clear()
            oplist, newoplist = pack.slice_operations(vec_reg_size)
            pack.operations = oplist
            pack.update_pack_of_nodes()
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
