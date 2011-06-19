import sys, os
from pypy.jit.metainterp.history import Box, Const, ConstInt, getkind
from pypy.jit.metainterp.history import BoxInt, BoxPtr, BoxFloat
from pypy.jit.metainterp.history import INT, REF, FLOAT, HOLE
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp import jitprof
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr
from pypy.rlib import rarithmetic, rstack
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.rlib.debug import have_debug_prints, ll_assert
from pypy.rlib.debug import debug_start, debug_stop, debug_print
from pypy.jit.metainterp.optimize import InvalidLoop

# Logic to encode the chain of frames and the state of the boxes at a
# guard operation, and to decode it again.  This is a bit advanced,
# because it needs to support optimize.py which encodes virtuals with
# arbitrary cycles and also to compress the information

class Snapshot(object):
    __slots__ = ('prev', 'boxes')

    def __init__(self, prev, boxes):
        self.prev = prev
        self.boxes = boxes

class FrameInfo(object):
    __slots__ = ('prev', 'jitcode', 'pc')

    def __init__(self, prev, jitcode, pc):
        self.prev = prev
        self.jitcode = jitcode
        self.pc = pc

def _ensure_parent_resumedata(framestack, n):
    target = framestack[n]
    if n == 0:
        return
    back = framestack[n-1]
    if target.parent_resumedata_frame_info_list is not None:
        assert target.parent_resumedata_frame_info_list.pc == back.pc
        return
    _ensure_parent_resumedata(framestack, n-1)
    target.parent_resumedata_frame_info_list = FrameInfo(
                                         back.parent_resumedata_frame_info_list,
                                         back.jitcode,
                                         back.pc)
    target.parent_resumedata_snapshot = Snapshot(
                                         back.parent_resumedata_snapshot,
                                         back.get_list_of_active_boxes(True))

def capture_resumedata(framestack, virtualizable_boxes, virtualref_boxes,
                       storage):
    n = len(framestack)-1
    top = framestack[n]
    _ensure_parent_resumedata(framestack, n)
    frame_info_list = FrameInfo(top.parent_resumedata_frame_info_list,
                                top.jitcode, top.pc)
    storage.rd_frame_info_list = frame_info_list
    snapshot = Snapshot(top.parent_resumedata_snapshot,
                        top.get_list_of_active_boxes(False))
    if virtualizable_boxes is not None:
        boxes = virtualref_boxes + virtualizable_boxes
    else:
        boxes = virtualref_boxes[:]
    snapshot = Snapshot(snapshot, boxes)
    storage.rd_snapshot = snapshot

#
# The following is equivalent to the RPython-level declaration:
#
#     class Numbering: __slots__ = ['prev', 'nums']
#
# except that it is more compact in translated programs, because the
# array 'nums' is inlined in the single NUMBERING object.  This is
# important because this is often the biggest single consumer of memory
# in a pypy-c-jit.
#
NUMBERINGP = lltype.Ptr(lltype.GcForwardReference())
NUMBERING = lltype.GcStruct('Numbering',
                            ('prev', NUMBERINGP),
                            ('nums', lltype.Array(rffi.SHORT)))
NUMBERINGP.TO.become(NUMBERING)

TAGMASK = 3

def tag(value, tagbits):
    if tagbits >> 2:
        raise ValueError
    sx = value >> 13
    if sx != 0 and sx != -1:
        raise ValueError
    return rffi.r_short(value<<2|tagbits)

def untag(value):
    value = rarithmetic.widen(value)
    tagbits = value&TAGMASK
    return value>>2, tagbits

def tagged_eq(x, y):
    # please rpython :(
    return rarithmetic.widen(x) == rarithmetic.widen(y)

def tagged_list_eq(tl1, tl2):
    if len(tl1) != len(tl2):
        return False
    for i in range(len(tl1)):
        if not tagged_eq(tl1[i], tl2[i]):
            return False
    return True

TAGCONST    = 0
TAGINT      = 1
TAGBOX      = 2
TAGVIRTUAL  = 3

UNASSIGNED = tag(-1<<13, TAGBOX)
UNASSIGNEDVIRTUAL = tag(-1<<13, TAGVIRTUAL)
NULLREF = tag(-1, TAGCONST)


class ResumeDataLoopMemo(object):

    def __init__(self, metainterp_sd):
        self.metainterp_sd = metainterp_sd
        self.cpu = metainterp_sd.cpu
        self.consts = []
        self.large_ints = {}
        self.refs = self.cpu.ts.new_ref_dict_2()
        self.numberings = {}
        self.cached_boxes = {}
        self.cached_virtuals = {}
    
        self.nvirtuals = 0
        self.nvholes = 0
        self.nvreused = 0

    def getconst(self, const):
        if const.type == INT:
            val = const.getint()
            if not we_are_translated() and not isinstance(val, int):
                # unhappiness, probably a symbolic
                return self._newconst(const)
            try:
                return tag(val, TAGINT)
            except ValueError:
                pass
            tagged = self.large_ints.get(val, UNASSIGNED)
            if not tagged_eq(tagged, UNASSIGNED):
                return tagged
            tagged = self._newconst(const)
            self.large_ints[val] = tagged
            return tagged
        elif const.type == REF:
            val = const.getref_base()
            if not val:
                return NULLREF
            tagged = self.refs.get(val, UNASSIGNED)
            if not tagged_eq(tagged, UNASSIGNED):
                return tagged
            tagged = self._newconst(const)
            self.refs[val] = tagged
            return tagged
        return self._newconst(const)

    def _newconst(self, const):
        result = tag(len(self.consts), TAGCONST)
        self.consts.append(const)
        return result

    # env numbering

    def number(self, values, snapshot):
        if snapshot is None:
            return lltype.nullptr(NUMBERING), {}, 0
        if snapshot in self.numberings:
             numb, liveboxes, v = self.numberings[snapshot]
             return numb, liveboxes.copy(), v

        numb1, liveboxes, v = self.number(values, snapshot.prev)
        n = len(liveboxes)-v
        boxes = snapshot.boxes
        length = len(boxes)
        numb = lltype.malloc(NUMBERING, length)
        for i in range(length):
            box = boxes[i]
            value = values.get(box, None)
            if value is not None:
                box = value.get_key_box()

            if isinstance(box, Const):
                tagged = self.getconst(box)
            elif box in liveboxes:
                tagged = liveboxes[box]
            else:
                if value is not None and value.is_virtual():
                    tagged = tag(v, TAGVIRTUAL)
                    v += 1
                else:
                    tagged = tag(n, TAGBOX)
                    n += 1
                liveboxes[box] = tagged
            numb.nums[i] = tagged
        #
        numb.prev = numb1
        self.numberings[snapshot] = numb, liveboxes, v
        return numb, liveboxes.copy(), v

    def forget_numberings(self, virtualbox):
        # XXX ideally clear only the affected numberings
        self.numberings.clear()
        self.clear_box_virtual_numbers()

    # caching for virtuals and boxes inside them

    def num_cached_boxes(self):
        return len(self.cached_boxes)

    def assign_number_to_box(self, box, boxes):
        # returns a negative number
        if box in self.cached_boxes:
            num = self.cached_boxes[box]
            boxes[-num-1] = box
        else:
            boxes.append(box)
            num = -len(boxes)
            self.cached_boxes[box] = num
        return num

    def num_cached_virtuals(self):
        return len(self.cached_virtuals)

    def assign_number_to_virtual(self, box):
        # returns a negative number
        if box in self.cached_virtuals:
            num = self.cached_virtuals[box]
        else:
            num = self.cached_virtuals[box] = -len(self.cached_virtuals) - 1
        return num

    def clear_box_virtual_numbers(self):
        self.cached_boxes.clear()
        self.cached_virtuals.clear()

    def update_counters(self, profiler):
        profiler.count(jitprof.NVIRTUALS, self.nvirtuals)
        profiler.count(jitprof.NVHOLES, self.nvholes)
        profiler.count(jitprof.NVREUSED, self.nvreused)

_frame_info_placeholder = (None, 0, 0)

class ResumeDataVirtualAdder(object):

    def __init__(self, storage, memo):
        self.storage = storage
        self.memo = memo

    def make_virtual(self, known_class, fielddescrs):
        return VirtualInfo(known_class, fielddescrs)

    def make_vstruct(self, typedescr, fielddescrs):
        return VStructInfo(typedescr, fielddescrs)

    def make_varray(self, arraydescr):
        return VArrayInfo(arraydescr)

    def make_vstrplain(self, is_unicode=False):
        if is_unicode:
            return VUniPlainInfo()
        return VStrPlainInfo()

    def make_vstrconcat(self, is_unicode=False):
        if is_unicode:
            return VUniConcatInfo()
        return VStrConcatInfo()

    def make_vstrslice(self, is_unicode=False):
        if is_unicode:
            return VUniSliceInfo()
        return VStrSliceInfo()

    def register_virtual_fields(self, virtualbox, fieldboxes):
        tagged = self.liveboxes_from_env.get(virtualbox, UNASSIGNEDVIRTUAL)
        self.liveboxes[virtualbox] = tagged
        self.vfieldboxes[virtualbox] = fieldboxes
        self._register_boxes(fieldboxes)

    def register_box(self, box):
        if (isinstance(box, Box) and box not in self.liveboxes_from_env
                                 and box not in self.liveboxes):
            self.liveboxes[box] = UNASSIGNED

    def _register_boxes(self, boxes):
        for box in boxes:
            self.register_box(box)

    def already_seen_virtual(self, virtualbox):
        if virtualbox not in self.liveboxes:
            assert virtualbox in self.liveboxes_from_env
            assert untag(self.liveboxes_from_env[virtualbox])[1] == TAGVIRTUAL
            return False
        tagged = self.liveboxes[virtualbox]
        _, tagbits = untag(tagged)
        return tagbits == TAGVIRTUAL

    def finish(self, values, pending_setfields=[]):
        # compute the numbering
        storage = self.storage
        # make sure that nobody attached resume data to this guard yet
        assert not storage.rd_numb
        snapshot = storage.rd_snapshot
        assert snapshot is not None # is that true?
        numb, liveboxes_from_env, v = self.memo.number(values, snapshot)
        self.liveboxes_from_env = liveboxes_from_env
        self.liveboxes = {}
        storage.rd_numb = numb
        storage.rd_snapshot = None

        # collect liveboxes and virtuals
        n = len(liveboxes_from_env) - v
        liveboxes = [None]*n
        self.vfieldboxes = {}
        for box, tagged in liveboxes_from_env.iteritems():
            i, tagbits = untag(tagged)
            if tagbits == TAGBOX:
                liveboxes[i] = box
            else:
                assert tagbits == TAGVIRTUAL
                value = values[box]
                value.get_args_for_fail(self)

        for _, box, fieldbox in pending_setfields:
            self.register_box(box)
            self.register_box(fieldbox)
            value = values[fieldbox]
            value.get_args_for_fail(self)

        self._number_virtuals(liveboxes, values, v)
        self._add_pending_fields(pending_setfields)

        storage.rd_consts = self.memo.consts
        dump_storage(storage, liveboxes)
        return liveboxes[:]

    def _number_virtuals(self, liveboxes, values, num_env_virtuals):
        # !! 'liveboxes' is a list that is extend()ed in-place !!
        memo = self.memo
        new_liveboxes = [None] * memo.num_cached_boxes()
        count = 0
        # So far, self.liveboxes should contain 'tagged' values that are
        # either UNASSIGNED, UNASSIGNEDVIRTUAL, or a *non-negative* value
        # with the TAGVIRTUAL.  The following loop removes the UNASSIGNED
        # and UNASSIGNEDVIRTUAL entries, and replaces them with real
        # negative values.
        for box, tagged in self.liveboxes.iteritems():
            i, tagbits = untag(tagged)
            if tagbits == TAGBOX:
                assert box not in self.liveboxes_from_env
                assert tagged_eq(tagged, UNASSIGNED)
                index = memo.assign_number_to_box(box, new_liveboxes)
                self.liveboxes[box] = tag(index, TAGBOX)
                count += 1
            else:
                assert tagbits == TAGVIRTUAL
                if tagged_eq(tagged, UNASSIGNEDVIRTUAL):
                    assert box not in self.liveboxes_from_env
                    index = memo.assign_number_to_virtual(box)
                    self.liveboxes[box] = tag(index, TAGVIRTUAL)
                else:
                    assert i >= 0
        new_liveboxes.reverse()
        liveboxes.extend(new_liveboxes)
        nholes = len(new_liveboxes) - count

        storage = self.storage
        storage.rd_virtuals = None
        vfieldboxes = self.vfieldboxes
        if vfieldboxes:
            length = num_env_virtuals + memo.num_cached_virtuals()
            virtuals = storage.rd_virtuals = [None] * length
            memo.nvirtuals += length
            memo.nvholes += length - len(vfieldboxes)
            for virtualbox, fieldboxes in vfieldboxes.iteritems():
                num, _ = untag(self.liveboxes[virtualbox])
                value = values[virtualbox]
                fieldnums = [self._gettagged(box)
                             for box in fieldboxes]
                vinfo = value.make_virtual_info(self, fieldnums)
                # if a new vinfo instance is made, we get the fieldnums list we
                # pass in as an attribute. hackish.
                if vinfo.fieldnums is not fieldnums:
                    memo.nvreused += 1
                virtuals[num] = vinfo

        if self._invalidation_needed(len(liveboxes), nholes):
            memo.clear_box_virtual_numbers()           

    def _invalidation_needed(self, nliveboxes, nholes):
        memo = self.memo
        # xxx heuristic a bit out of thin air
        failargs_limit = memo.metainterp_sd.options.failargs_limit
        if nliveboxes > (failargs_limit // 2):
            if nholes > nliveboxes//3:
                return True
        return False

    def _add_pending_fields(self, pending_setfields):
        rd_pendingfields = None
        if pending_setfields:
            rd_pendingfields = []
            for descr, box, fieldbox in pending_setfields:
                num = self._gettagged(box)
                fieldnum = self._gettagged(fieldbox)
                rd_pendingfields.append((descr, num, fieldnum))
        self.storage.rd_pendingfields = rd_pendingfields

    def _gettagged(self, box):
        if isinstance(box, Const):
            return self.memo.getconst(box)
        else:
            if box in self.liveboxes_from_env:
                return self.liveboxes_from_env[box]
            return self.liveboxes[box]


class AbstractVirtualInfo(object):
    #def allocate(self, decoder, index):
    #    raise NotImplementedError
    def equals(self, fieldnums):
        return tagged_list_eq(self.fieldnums, fieldnums)

    def set_content(self, fieldnums):
        self.fieldnums = fieldnums

    def debug_prints(self):
        raise NotImplementedError
        
class AbstractVirtualStructInfo(AbstractVirtualInfo):
    def __init__(self, fielddescrs):
        self.fielddescrs = fielddescrs
        #self.fieldnums = ...

    @specialize.argtype(1)
    def setfields(self, decoder, struct):
        for i in range(len(self.fielddescrs)):
            descr = self.fielddescrs[i]
            decoder.setfield(descr, struct, self.fieldnums[i])
        return struct

    def debug_prints(self):
        assert len(self.fielddescrs) == len(self.fieldnums)
        for i in range(len(self.fielddescrs)):
            debug_print("\t\t",
                        str(self.fielddescrs[i]),
                        str(untag(self.fieldnums[i])))

class VirtualInfo(AbstractVirtualStructInfo):
    def __init__(self, known_class, fielddescrs):
        AbstractVirtualStructInfo.__init__(self, fielddescrs)
        self.known_class = known_class

    @specialize.argtype(1)
    def allocate(self, decoder, index):
        struct = decoder.allocate_with_vtable(self.known_class)
        decoder.virtuals_cache[index] = struct
        return self.setfields(decoder, struct)

    def debug_prints(self):
        debug_print("\tvirtualinfo", self.known_class.repr_rpython())
        AbstractVirtualStructInfo.debug_prints(self)


class VStructInfo(AbstractVirtualStructInfo):
    def __init__(self, typedescr, fielddescrs):
        AbstractVirtualStructInfo.__init__(self, fielddescrs)
        self.typedescr = typedescr

    @specialize.argtype(1)
    def allocate(self, decoder, index):
        struct = decoder.allocate_struct(self.typedescr)
        decoder.virtuals_cache[index] = struct
        return self.setfields(decoder, struct)

    def debug_prints(self):
        debug_print("\tvstructinfo", self.typedescr.repr_rpython())
        AbstractVirtualStructInfo.debug_prints(self)

class VArrayInfo(AbstractVirtualInfo):
    def __init__(self, arraydescr):
        self.arraydescr = arraydescr
        #self.fieldnums = ...

    @specialize.argtype(1)
    def allocate(self, decoder, index):
        length = len(self.fieldnums)
        arraydescr = self.arraydescr
        array = decoder.allocate_array(arraydescr, length)
        decoder.virtuals_cache[index] = array
        # NB. the check for the kind of array elements is moved out of the loop
        if arraydescr.is_array_of_pointers():
            for i in range(length):
                decoder.setarrayitem_ref(arraydescr, array, i,
                                         self.fieldnums[i])
        elif arraydescr.is_array_of_floats():
            for i in range(length):
                decoder.setarrayitem_float(arraydescr, array, i,
                                           self.fieldnums[i])
        else:
            for i in range(length):
                decoder.setarrayitem_int(arraydescr, array, i,
                                         self.fieldnums[i])
        return array

    def debug_prints(self):
        debug_print("\tvarrayinfo", self.arraydescr)
        for i in self.fieldnums:
            debug_print("\t\t", str(untag(i)))

class VStrPlainInfo(AbstractVirtualInfo):
    """Stands for the string made out of the characters of all fieldnums."""

    @specialize.argtype(1)
    def allocate(self, decoder, index):
        length = len(self.fieldnums)
        string = decoder.allocate_string(length)
        decoder.virtuals_cache[index] = string
        for i in range(length):
            decoder.string_setitem(string, i, self.fieldnums[i])
        return string

    def debug_prints(self):
        debug_print("\tvstrplaininfo length", len(self.fieldnums))


class VStrConcatInfo(AbstractVirtualInfo):
    """Stands for the string made out of the concatenation of two
    other strings."""

    @specialize.argtype(1)
    def allocate(self, decoder, index):
        # xxx for blackhole resuming, this will build all intermediate
        # strings and throw them away immediately, which is a bit sub-
        # efficient.  Not sure we care.
        left, right = self.fieldnums
        string = decoder.concat_strings(left, right)
        decoder.virtuals_cache[index] = string
        return string

    def debug_prints(self):
        debug_print("\tvstrconcatinfo")
        for i in self.fieldnums:
            debug_print("\t\t", str(untag(i)))


class VStrSliceInfo(AbstractVirtualInfo):
    """Stands for the string made out of slicing another string."""

    @specialize.argtype(1)
    def allocate(self, decoder, index):
        largerstr, start, length = self.fieldnums
        string = decoder.slice_string(largerstr, start, length)
        decoder.virtuals_cache[index] = string
        return string

    def debug_prints(self):
        debug_print("\tvstrsliceinfo")
        for i in self.fieldnums:
            debug_print("\t\t", str(untag(i)))


class VUniPlainInfo(AbstractVirtualInfo):
    """Stands for the unicode string made out of the characters of all
    fieldnums."""

    @specialize.argtype(1)
    def allocate(self, decoder, index):
        length = len(self.fieldnums)
        string = decoder.allocate_unicode(length)
        decoder.virtuals_cache[index] = string
        for i in range(length):
            decoder.unicode_setitem(string, i, self.fieldnums[i])
        return string

    def debug_prints(self):
        debug_print("\tvuniplaininfo length", len(self.fieldnums))


class VUniConcatInfo(AbstractVirtualInfo):
    """Stands for the unicode string made out of the concatenation of two
    other unicode strings."""

    @specialize.argtype(1)
    def allocate(self, decoder, index):
        # xxx for blackhole resuming, this will build all intermediate
        # strings and throw them away immediately, which is a bit sub-
        # efficient.  Not sure we care.
        left, right = self.fieldnums
        string = decoder.concat_unicodes(left, right)
        decoder.virtuals_cache[index] = string
        return string

    def debug_prints(self):
        debug_print("\tvuniconcatinfo")
        for i in self.fieldnums:
            debug_print("\t\t", str(untag(i)))


class VUniSliceInfo(AbstractVirtualInfo):
    """Stands for the unicode string made out of slicing another
    unicode string."""

    @specialize.argtype(1)
    def allocate(self, decoder, index):
        largerstr, start, length = self.fieldnums
        string = decoder.slice_unicode(largerstr, start, length)
        decoder.virtuals_cache[index] = string
        return string

    def debug_prints(self):
        debug_print("\tvunisliceinfo")
        for i in self.fieldnums:
            debug_print("\t\t", str(untag(i)))

# ____________________________________________________________

class AbstractResumeDataReader(object):
    """A base mixin containing the logic to reconstruct virtuals out of
    guard failure.  There are two implementations of this mixin:
    ResumeDataBoxReader for when we are compiling (i.e. when we have a
    metainterp), and ResumeDataDirectReader for when we are merely
    blackholing and want the best performance.
    """
    _mixin_ = True
    rd_virtuals = None
    virtuals_cache = None
    virtual_default = None

    def _init(self, cpu, storage):
        self.cpu = cpu
        self.cur_numb = storage.rd_numb
        self.consts = storage.rd_consts

    def _prepare(self, storage):
        self._prepare_virtuals(storage.rd_virtuals)
        self._prepare_pendingfields(storage.rd_pendingfields)

    def getvirtual(self, index):
        # Returns the index'th virtual, building it lazily if needed.
        # Note that this may be called recursively; that's why the
        # allocate() methods must fill in the cache as soon as they
        # have the object, before they fill its fields.
        assert self.virtuals_cache is not None
        v = self.virtuals_cache[index]
        if not v:
            v = self.rd_virtuals[index].allocate(self, index)
            ll_assert(v == self.virtuals_cache[index], "resume.py: bad cache")
        return v

    def force_all_virtuals(self):
        rd_virtuals = self.rd_virtuals
        if rd_virtuals:
            for i in range(len(rd_virtuals)):
                if rd_virtuals[i] is not None:
                    self.getvirtual(i)
        return self.virtuals_cache

    def _prepare_virtuals(self, virtuals):
        if virtuals:
            self.rd_virtuals = virtuals
            self.virtuals_cache = [self.virtual_default] * len(virtuals)

    def _prepare_pendingfields(self, pendingfields):
        if pendingfields is not None:
            for descr, num, fieldnum in pendingfields:
                struct = self.decode_ref(num)
                self.setfield(descr, struct, fieldnum)

    def _prepare_next_section(self, info):
        # Use info.enumerate_vars(), normally dispatching to
        # pypy.jit.codewriter.jitcode.  Some tests give a different 'info'.
        info.enumerate_vars(self._callback_i,
                            self._callback_r,
                            self._callback_f,
                            self.unique_id)    # <-- annotation hack
        self.cur_numb = self.cur_numb.prev

    def _callback_i(self, index, register_index):
        value = self.decode_int(self.cur_numb.nums[index])
        self.write_an_int(register_index, value)

    def _callback_r(self, index, register_index):
        value = self.decode_ref(self.cur_numb.nums[index])
        self.write_a_ref(register_index, value)

    def _callback_f(self, index, register_index):
        value = self.decode_float(self.cur_numb.nums[index])
        self.write_a_float(register_index, value)

    def done(self):
        self.cpu.clear_latest_values(self.cpu.get_latest_value_count())

# ---------- when resuming for pyjitpl.py, make boxes ----------

def rebuild_from_resumedata(metainterp, storage, virtualizable_info,
                            greenfield_info):
    resumereader = ResumeDataBoxReader(storage, metainterp)
    boxes = resumereader.consume_vref_and_vable_boxes(virtualizable_info,
                                                      greenfield_info)
    virtualizable_boxes, virtualref_boxes = boxes
    frameinfo = storage.rd_frame_info_list
    while True:
        f = metainterp.newframe(frameinfo.jitcode)
        f.setup_resume_at_op(frameinfo.pc)
        resumereader.consume_boxes(f.get_current_position_info(),
                                   f.registers_i, f.registers_r, f.registers_f)
        frameinfo = frameinfo.prev
        if frameinfo is None:
            break
    metainterp.framestack.reverse()
    resumereader.done()
    return resumereader.liveboxes, virtualizable_boxes, virtualref_boxes

class ResumeDataBoxReader(AbstractResumeDataReader):
    unique_id = lambda: None

    def __init__(self, storage, metainterp):
        self._init(metainterp.cpu, storage)
        self.metainterp = metainterp
        self.liveboxes = [None] * metainterp.cpu.get_latest_value_count()
        self._prepare(storage)

    def consume_boxes(self, info, boxes_i, boxes_r, boxes_f):
        self.boxes_i = boxes_i
        self.boxes_r = boxes_r
        self.boxes_f = boxes_f
        self._prepare_next_section(info)

    def consume_virtualizable_boxes(self, vinfo, numb):
        # we have to ignore the initial part of 'nums' (containing vrefs),
        # find the virtualizable from nums[-1], and use it to know how many
        # boxes of which type we have to return.  This does not write
        # anything into the virtualizable.
        index = len(numb.nums) - 1
        virtualizablebox = self.decode_ref(numb.nums[index])
        virtualizable = vinfo.unwrap_virtualizable_box(virtualizablebox)
        return vinfo.load_list_of_boxes(virtualizable, self, numb)

    def consume_virtualref_boxes(self, numb, end):
        # Returns a list of boxes, assumed to be all BoxPtrs.
        # We leave up to the caller to call vrefinfo.continue_tracing().
        assert (end & 1) == 0
        return [self.decode_ref(numb.nums[i]) for i in range(end)]

    def consume_vref_and_vable_boxes(self, vinfo, ginfo):
        numb = self.cur_numb
        self.cur_numb = numb.prev
        if vinfo is not None:
            virtualizable_boxes = self.consume_virtualizable_boxes(vinfo, numb)
            end = len(numb.nums) - len(virtualizable_boxes)
        elif ginfo is not None:
            index = len(numb.nums) - 1
            virtualizable_boxes = [self.decode_ref(numb.nums[index])]
            end = len(numb.nums) - 1
        else:
            virtualizable_boxes = None
            end = len(numb.nums)
        virtualref_boxes = self.consume_virtualref_boxes(numb, end)
        return virtualizable_boxes, virtualref_boxes

    def allocate_with_vtable(self, known_class):
        return self.metainterp.execute_and_record(rop.NEW_WITH_VTABLE,
                                                  None, known_class)

    def allocate_struct(self, typedescr):
        return self.metainterp.execute_and_record(rop.NEW, typedescr)

    def allocate_array(self, arraydescr, length):
        return self.metainterp.execute_and_record(rop.NEW_ARRAY,
                                                  arraydescr, ConstInt(length))

    def allocate_string(self, length):
        return self.metainterp.execute_and_record(rop.NEWSTR,
                                                  None, ConstInt(length))

    def string_setitem(self, strbox, index, charnum):
        charbox = self.decode_box(charnum, INT)
        self.metainterp.execute_and_record(rop.STRSETITEM, None,
                                           strbox, ConstInt(index), charbox)

    def concat_strings(self, str1num, str2num):
        cic = self.metainterp.staticdata.callinfocollection
        calldescr, func = cic.callinfo_for_oopspec(EffectInfo.OS_STR_CONCAT)
        str1box = self.decode_box(str1num, REF)
        str2box = self.decode_box(str2num, REF)
        return self.metainterp.execute_and_record_varargs(
            rop.CALL, [ConstInt(func), str1box, str2box], calldescr)

    def slice_string(self, strnum, startnum, lengthnum):
        cic = self.metainterp.staticdata.callinfocollection
        calldescr, func = cic.callinfo_for_oopspec(EffectInfo.OS_STR_SLICE)
        strbox = self.decode_box(strnum, REF)
        startbox = self.decode_box(startnum, INT)
        lengthbox = self.decode_box(lengthnum, INT)
        stopbox = self.metainterp.execute_and_record(rop.INT_ADD, None,
                                                     startbox, lengthbox)
        return self.metainterp.execute_and_record_varargs(
            rop.CALL, [ConstInt(func), strbox, startbox, stopbox], calldescr)

    def allocate_unicode(self, length):
        return self.metainterp.execute_and_record(rop.NEWUNICODE,
                                                  None, ConstInt(length))

    def unicode_setitem(self, strbox, index, charnum):
        charbox = self.decode_box(charnum, INT)
        self.metainterp.execute_and_record(rop.UNICODESETITEM, None,
                                           strbox, ConstInt(index), charbox)

    def concat_unicodes(self, str1num, str2num):
        cic = self.metainterp.staticdata.callinfocollection
        calldescr, func = cic.callinfo_for_oopspec(EffectInfo.OS_UNI_CONCAT)
        str1box = self.decode_box(str1num, REF)
        str2box = self.decode_box(str2num, REF)
        return self.metainterp.execute_and_record_varargs(
            rop.CALL, [ConstInt(func), str1box, str2box], calldescr)

    def slice_unicode(self, strnum, startnum, lengthnum):
        cic = self.metainterp.staticdata.callinfocollection
        calldescr, func = cic.callinfo_for_oopspec(EffectInfo.OS_UNI_SLICE)
        strbox = self.decode_box(strnum, REF)
        startbox = self.decode_box(startnum, INT)
        lengthbox = self.decode_box(lengthnum, INT)
        stopbox = self.metainterp.execute_and_record(rop.INT_ADD, None,
                                                     startbox, lengthbox)
        return self.metainterp.execute_and_record_varargs(
            rop.CALL, [ConstInt(func), strbox, startbox, stopbox], calldescr)

    def setfield(self, descr, structbox, fieldnum):
        if descr.is_pointer_field():
            kind = REF
        elif descr.is_float_field():
            kind = FLOAT
        else:
            kind = INT
        fieldbox = self.decode_box(fieldnum, kind)
        self.metainterp.execute_and_record(rop.SETFIELD_GC, descr,
                                           structbox, fieldbox)

    def setarrayitem_int(self, arraydescr, arraybox, index, fieldnum):
        self.setarrayitem(arraydescr, arraybox, index, fieldnum, INT)

    def setarrayitem_ref(self, arraydescr, arraybox, index, fieldnum):
        self.setarrayitem(arraydescr, arraybox, index, fieldnum, REF)

    def setarrayitem_float(self, arraydescr, arraybox, index, fieldnum):
        self.setarrayitem(arraydescr, arraybox, index, fieldnum, FLOAT)

    def setarrayitem(self, arraydescr, arraybox, index, fieldnum, kind):
        itembox = self.decode_box(fieldnum, kind)
        self.metainterp.execute_and_record(rop.SETARRAYITEM_GC,
                                           arraydescr, arraybox,
                                           ConstInt(index), itembox)

    def decode_int(self, tagged):
        return self.decode_box(tagged, INT)
    def decode_ref(self, tagged):
        return self.decode_box(tagged, REF)
    def decode_float(self, tagged):
        return self.decode_box(tagged, FLOAT)

    def decode_box(self, tagged, kind):
        num, tag = untag(tagged)
        if tag == TAGCONST:
            if tagged_eq(tagged, NULLREF):
                box = self.cpu.ts.CONST_NULL
            else:
                box = self.consts[num]
        elif tag == TAGVIRTUAL:
            box = self.getvirtual(num)
        elif tag == TAGINT:
            box = ConstInt(num)
        else:
            assert tag == TAGBOX
            box = self.liveboxes[num]
            if box is None:
                box = self.load_box_from_cpu(num, kind)
        assert box.type == kind
        return box

    def load_box_from_cpu(self, num, kind):
        if num < 0:
            num += len(self.liveboxes)
            assert num >= 0
        if kind == INT:
            box = BoxInt(self.cpu.get_latest_value_int(num))
        elif kind == REF:
            box = BoxPtr(self.cpu.get_latest_value_ref(num))
        elif kind == FLOAT:
            box = BoxFloat(self.cpu.get_latest_value_float(num))
        else:
            assert 0, "bad kind: %d" % ord(kind)
        self.liveboxes[num] = box
        return box

    def decode_box_of_type(self, TYPE, tagged):
        kind = getkind(TYPE)
        if kind == 'int':     kind = INT
        elif kind == 'ref':   kind = REF
        elif kind == 'float': kind = FLOAT
        else: raise AssertionError(kind)
        return self.decode_box(tagged, kind)
    decode_box_of_type._annspecialcase_ = 'specialize:arg(1)'

    def write_an_int(self, index, box):
        self.boxes_i[index] = box
    def write_a_ref(self, index, box):
        self.boxes_r[index] = box
    def write_a_float(self, index, box):
        self.boxes_f[index] = box

# ---------- when resuming for blackholing, get direct values ----------

def blackhole_from_resumedata(blackholeinterpbuilder, jitdriver_sd, storage,
                              all_virtuals=None):
    # The initialization is stack-critical code: it must not be interrupted by
    # StackOverflow, otherwise the jit_virtual_refs are left in a dangling state.
    rstack._stack_criticalcode_start()
    try:
        resumereader = ResumeDataDirectReader(blackholeinterpbuilder.metainterp_sd,
                                              storage, all_virtuals)
        vinfo = jitdriver_sd.virtualizable_info
        ginfo = jitdriver_sd.greenfield_info
        vrefinfo = blackholeinterpbuilder.metainterp_sd.virtualref_info
        resumereader.consume_vref_and_vable(vrefinfo, vinfo, ginfo)
    finally:
        rstack._stack_criticalcode_stop()
    #
    # First get a chain of blackhole interpreters whose length is given
    # by the depth of rd_frame_info_list.  The first one we get must be
    # the bottom one, i.e. the last one in the chain, in order to make
    # the comment in BlackholeInterpreter.setposition() valid.
    nextbh = None
    frameinfo = storage.rd_frame_info_list
    while True:
        curbh = blackholeinterpbuilder.acquire_interp()
        curbh.nextblackholeinterp = nextbh
        nextbh = curbh
        frameinfo = frameinfo.prev
        if frameinfo is None:
            break
    firstbh = nextbh
    #
    # Now fill the blackhole interpreters with resume data.
    curbh = firstbh
    frameinfo = storage.rd_frame_info_list
    while True:
        curbh.setposition(frameinfo.jitcode, frameinfo.pc)
        resumereader.consume_one_section(curbh)
        curbh = curbh.nextblackholeinterp
        frameinfo = frameinfo.prev
        if frameinfo is None:
            break
    resumereader.done()
    return firstbh

def force_from_resumedata(metainterp_sd, storage, vinfo, ginfo):
    resumereader = ResumeDataDirectReader(metainterp_sd, storage)
    resumereader.handling_async_forcing()
    vrefinfo = metainterp_sd.virtualref_info
    resumereader.consume_vref_and_vable(vrefinfo, vinfo, ginfo)
    return resumereader.force_all_virtuals()

class ResumeDataDirectReader(AbstractResumeDataReader):
    unique_id = lambda: None
    virtual_default = lltype.nullptr(llmemory.GCREF.TO)
    resume_after_guard_not_forced = 0
    #             0: not a GUARD_NOT_FORCED
    #             1: in handle_async_forcing
    #             2: resuming from the GUARD_NOT_FORCED

    def __init__(self, metainterp_sd, storage, all_virtuals=None):
        self._init(metainterp_sd.cpu, storage)
        self.callinfocollection = metainterp_sd.callinfocollection
        if all_virtuals is None:        # common case
            self._prepare(storage)
        else:
            # special case for resuming after a GUARD_NOT_FORCED: we already
            # have the virtuals
            self.resume_after_guard_not_forced = 2
            self.virtuals_cache = all_virtuals
            # self.rd_virtuals can remain None, because virtuals_cache is
            # already filled

    def handling_async_forcing(self):
        self.resume_after_guard_not_forced = 1

    def consume_one_section(self, blackholeinterp):
        self.blackholeinterp = blackholeinterp
        info = blackholeinterp.get_current_position_info()
        self._prepare_next_section(info)

    def consume_virtualref_info(self, vrefinfo, numb, end):
        # we have to decode a list of references containing pairs
        # [..., virtual, vref, ...]  stopping at 'end'
        assert (end & 1) == 0
        for i in range(0, end, 2):
            virtual = self.decode_ref(numb.nums[i])
            vref = self.decode_ref(numb.nums[i+1])
            # For each pair, we store the virtual inside the vref.
            vrefinfo.continue_tracing(vref, virtual)

    def consume_vable_info(self, vinfo, numb):
        # we have to ignore the initial part of 'nums' (containing vrefs),
        # find the virtualizable from nums[-1], load all other values
        # from the CPU stack, and copy them into the virtualizable
        if vinfo is None:
            return len(numb.nums)
        index = len(numb.nums) - 1
        virtualizable = self.decode_ref(numb.nums[index])
        if self.resume_after_guard_not_forced == 1:
            # in the middle of handle_async_forcing()
            assert vinfo.gettoken(virtualizable)
            vinfo.settoken(virtualizable, vinfo.TOKEN_NONE)
        else:
            # just jumped away from assembler (case 4 in the comment in
            # virtualizable.py) into tracing (case 2); check that vable_token
            # is and stays 0.  Note the call to reset_vable_token() in
            # warmstate.py.
            assert not vinfo.gettoken(virtualizable)
        return vinfo.write_from_resume_data_partial(virtualizable, self, numb)

    def load_value_of_type(self, TYPE, tagged):
        from pypy.jit.metainterp.warmstate import specialize_value
        kind = getkind(TYPE)
        if kind == 'int':
            x = self.decode_int(tagged)
        elif kind == 'ref':
            x = self.decode_ref(tagged)
        elif kind == 'float':
            x = self.decode_float(tagged)
        else:
            raise AssertionError(kind)
        return specialize_value(TYPE, x)
    load_value_of_type._annspecialcase_ = 'specialize:arg(1)'

    def consume_vref_and_vable(self, vrefinfo, vinfo, ginfo):
        numb = self.cur_numb
        self.cur_numb = numb.prev
        if self.resume_after_guard_not_forced != 2:
            end_vref = self.consume_vable_info(vinfo, numb)
            if ginfo is not None: end_vref -= 1
            self.consume_virtualref_info(vrefinfo, numb, end_vref)

    def allocate_with_vtable(self, known_class):
        from pypy.jit.metainterp.executor import exec_new_with_vtable
        return exec_new_with_vtable(self.cpu, known_class)

    def allocate_struct(self, typedescr):
        return self.cpu.bh_new(typedescr)

    def allocate_array(self, arraydescr, length):
        return self.cpu.bh_new_array(arraydescr, length)

    def allocate_string(self, length):
        return self.cpu.bh_newstr(length)

    def string_setitem(self, str, index, charnum):
        char = self.decode_int(charnum)
        self.cpu.bh_strsetitem(str, index, char)

    def concat_strings(self, str1num, str2num):
        str1 = self.decode_ref(str1num)
        str2 = self.decode_ref(str2num)
        str1 = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), str1)
        str2 = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), str2)
        cic = self.callinfocollection
        funcptr = cic.funcptr_for_oopspec(EffectInfo.OS_STR_CONCAT)
        result = funcptr(str1, str2)
        return lltype.cast_opaque_ptr(llmemory.GCREF, result)

    def slice_string(self, strnum, startnum, lengthnum):
        str = self.decode_ref(strnum)
        start = self.decode_int(startnum)
        length = self.decode_int(lengthnum)
        str = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), str)
        cic = self.callinfocollection
        funcptr = cic.funcptr_for_oopspec(EffectInfo.OS_STR_SLICE)
        result = funcptr(str, start, start + length)
        return lltype.cast_opaque_ptr(llmemory.GCREF, result)

    def allocate_unicode(self, length):
        return self.cpu.bh_newunicode(length)

    def unicode_setitem(self, str, index, charnum):
        char = self.decode_int(charnum)
        self.cpu.bh_unicodesetitem(str, index, char)

    def concat_unicodes(self, str1num, str2num):
        str1 = self.decode_ref(str1num)
        str2 = self.decode_ref(str2num)
        str1 = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), str1)
        str2 = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), str2)
        cic = self.callinfocollection
        funcptr = cic.funcptr_for_oopspec(EffectInfo.OS_UNI_CONCAT)
        result = funcptr(str1, str2)
        return lltype.cast_opaque_ptr(llmemory.GCREF, result)

    def slice_unicode(self, strnum, startnum, lengthnum):
        str = self.decode_ref(strnum)
        start = self.decode_int(startnum)
        length = self.decode_int(lengthnum)
        str = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), str)
        cic = self.callinfocollection
        funcptr = cic.funcptr_for_oopspec(EffectInfo.OS_UNI_SLICE)
        result = funcptr(str, start, start + length)
        return lltype.cast_opaque_ptr(llmemory.GCREF, result)

    def setfield(self, descr, struct, fieldnum):
        if descr.is_pointer_field():
            newvalue = self.decode_ref(fieldnum)
            self.cpu.bh_setfield_gc_r(struct, descr, newvalue)
        elif descr.is_float_field():
            newvalue = self.decode_float(fieldnum)
            self.cpu.bh_setfield_gc_f(struct, descr, newvalue)
        else:
            newvalue = self.decode_int(fieldnum)
            self.cpu.bh_setfield_gc_i(struct, descr, newvalue)

    def setarrayitem_int(self, arraydescr, array, index, fieldnum):
        newvalue = self.decode_int(fieldnum)
        self.cpu.bh_setarrayitem_gc_i(arraydescr, array, index, newvalue)

    def setarrayitem_ref(self, arraydescr, array, index, fieldnum):
        newvalue = self.decode_ref(fieldnum)
        self.cpu.bh_setarrayitem_gc_r(arraydescr, array, index, newvalue)

    def setarrayitem_float(self, arraydescr, array, index, fieldnum):
        newvalue = self.decode_float(fieldnum)
        self.cpu.bh_setarrayitem_gc_f(arraydescr, array, index, newvalue)

    def decode_int(self, tagged):
        num, tag = untag(tagged)
        if tag == TAGCONST:
            return self.consts[num].getint()
        elif tag == TAGINT:
            return num
        else:
            assert tag == TAGBOX
            if num < 0:
                num += self.cpu.get_latest_value_count()
            return self.cpu.get_latest_value_int(num)

    def decode_ref(self, tagged):
        num, tag = untag(tagged)
        if tag == TAGCONST:
            if tagged_eq(tagged, NULLREF):
                return self.cpu.ts.NULLREF
            return self.consts[num].getref_base()
        elif tag == TAGVIRTUAL:
            return self.getvirtual(num)
        else:
            assert tag == TAGBOX
            if num < 0:
                num += self.cpu.get_latest_value_count()
            return self.cpu.get_latest_value_ref(num)

    def decode_float(self, tagged):
        num, tag = untag(tagged)
        if tag == TAGCONST:
            return self.consts[num].getfloatstorage()
        else:
            assert tag == TAGBOX
            if num < 0:
                num += self.cpu.get_latest_value_count()
            return self.cpu.get_latest_value_float(num)

    def write_an_int(self, index, int):
        self.blackholeinterp.setarg_i(index, int)

    def write_a_ref(self, index, ref):
        self.blackholeinterp.setarg_r(index, ref)

    def write_a_float(self, index, float):
        self.blackholeinterp.setarg_f(index, float)

# ____________________________________________________________

def dump_storage(storage, liveboxes):
    "For profiling only."
    from pypy.rlib.objectmodel import compute_unique_id
    debug_start("jit-resume")
    if have_debug_prints():
        debug_print('Log storage', compute_unique_id(storage))
        frameinfo = storage.rd_frame_info_list
        while frameinfo is not None:
            try:
                jitcodename = frameinfo.jitcode.name
            except AttributeError:
                jitcodename = str(compute_unique_id(frameinfo.jitcode))
            debug_print('\tjitcode/pc', jitcodename,
                        frameinfo.pc,
                        'at', compute_unique_id(frameinfo))
            frameinfo = frameinfo.prev
        numb = storage.rd_numb
        while numb:
            debug_print('\tnumb', str([untag(numb.nums[i])
                                       for i in range(len(numb.nums))]),
                        'at', compute_unique_id(numb))
            numb = numb.prev
        for const in storage.rd_consts:
            debug_print('\tconst', const.repr_rpython())
        for box in liveboxes:
            if box is None:
                debug_print('\tbox', 'None')
            else:
                debug_print('\tbox', box.repr_rpython())
        if storage.rd_virtuals is not None:
            for virtual in storage.rd_virtuals:
                if virtual is None:
                    debug_print('\t\t', 'None')
                else:
                    virtual.debug_prints()
    debug_stop("jit-resume")
