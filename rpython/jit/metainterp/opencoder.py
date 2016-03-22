
""" Storage format:
for each operation (inputargs numbered with negative numbers)
<opnum> [size-if-unknown-arity] [<arg0> <arg1> ...] [descr] [potential snapshot]
snapshot is as follows
<total size of snapshot> <virtualizable size> <virtualizable boxes>
<virtualref size> <virtualref boxes> [<size> <jitcode> <pc> <boxes...> ...]
"""

from rpython.jit.metainterp.history import ConstInt, Const, ConstFloat, ConstPtr
from rpython.jit.metainterp.resoperation import AbstractResOp, AbstractInputArg,\
    ResOperation, oparity, rop, opwithdescr, GuardResOp, IntOp, FloatOp, RefOp,\
    opclasses
from rpython.rlib.rarithmetic import intmask, r_uint
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
    def __init__(self, main_iter, snapshot):
        self.main_iter = main_iter
        # reverse the snapshots and store the vable, vref lists
        assert isinstance(snapshot, TopSnapshot)
        self.vable_array = snapshot.vable_array
        self.vref_array = snapshot.vref_array
        self.size = len(self.vable_array) + len(self.vref_array) + 2
        jc_index, pc = unpack_uint(snapshot.packed_jitcode_pc)
        self.framestack = []
        if jc_index == 2**16-1:
            return
        while snapshot:
            self.framestack.append(snapshot)
            self.size += len(snapshot.box_array) + 2
            snapshot = snapshot.prev
        self.framestack.reverse()

    def get(self, index):
        return self.main_iter._untag(index)

    def _update_liverange(self, item, index, liveranges):
        tag, v = untag(item)
        if tag == TAGBOX:
            liveranges[v] = index

    def update_liveranges(self, index, liveranges):
        for item in self.vable_array:
            self._update_liverange(item, index, liveranges)
        for item in self.vref_array:
            self._update_liverange(item, index, liveranges)
        for frame in self.framestack:
            for item in frame.box_array:
                self._update_liverange(item, index, liveranges)

    def unpack_jitcode_pc(self, snapshot):
        return unpack_uint(snapshot.packed_jitcode_pc)

    def unpack_array(self, arr):
        # NOT_RPYTHON
        return [self.get(i) for i in arr]

class TraceIterator(BaseTrace):
    def __init__(self, trace, start, end, force_inputargs=None,
                 metainterp_sd=None):
        self.trace = trace
        self.metainterp_sd = metainterp_sd
        self._cache = [None] * trace._count
        if force_inputargs is not None:
            self.inputargs = [rop.inputarg_from_tp(arg.type) for
                              arg in force_inputargs]
            for i, arg in enumerate(force_inputargs):
                self._cache[arg.get_position()] = self.inputargs[i]
        else:
            self.inputargs = [rop.inputarg_from_tp(arg.type) for
                              arg in self.trace.inputargs]
            for i, arg in enumerate(self.inputargs):
               self._cache[i] = arg
        self.start = start
        self.pos = start
        self._count = start
        self.start_index = start
        self.end = end

    def get_dead_ranges(self, metainterp_sd=None):
        return self.trace.get_dead_ranges(self.metainterp_sd)

    def kill_cache_at(self, pos):
        if pos:
            self._cache[pos] = None

    def _get(self, i):
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

    def get_snapshot_iter(self, index):
        return SnapshotIterator(self, self.trace._snapshots[index])

    def next_element_update_live_range(self, index, liveranges):
        opnum = self._next()
        if oparity[opnum] == -1:
            argnum = self._next()
        else:
            argnum = oparity[opnum]
        for i in range(argnum):
            tagged = self._next()
            tag, v = untag(tagged)
            if tag == TAGBOX:
                liveranges[v] = index
        if opclasses[opnum].type != 'v':
            liveranges[index] = index
        if opwithdescr[opnum]:
            descr_index = self._next()
            if rop.is_guard(opnum):
                self.get_snapshot_iter(descr_index).update_liveranges(
                    index, liveranges)
        return index + 1

    def next(self):
        opnum = self._next()
        if oparity[opnum] == -1:
            argnum = self._next()
        else:
            argnum = oparity[opnum]
        args = []
        for i in range(argnum):
            args.append(self._untag(self._next()))
        descr_index = -1
        if opwithdescr[opnum]:
            descr_index = self._next()
            if descr_index == 0 or rop.is_guard(opnum):
                descr = None
            else:
                if descr_index < 0:
                    descr = self.metainterp_sd.all_descrs[-descr_index-1]
                else:
                    descr = self.trace._descrs[descr_index]
        else:
            descr = None
        res = ResOperation(opnum, args, descr=descr)
        if rop.is_guard(opnum):
            assert isinstance(res, GuardResOp)
            res.rd_resume_position = descr_index
        if res.type != 'v':
            self._cache[self._count] = res
        self._count += 1
        return res

class CutTrace(BaseTrace):
    def __init__(self, trace, start, count, inputargs):
        self.trace = trace
        self.start = start
        self.inputargs = inputargs
        self.count = count

    def get_iter(self, metainterp_sd=None):
        iter = TraceIterator(self.trace, self.start, self.trace._pos,
                             self.inputargs, metainterp_sd=metainterp_sd)
        iter._count = self.count
        iter.start_index = self.count
        return iter

def combine_uint(index1, index2):
    assert 0 <= index1 < 65536
    assert 0 <= index2 < 65536
    return index1 << 16 | index2 # it's ok to return signed here,
    # we need only 32bit, but 64 is ok for now

def unpack_uint(packed):
    return (packed >> 16) & 0xffff, packed & 0xffff

class Snapshot(object):
    _attrs_ = ('packed_jitcode_pc', 'box_array', 'prev')

    prev = None

    def __init__(self, packed_jitcode_pc, box_array):
        self.packed_jitcode_pc = packed_jitcode_pc
        self.box_array = box_array

class TopSnapshot(Snapshot):
    def __init__(self, packed_jitcode_pc, box_array, vable_array, vref_array):
        Snapshot.__init__(self, packed_jitcode_pc, box_array)
        self.vable_array = vable_array
        self.vref_array = vref_array

class Trace(BaseTrace):
    _deadranges = (-1, None)

    def __init__(self, inputargs):
        self._ops = [rffi.cast(rffi.SHORT, -15)] * 30000
        self._pos = 0
        self._consts_bigint = 0
        self._consts_float = 0
        self._total_snapshots = 0
        self._consts_ptr = 0
        self._descrs = [None]
        self._refs = [lltype.nullptr(llmemory.GCREF.TO)]
        self._refs_dict = llhelper.new_ref_dict_3()
        self._bigints = []
        self._bigints_dict = {}
        self._floats = []
        self._floats_dict = {}
        self._snapshots = []
        for i, inparg in enumerate(inputargs):
            inparg.set_position(i)
        self._count = len(inputargs)
        self._start = len(inputargs)
        self._pos = self._start
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
        debug_print(" total snapshots: " + str(self._total_snapshots))
        debug_print(" bigint consts: " + str(self._consts_bigint) + " " + str(len(self._bigints)))
        debug_print(" float consts: " + str(self._consts_float) + " " + str(len(self._floats)))
        debug_print(" ref consts: " + str(self._consts_ptr) + " " + str(len(self._refs)))
        debug_print(" descrs: " + str(len(self._descrs)))
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
                    # XXX the next line is bogus, can't use a float as
                    # dict key.  Must convert it first to a longlong
                    self._floats_dict[box.getfloat()] = v
                    self._floats.append(box.getfloat())
                return tag(TAGCONSTOTHER, v)
            else:
                self._consts_ptr += 1
                assert isinstance(box, ConstPtr)
                if not box.getref_base():
                    return tag(TAGCONSTPTR, 0)
                addr = box.getref_base()
                v = self._refs_dict.get(addr, -1)
                if v == -1:
                    v = len(self._refs)
                    self._refs_dict[addr] = v
                    self._refs.append(box.getref_base())
                return tag(TAGCONSTPTR, v)
        elif isinstance(box, AbstractResOp):
            assert box.get_position() >= 0
            return tag(TAGBOX, box.get_position())
        else:
            assert False, "unreachable code"

    def record_op(self, opnum, argboxes, descr=None):
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
                self.append(0)
            else:
                self.append(self._encode_descr(descr))
        self._count += 1
        return pos

    def _encode_descr(self, descr):
        if descr.descr_index != -1:
            return -descr.descr_index-1
        self._descrs.append(descr)
        return len(self._descrs) - 1

    def _list_of_boxes(self, boxes):
        array = [rffi.cast(rffi.SHORT, 0)] * len(boxes)
        for i in range(len(boxes)):
            array[i] = self._encode(boxes[i])
        return array

    def new_array(self, lgt):
        return [rffi.cast(rffi.SHORT, 0)] * lgt

    def create_top_snapshot(self, jitcode, pc, frame, flag, vable_boxes, vref_boxes):
        self._total_snapshots += 1
        array = frame.get_list_of_active_boxes(flag, self.new_array, self._encode)
        vable_array = self._list_of_boxes(vable_boxes)
        vref_array = self._list_of_boxes(vref_boxes)
        s = TopSnapshot(combine_uint(jitcode.index, pc), array, vable_array,
                        vref_array)
        assert rffi.cast(lltype.Signed, self._ops[self._pos - 1]) == 0
        # guards have no descr
        self._snapshots.append(s)
        self._ops[self._pos - 1] = rffi.cast(rffi.SHORT, len(self._snapshots) - 1)
        return s

    def create_empty_top_snapshot(self, vable_boxes, vref_boxes):
        self._total_snapshots += 1
        vable_array = self._list_of_boxes(vable_boxes)
        vref_array = self._list_of_boxes(vref_boxes)
        s = TopSnapshot(combine_uint(2**16 - 1, 0), [], vable_array,
                        vref_array)
        assert rffi.cast(lltype.Signed, self._ops[self._pos - 1]) == 0
        # guards have no descr
        self._snapshots.append(s)
        self._ops[self._pos - 1] = rffi.cast(rffi.SHORT, len(self._snapshots) - 1)
        return s

    def create_snapshot(self, jitcode, pc, frame, flag):
        self._total_snapshots += 1
        array = frame.get_list_of_active_boxes(flag, self.new_array, self._encode)
        return Snapshot(combine_uint(jitcode.index, pc), array)

    def get_iter(self, metainterp_sd=None):
        assert metainterp_sd
        return TraceIterator(self, self._start, self._pos, metainterp_sd=metainterp_sd)

    def get_live_ranges(self, metainterp_sd):
        t = self.get_iter(metainterp_sd)
        liveranges = [0] * self._count
        index = t._count
        while not t.done():
            index = t.next_element_update_live_range(index, liveranges)
        return liveranges

    def get_dead_ranges(self, metainterp_sd=None):
        """ Same as get_live_ranges, but returns a list of "dying" indexes,
        such as for each index x, the number found there is for sure dead
        before x
        """
        def insert(ranges, pos, v):
            # XXX skiplist
            while ranges[pos]:
                pos += 1
                if pos == len(ranges):
                    return
            ranges[pos] = v

        if self._deadranges != (-1, None):
            if self._deadranges[0] == self._count:
                return self._deadranges[1]
        liveranges = self.get_live_ranges(metainterp_sd)
        deadranges = [0] * (self._count + 1)
        for i in range(self._start, len(liveranges)):
            elem = liveranges[i]
            if elem:
                insert(deadranges, elem + 1, i)
        self._deadranges = (self._count, deadranges)
        return deadranges

    def unpack(self, metainterp_sd):
        iter = self.get_iter(metainterp_sd)
        ops = []
        while not iter.done():
            ops.append(iter.next())
        return iter.inputargs, ops

def tag(kind, pos):
    #if not SMALL_INT_START <= pos < SMALL_INT_STOP:
    #    raise some error
    return (pos << TAGSHIFT) | kind

def untag(tagged):
    return intmask(tagged) & TAGMASK, intmask(tagged) >> TAGSHIFT
