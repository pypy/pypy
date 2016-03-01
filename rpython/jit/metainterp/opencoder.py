
from rpython.jit.metainterp.history import ConstInt, Const, AbstractDescr,\
    AbstractValue
from rpython.jit.metainterp.resoperation import AbstractResOp, AbstractInputArg,\
    ResOperation, oparity, opname, rop, ResOperation, opwithdescr
from rpython.rlib.rarithmetic import intmask
from rpython.jit.metainterp import resume

TAGINT, TAGCONST, TAGBOX = range(3)
TAGMASK = 0x3
TAGSHIFT = 2
MAXINT = 65536

class TraceIterator(object):
    def __init__(self, trace, end):
        self.trace = trace
        self.inputargs = [rop.inputarg_from_tp(arg.type) for
                          arg in self.trace.inputargs]
        self.pos = 0
        self._count = 0
        self.end = end
        self._cache = [None] * trace._count

    def _get(self, i):
        if i < 0:
            return self.inputargs[-i - 1]
        res = self._cache[i]
        assert res is not None
        return res

    def done(self):
        return self.pos >= self.end

    def _next(self):
        res = self.trace._ops[self.pos]
        self.pos += 1
        return res

    def _untag(self, tagged):
        tag, v = untag(tagged)
        if tag == TAGBOX:
            return self._get(v)
        elif tag == TAGINT:
            return ConstInt(v)
        elif tag == TAGCONST:
            return self.trace._consts[v]
        else:
            yyyy

    def read_resume(self, op):
        jc_index = self._next()
        pc = self._next()
        f = resume.FrameInfo(None, jc_index, pc)
        op.rd_frame_info_list = f
        lgt = self._next()
        box_list = []
        for i in range(lgt):
            box = self._get(self._next())
            assert box
            box_list.append(box)
        op.rd_snapshot = resume.Snapshot(None, box_list)

    def next(self):
        opnum = self._next()
        if oparity[opnum] == -1:
            argnum = self._next()
        else:
            argnum = oparity[opnum]
        args = []
        for i in range(argnum):
            args.append(self._untag(self._next()))
        if opwithdescr[opnum]:
            descr_index = self._next()
            if descr_index == -1:
                descr = None
            else:
                descr = self.trace._descrs[descr_index]
        else:
            descr = None
        res = ResOperation(opnum, args, -1, descr=descr)
        if rop.is_guard(opnum):
            self.read_resume(res)
        self._cache[self._count] = res
        self._count += 1
        return res

class Trace(object):
    def __init__(self, inputargs):
        self._ops = []
        self._descrs = [None]
        self._consts = [None]
        for i, inparg in enumerate(inputargs):
            inparg.position = -i - 1
        self._count = 0
        self.inputargs = inputargs

    def _encode(self, box):
        if isinstance(box, Const):
            if isinstance(box, ConstInt) and box.getint() < MAXINT:
                return tag(TAGINT, box.getint())
            else:
                self._consts.append(box)
                return tag(TAGCONST, len(self._consts) - 1)
        elif isinstance(box, AbstractResOp):
            return tag(TAGBOX, box.position)
        elif isinstance(box, AbstractInputArg):
            return tag(TAGBOX, box.position)
        else:
            assert False, "unreachable code"

    def _record_op(self, opnum, argboxes, descr=None):
        operations = self._ops
        pos = len(operations)
        operations.append(opnum)
        if oparity[opnum] == -1:
            operations.append(len(argboxes))
        operations.extend([self._encode(box) for box in argboxes])
        if opwithdescr[opnum]:
            if descr is None:
                operations.append(-1)
            else:
                operations.append(self._encode_descr(descr))
        self._count += 1
        return pos

    def _record_raw(self, opnum, tagged_args, tagged_descr=-1):
        operations = self._ops
        pos = len(operations)
        operations.append(opnum)
        if oparity[opnum] == -1:
            operations.append(len(tagged_args))
        operations.extend(tagged_args)
        if tagged_descr != -1:
            operations.append(tagged_descr)
        self._count += 1
        return pos        

    def _encode_descr(self, descr):
        # XXX provide a global cache for prebuilt descrs so we don't
        #     have to repeat them here        
        self._descrs.append(descr)
        return len(self._descrs) - 1

    def record_forwarding(self, op, newtag):
        index = op._pos
        self._ops[index] = -newtag - 1

    def record_op(self, opnum, argboxes, descr=None):
        # return an ResOperation instance, ideally die in hell
        pos = self._record_op(opnum, argboxes, descr)
        return ResOperation(opnum, argboxes, pos, descr)

    def record_op_tag(self, opnum, tagged_args, descr=None):
        return tag(TAGBOX, self._record_raw(opnum, tagged_args, descr))

    def record_snapshot(self, jitcode, pc, active_boxes):
        self._ops.append(jitcode.index)
        self._ops.append(pc)
        self._ops.append(len(active_boxes)) # unnecessary, can be read from
        # jitcode
        for box in active_boxes:
            self._ops.append(box.position) # not tagged, as it must be boxes

    def get_iter(self):
        return TraceIterator(self, len(self._ops))

    def _get_operations(self):
        """ NOT_RPYTHON
        """
        l = []
        i = self.get_iter()
        while not i.done():
            l.append(i.next())
        return l

def tag(kind, pos):
    return (pos << TAGSHIFT) | kind

def untag(tagged):
    return intmask(tagged) & TAGMASK, intmask(tagged) >> TAGSHIFT
