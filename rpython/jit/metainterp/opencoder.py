
""" Storage format:
for each operation (inputargs numbered with negative numbers)
<opnum> [size-if-unknown-arity] [<arg0> <arg1> ...] [descr] [potential snapshot]
snapshot is as follows
<total size of snapshot> <virtualizable size> <virtualizable boxes>
<virtualref size> <virtualref boxes> [<size> <jitcode> <pc> <boxes...> ...]
"""

from rpython.jit.metainterp.history import ConstInt, Const, ConstFloat, ConstPtr
from rpython.jit.metainterp.resoperation import AbstractResOp, AbstractInputArg,\
    ResOperation, oparity, rop, opwithdescr, GuardResOp
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.jit.metainterp.typesystem import llhelper

TAGINT, TAGCONSTPTR, TAGCONSTOTHER, TAGBOX = range(4)
TAGMASK = 0x3
TAGSHIFT = 2
SMALL_INT_STOP  = 2 ** (15 - TAGSHIFT)
SMALL_INT_START = -SMALL_INT_STOP
MIN_SHORT = -2**15 + 1
MAX_SHORT = 2**15 - 1

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
        res = rffi.cast(lltype.Signed, self.trace._ops[self.pos])
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
            self.save_pos = self.pos + 1
            self.pos = ((-size - 1) << 15) | (self._next())
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
        res = rffi.cast(lltype.Signed, self.trace._ops[self.pos])
        self.pos += 1
        return res

    def _untag(self, tagged):
        tag, v = untag(tagged)
        if tag == TAGBOX:
            return self._get(v)
        elif tag == TAGINT:
            return ConstInt(v)
        elif tag == TAGCONSTPTR:
            return ConstPtr(self.trace._refs[v])
        elif tag == TAGCONSTOTHER:
            if v & 1:
                return ConstFloat(self.trace._floats[v >> 1])
            else:
                return ConstInt(self.trace._bigints[v >> 1])
        else:
            assert False

    def skip_resume_data(self):
        pos = self.pos
        self.pos += self._next()
        return pos

    def get_snapshot_iter(self, pos):
        end = rffi.cast(lltype.Signed, self.trace._ops[pos]) + pos
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
        iter = TraceIterator(self.trace, self.start, self.trace._pos,
                             self.inputargs)
        iter._count = self.count
        return iter

class Trace(BaseTrace):
    def __init__(self, inputargs):
        self._ops = [rffi.cast(rffi.SHORT, -15)] * 30000
        self._pos = 0
        self._snapshot_lgt = 0
        self._consts_bigint = 0
        self._consts_float = 0
        self._consts_ptr = 0
        self._descrs = [None]
        self._refs = [lltype.nullptr(llmemory.GCREF.TO)]
        self._refs_dict = llhelper.new_ref_dict_3()
        self._bigints = []
        self._bigints_dict = {}
        self._floats = []
        self._floats_dict = {}
        for i, inparg in enumerate(inputargs):
            assert isinstance(inparg, AbstractInputArg)
            inparg.position = -i - 1
        self._count = 0
        self.inputargs = inputargs

    def append(self, v):
        if self._pos >= len(self._ops):
            # grow by 2X
            self._ops = self._ops + [rffi.cast(rffi.SHORT, -15)] * len(self._ops)
        assert MIN_SHORT < v < MAX_SHORT
        self._ops[self._pos] = rffi.cast(rffi.SHORT, v)
        self._pos += 1

    def done(self):
        from rpython.rlib.debug import debug_start, debug_stop, debug_print

        self._bigints_dict = {}
        self._refs_dict = llhelper.new_ref_dict_3()
        self._floats_dict = {}
        debug_start("jit-trace-done")
        debug_print("trace length: " + str(self._pos))
        debug_print(" snapshots: " + str(self._snapshot_lgt))
        debug_print(" bigint consts: " + str(self._consts_bigint) + " " + str(len(self._bigints)))
        debug_print(" float consts: " + str(self._consts_float) + " " + str(len(self._floats)))
        debug_print(" ref consts: " + str(self._consts_ptr) + " " + str(len(self._refs)))
        debug_stop("jit-trace-done")
        return 0 # completely different than TraceIter.done, but we have to
        # share the base class

    def length(self):
        return self._pos

    def cut_point(self):
        return self._pos, self._count

    def cut_at(self, end):
        self._pos = end[0]
        self._count = end[1]

    def cut_trace_from(self, (start, count), inputargs):
        return CutTrace(self, start, count, inputargs)

    def _encode(self, box):
        if isinstance(box, Const):
            if (isinstance(box, ConstInt) and
                isinstance(box.getint(), int) and # symbolics
                SMALL_INT_START <= box.getint() < SMALL_INT_STOP):
                return tag(TAGINT, box.getint())
            elif isinstance(box, ConstInt):
                self._consts_bigint += 1
                if not isinstance(box.getint(), int):
                    # symbolics, for tests, don't worry about caching
                    v = len(self._bigints) << 1
                    self._bigints.append(box.getint())
                else:
                    v = self._bigints_dict.get(box.getint(), -1)
                    if v == -1:
                        v = len(self._bigints) << 1
                        self._bigints_dict[box.getint()] = v
                        self._bigints.append(box.getint())
                return tag(TAGCONSTOTHER, v)
            elif isinstance(box, ConstFloat):
                self._consts_float += 1
                v = self._floats_dict.get(box.getfloat(), -1)
                if v == -1:
                    v = (len(self._floats) << 1) | 1
                    self._floats_dict[box.getfloat()] = v
                    self._floats.append(box.getfloat())
                return tag(TAGCONSTOTHER, v)
            else:
                self._consts_ptr += 1
                assert isinstance(box, ConstPtr)
                if not box.getref_base():
                    return tag(TAGCONSTPTR, 0)
                addr = llmemory.cast_ptr_to_adr(box.getref_base())
                v = self._refs_dict.get(addr, -1)
                if v == -1:
                    v = len(self._refs)
                    self._refs_dict[addr] = v
                    self._refs.append(box.getref_base())
                return tag(TAGCONSTPTR, v)
        elif isinstance(box, AbstractResOp):
            return tag(TAGBOX, box.get_position())
        elif isinstance(box, AbstractInputArg):
            return tag(TAGBOX, box.get_position())
        else:
            assert False, "unreachable code"

    def _record_op(self, opnum, argboxes, descr=None):
        pos = self._count
        self.append(opnum)
        expected_arity = oparity[opnum]
        if expected_arity == -1:
            self.append(len(argboxes))
        else:
            assert len(argboxes) == expected_arity
        for box in argboxes:
            self.append(self._encode(box))
        if opwithdescr[opnum]:
            if descr is None:
                self.append(-1)
            else:
                self.append(self._encode_descr(descr))
        self._count += 1
        return pos

    def _record_raw(self, opnum, tagged_args, tagged_descr=-1):
        NOT_USED
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
        lower = pos & 0x7fff
        upper = pos >> 15
        self.append(-upper-1)
        self.append(lower)

    def record_op(self, opnum, argboxes, descr=None):
        # return an ResOperation instance, ideally die in hell
        pos = self._record_op(opnum, argboxes, descr)
        assert opnum >= 0
        return ResOperation(opnum, argboxes, pos, descr)

    def record_op_tag(self, opnum, tagged_args, descr=None):
        NOT_USED
        return tag(TAGBOX, self._record_raw(opnum, tagged_args, descr))

    def record_snapshot(self, jitcode, pc, active_boxes):
        pos = self._pos
        self.append(len(active_boxes)) # unnecessary, can be read from
        self.append(jitcode.index)
        self.append(pc)
        for box in active_boxes:
            self.append(self._encode(box)) # not tagged, as it must be boxes
        return pos

    def record_list_of_boxes(self, boxes):
        self.append(len(boxes))
        for box in boxes:
            self.append(self._encode(box))

    def get_patchable_position(self):
        p = self._pos
        self.append(-1)
        return p

    def patch_position_to_current(self, p):
        prev = self._ops[p]
        assert rffi.cast(lltype.Signed, prev) == -1
        self._snapshot_lgt += self._pos - p
        self._ops[p] = rffi.cast(rffi.SHORT, self._pos - p)

    def check_snapshot_jitcode_pc(self, jitcode, pc, resumedata_pos):
        # XXX expensive?
        assert self._ops[resumedata_pos + 1] == rffi.cast(rffi.SHORT, jitcode.index)
        assert self._ops[resumedata_pos + 2] == rffi.cast(rffi.SHORT, pc)

    def get_iter(self):
        return TraceIterator(self, 0, self._pos)

    def unpack(self):
        iter = self.get_iter()
        ops = []
        while not iter.done():
            ops.append(iter.next())
        return ops

def tag(kind, pos):
    #if not SMALL_INT_START <= pos < SMALL_INT_STOP:
    #    raise some error
    return (pos << TAGSHIFT) | kind

def untag(tagged):
    return intmask(tagged) & TAGMASK, intmask(tagged) >> TAGSHIFT
