
""" Storage format:
for each operation (inputargs numbered with negative numbers)
<opnum> [size-if-unknown-arity] [<arg0> <arg1> ...] [descr] [potential snapshot]
snapshot is as follows
<total size of snapshot> <virtualizable size> <virtualizable boxes>
<virtualref size> <virtualref boxes> [<size> <jitcode> <pc> <boxes...> ...]
"""

from rpython.jit.metainterp.history import ConstInt, Const
from rpython.jit.metainterp.resoperation import AbstractResOp, AbstractInputArg,\
    ResOperation, oparity, rop, opwithdescr, GuardResOp
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.objectmodel import we_are_translated

TAGINT, TAGCONST, TAGBOX = range(3)
TAGMASK = 0x3
TAGSHIFT = 2
NUM_SMALL_INTS = 2 ** (16 - TAGSHIFT)

class Sentinel(object):
    pass

class BaseTrace(object):
    pass

class SnapshotIterator(object):
    def __init__(self, main_iter, pos, end_pos):
        self.trace = main_iter.trace
        self.main_iter = main_iter
        self.end = end_pos
        self.start = pos
        self.pos = pos
        self.save_pos = -1

    def length(self):
        return self.end - self.start

    def done(self):
        return self.pos >= self.end

    def _next(self):
        res = self.trace._ops[self.pos]
        self.pos += 1
        return res

    def next(self):
        r = self.main_iter._untag(self._next())
        assert r
        return r

    def read_boxes(self, size):
        return [self.next() for i in range(size)]

    def get_size_jitcode_pc(self):
        if self.save_pos >= 0:
            self.pos = self.save_pos
            self.save_pos = -1
        size = self._next()
        if size < 0:
            self.save_pos = self.pos
            self.pos = -size - 1
            assert self.pos >= 0
            size = self._next()
            assert size >= 0
        return size, self._next(), self._next()

    def get_list_of_boxes(self):
        size = self._next()
        l = []
        for i in range(size):
            l.append(self.next())
        return l

class TraceIterator(BaseTrace):
    def __init__(self, trace, start, end, force_inputargs=None):
        self.trace = trace
        self._cache = [None] * trace._count
        if force_inputargs is not None:
            self.inputargs = [rop.inputarg_from_tp(arg.type) for
                              arg in force_inputargs]
            self._inputargs = [None] * len(trace.inputargs)
            for i, arg in enumerate(force_inputargs):
                if arg.get_position() >= 0:
                    self._cache[arg.get_position()] = self.inputargs[i]
                else:
                    self._inputargs[-arg.get_position()-1] = self.inputargs[i]
        else:
            self.inputargs = [rop.inputarg_from_tp(arg.type) for
                              arg in self.trace.inputargs]
            self._inputargs = self.inputargs[:]
        self.start = start
        self.pos = start
        self._count = 0
        self.end = end

    def _get(self, i):
        if i < 0:
            return self._inputargs[-i - 1]
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
            assert False

    def skip_resume_data(self):
        pos = self.pos
        self.pos = self._next()
        return pos

    def get_snapshot_iter(self, pos):
        end = self.trace._ops[pos]
        return SnapshotIterator(self, pos + 1, end)

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
            assert isinstance(res, GuardResOp)
            res.rd_resume_position = self.skip_resume_data()
        self._cache[self._count] = res
        self._count += 1
        return res

class CutTrace(BaseTrace):
    def __init__(self, trace, start, count, inputargs):
        self.trace = trace
        self.start = start
        self.inputargs = inputargs
        self.count = count

    def get_iter(self):
        iter = TraceIterator(self.trace, self.start, len(self.trace._ops),
                             self.inputargs)
        iter._count = self.count
        return iter

class Trace(BaseTrace):
    def __init__(self, inputargs):
        self._ops = []
        self._descrs = [None]
        self._consts = [None]
        for i, inparg in enumerate(inputargs):
            assert isinstance(inparg, AbstractInputArg)
            inparg.position = -i - 1
        self._count = 0
        self.inputargs = inputargs

    def length(self):
        return len(self._ops)

    def cut_point(self):
        return len(self._ops), self._count

    def cut_at(self, end):
        self._ops = self._ops[:end[0]]
        self._count = end[1]

    def cut_trace_from(self, (start, count), inputargs):
        return CutTrace(self, start, count, inputargs)

    def _encode(self, box):
        if isinstance(box, Const):
            if (isinstance(box, ConstInt) and
                isinstance(box.getint(), int) and # symbolics
                0 <= box.getint() < NUM_SMALL_INTS):
                return tag(TAGINT, box.getint())
            else:
                self._consts.append(box)
                return tag(TAGCONST, len(self._consts) - 1)
        elif isinstance(box, AbstractResOp):
            return tag(TAGBOX, box.get_position())
        elif isinstance(box, AbstractInputArg):
            return tag(TAGBOX, box.get_position())
        else:
            assert False, "unreachable code"

    def _record_op(self, opnum, argboxes, descr=None):
        operations = self._ops
        pos = self._count
        operations.append(opnum)
        expected_arity = oparity[opnum]
        if expected_arity == -1:
            operations.append(len(argboxes))
        else:
            assert len(argboxes) == expected_arity
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
        pos = self._count
        operations.append(opnum)
        expected_arity = oparity[opnum]
        if expected_arity == -1:
            operations.append(len(tagged_args))
        else:
            assert len(argboxes) == expected_arity
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

#    def record_forwarding(self, op, newtag):
#        index = op._pos
#        self._ops[index] = -newtag - 1

    def record_snapshot_link(self, pos):
        self._ops.append(-pos - 1)

    def record_op(self, opnum, argboxes, descr=None):
        # return an ResOperation instance, ideally die in hell
        pos = self._record_op(opnum, argboxes, descr)
        assert opnum >= 0
        return ResOperation(opnum, argboxes, pos, descr)

    def record_op_tag(self, opnum, tagged_args, descr=None):
        return tag(TAGBOX, self._record_raw(opnum, tagged_args, descr))

    def record_snapshot(self, jitcode, pc, active_boxes):
        pos = len(self._ops)
        self._ops.append(len(active_boxes)) # unnecessary, can be read from
        self._ops.append(jitcode.index)
        self._ops.append(pc)
        for box in active_boxes:
            self._ops.append(self._encode(box)) # not tagged, as it must be boxes
        return pos

    def record_list_of_boxes(self, boxes):
        self._ops.append(len(boxes))
        for box in boxes:
            self._ops.append(self._encode(box))

    def get_patchable_position(self):
        p = len(self._ops)
        if not we_are_translated():
            self._ops.append(Sentinel())
        else:
            self._ops.append(-1)
        return p

    def patch_position_to_current(self, p):
        prev = self._ops[p]
        if we_are_translated():
            assert prev == -1
        else:
            assert isinstance(prev, Sentinel)
        self._ops[p] = len(self._ops)

    def check_snapshot_jitcode_pc(self, jitcode, pc, resumedata_pos):
        assert self._ops[resumedata_pos + 1] == jitcode.index
        assert self._ops[resumedata_pos + 2] == pc

    def get_iter(self):
        return TraceIterator(self, 0, len(self._ops))

    def unpack(self):
        iter = self.get_iter()
        ops = []
        while not iter.done():
            ops.append(iter.next())
        return ops

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
