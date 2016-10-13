from __future__ import with_statement
import py
import sys
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.jit.metainterp.resume import ResumeDataVirtualAdder,\
     AbstractResumeDataReader, get_VirtualCache_class, ResumeDataBoxReader,\
     tag, TagOverflow, untag, tagged_eq, UNASSIGNED, TAGBOX, TAGVIRTUAL,\
     tagged_list_eq, AbstractVirtualInfo, TAGCONST, NULLREF,\
     ResumeDataDirectReader, TAGINT, REF, VirtualInfo, VStructInfo,\
     VArrayInfoNotClear, VStrPlainInfo, VStrConcatInfo, VStrSliceInfo,\
     VUniPlainInfo, VUniConcatInfo, VUniSliceInfo,\
     capture_resumedata, ResumeDataLoopMemo, UNASSIGNEDVIRTUAL, INT,\
     annlowlevel, PENDINGFIELDSP, TAG_CONST_OFFSET
from rpython.jit.metainterp.resumecode import unpack_numbering,\
     create_numbering, NULL_NUMBER
from rpython.jit.metainterp.opencoder import Trace, Snapshot, TopSnapshot

from rpython.jit.metainterp.optimizeopt import info
from rpython.jit.metainterp.history import ConstInt, Const, AbstractDescr
from rpython.jit.metainterp.history import ConstPtr, ConstFloat,\
     IntFrontendOp, RefFrontendOp
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.metainterp import executor
from rpython.jit.codewriter import heaptracker, longlong
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.rlib.debug import debug_start, debug_stop, debug_print,\
     have_debug_prints
from rpython.jit.metainterp.test.strategies import intconsts
from rpython.jit.metainterp import resumecode

from hypothesis import given, strategies

class Storage:
    rd_frame_info_list = None
    rd_numb = None
    rd_consts = []
    rd_virtuals = None
    rd_pendingfields = None
    rd_count = 0


class FakeOptimizer(object):
    metainterp_sd = None
    optheap = None

    def __init__(self, trace=None):
        self.trace = trace

    def get_box_replacement(self, op):
        while (op.get_forwarded() is not None and
               not isinstance(op.get_forwarded(), info.AbstractInfo)):
            op = op.get_forwarded()
        return op

    def getrawptrinfo(self, op, create=True):
        op = self.get_box_replacement(op)
        return op.get_forwarded()

    def getptrinfo(self, op, create=True):
        op = self.get_box_replacement(op)
        return op.get_forwarded()        


# ____________________________________________________________

def dump_storage(storage, liveboxes):
    "For profiling only."
    debug_start("jit-resume")
    return # XXX refactor if needed
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
        if storage.rd_pendingfields:
            debug_print('\tpending setfields')
            for i in range(len(storage.rd_pendingfields)):
                lldescr = storage.rd_pendingfields[i].lldescr
                num = storage.rd_pendingfields[i].num
                fieldnum = storage.rd_pendingfields[i].fieldnum
                itemindex = storage.rd_pendingfields[i].itemindex
                debug_print("\t\t", str(lldescr), str(untag(num)), str(untag(fieldnum)), itemindex)

    debug_stop("jit-resume")


def test_tag():
    assert tag(3, 1) == rffi.r_short(3<<2|1)
    assert tag(-3, 2) == rffi.r_short(-3<<2|2)
    assert tag((1<<13)-1, 3) == rffi.r_short(((1<<15)-1)|3)
    assert tag(-1<<13, 3) == rffi.r_short((-1<<15)|3)
    py.test.raises(AssertionError, tag, 3, 5)
    py.test.raises(TagOverflow, tag, 1<<13, 0)
    py.test.raises(TagOverflow, tag, (1<<13)+1, 0)
    py.test.raises(TagOverflow, tag, (-1<<13)-1, 0)
    py.test.raises(TagOverflow, tag, (-1<<13)-5, 0)

def test_untag():
    assert untag(tag(3, 1)) == (3, 1)
    assert untag(tag(-3, 2)) == (-3, 2)
    assert untag(tag((1<<13)-1, 3)) == ((1<<13)-1, 3)
    assert untag(tag(-1<<13, 3)) == (-1<<13, 3)

def test_tagged_eq():
    assert tagged_eq(UNASSIGNED, UNASSIGNED)
    assert not tagged_eq(tag(1, TAGBOX), UNASSIGNED)

def test_tagged_list_eq():
    assert tagged_list_eq([UNASSIGNED, tag(1, TAGBOX), tag(-2, TAGVIRTUAL)],
                          [UNASSIGNED, tag(1, TAGBOX), tag(-2, TAGVIRTUAL)])
    assert not tagged_list_eq([tag(1, TAGBOX)], [tag(-2, TAGBOX)])
    assert not tagged_list_eq([tag(1, TAGBOX), tag(-2, TAGBOX)], [tag(1, TAGBOX)])

def test_vinfo():
    v1 = AbstractVirtualInfo()
    v1.set_content([1, 2, 4])
    assert v1.equals([1, 2, 4])
    assert not v1.equals([1, 2, 6])

def test_reuse_vinfo():
    class FakeVInfo(object):
        def set_content(self, fieldnums):
            self.fieldnums = fieldnums
        def equals(self, fieldnums):
            return self.fieldnums == fieldnums
    class FakeVirtualValue(info.AbstractVirtualPtrInfo):
        def visitor_dispatch_virtual_type(self, *args):
            return FakeVInfo()
    modifier = ResumeDataVirtualAdder(None, None, None, None, None)
    v1 = FakeVirtualValue()
    vinfo1 = modifier.make_virtual_info(v1, [1, 2, 4])
    vinfo2 = modifier.make_virtual_info(v1, [1, 2, 4])
    assert vinfo1 is vinfo2
    vinfo3 = modifier.make_virtual_info(v1, [1, 2, 6])
    assert vinfo3 is not vinfo2
    vinfo4 = modifier.make_virtual_info(v1, [1, 2, 6])
    assert vinfo3 is vinfo4

def setvalue(op, val):
    if op.type == 'i':
        op.setint(val)
    elif op.type == 'r':
        op.setref_base(val)
    elif op.type == 'f':
        op.setfloatstorage(val)
    else:
        assert op.type == 'v'

class MyMetaInterp:
    _already_allocated_resume_virtuals = None
    callinfocollection = None

    def __init__(self, cpu=None):
        if cpu is None:
            cpu = LLtypeMixin.cpu
        self.cpu = cpu
        self.trace = []
        self.framestack = []

    def newframe(self, jitcode):
        frame = FakeFrame(jitcode, -1)
        self.framestack.append(frame)
        return frame    

    def execute_and_record(self, opnum, descr, *argboxes):
        resvalue = executor.execute(self.cpu, None, opnum, descr, *argboxes)
        if isinstance(resvalue, int):
            op = IntFrontendOp(0)
        else:
            op = RefFrontendOp(0)
        setvalue(op, resvalue)
        self.trace.append((opnum, list(argboxes), resvalue, descr))
        return op

    def execute_new_with_vtable(self, descr=None):
        return self.execute_and_record(rop.NEW_WITH_VTABLE, descr)

    def execute_new(self, typedescr):
        return self.execute_and_record(rop.NEW, typedescr)

    def execute_new_array(self, itemsizedescr, lengthbox):
        return self.execute_and_record(rop.NEW_ARRAY, itemsizedescr,
                                       lengthbox)

    def execute_setfield_gc(self, fielddescr, box, valuebox):
        self.execute_and_record(rop.SETFIELD_GC, fielddescr, box, valuebox)

    def execute_setarrayitem_gc(self, arraydescr, arraybox, indexbox, itembox):
        self.execute_and_record(rop.SETARRAYITEM_GC, arraydescr,
                                arraybox, indexbox, itembox)

    def execute_setinteriorfield_gc(self, descr, array, index, value):
        self.execute_and_record(rop.SETINTERIORFIELD_GC, descr,
                                array, index, value)

    def execute_raw_store(self, arraydescr, addrbox, offsetbox, valuebox):
        self.execute_and_record(rop.RAW_STORE, arraydescr,
                                addrbox, offsetbox, valuebox)

S = lltype.GcStruct('S')
gcref1 = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S))
gcref2 = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S))
gcrefnull = lltype.nullptr(llmemory.GCREF.TO)

class MyCPU:
    class ts:
        NULLREF = gcrefnull
        CONST_NULL = ConstPtr(gcrefnull)
    def __init__(self, values):
        self.values = values
    def get_int_value(self, deadframe, index):
        assert deadframe == "deadframe"
        return self.values[index]
    def get_ref_value(self, deadframe, index):
        assert deadframe == "deadframe"
        return self.values[index]
    def get_float_value(self, deadframe, index):
        assert deadframe == "deadframe"
        return self.values[index]

class MyBlackholeInterp:
    def __init__(self, ARGS):
        self.written_i = []
        self.written_r = []
        self.written_f = []
        self.ARGS = ARGS

    def get_current_position_info(self):
        class MyInfo:
            @staticmethod
            def enumerate_vars(callback_i, callback_r, callback_f, _, index):
                count_i = count_r = count_f = 0
                for ARG in self.ARGS:
                    if ARG == lltype.Signed:
                        index = callback_i(index, count_i); count_i += 1
                    elif ARG == llmemory.GCREF:
                        index = callback_r(index, count_r); count_r += 1
                    elif ARG == longlong.FLOATSTORAGE:
                        index = callback_f(index, count_f); count_f += 1
                    else:
                        assert 0
                return index
        return MyInfo()

    def setarg_i(self, index, value):
        assert index == len(self.written_i)
        self.written_i.append(value)

    def setarg_r(self, index, value):
        assert index == len(self.written_r)
        self.written_r.append(value)

    def setarg_f(self, index, value):
        assert index == len(self.written_f)
        self.written_f.append(value)

def _next_section(reader, *expected):
    bh = MyBlackholeInterp(map(lltype.typeOf, expected))
    reader.consume_one_section(bh)
    expected_i = [x for x in expected if lltype.typeOf(x) == lltype.Signed]
    expected_r = [x for x in expected if lltype.typeOf(x) == llmemory.GCREF]
    expected_f = [x for x in expected if lltype.typeOf(x) ==
                                                      longlong.FLOATSTORAGE]
    assert bh.written_i == expected_i
    assert bh.written_r == expected_r
    assert bh.written_f == expected_f


def Numbering(l):
    return create_numbering([len(l)] + l) # prefix index to the end of thing

def tagconst(i):
    return tag(i + TAG_CONST_OFFSET, TAGCONST)

def test_simple_read():
    #b1, b2, b3 = [BoxInt(), InputArgRef(), BoxInt()]
    c1, c2, c3 = [ConstInt(111), ConstInt(222), ConstInt(333)]
    storage = Storage()
    storage.rd_consts = [c1, c2, c3]
    numb = Numbering([tag(0, TAGBOX), tagconst(0),
                       NULLREF, tag(0, TAGBOX), tag(1, TAGBOX)] +
                       [tagconst(1), tagconst(2)] + 
                       [tag(0, TAGBOX), tag(1, TAGBOX), tag(2, TAGBOX)])
    storage.rd_numb = numb
    storage.rd_count = 3
    #
    cpu = MyCPU([42, gcref1, -66])
    metainterp = MyMetaInterp(cpu)
    reader = ResumeDataDirectReader(metainterp, storage, "deadframe")
    _next_section(reader, 42, 111, gcrefnull, 42, gcref1)
    _next_section(reader, 222, 333)
    _next_section(reader, 42, gcref1, -66)
    #
    reader = ResumeDataBoxReader(storage, "deadframe", metainterp)
    bi, br, bf = [None]*3, [None]*2, [None]*0
    info = MyBlackholeInterp([lltype.Signed, lltype.Signed,
                              llmemory.GCREF, lltype.Signed,
                              llmemory.GCREF]).get_current_position_info()
    reader.consume_boxes(info, bi, br, bf)
    b1s = reader.liveboxes[0]
    b2s = reader.liveboxes[1]
    assert_same(bi, [b1s, ConstInt(111), b1s])
    assert_same(br, [ConstPtr(gcrefnull), b2s])
    bi, br, bf = [None]*2, [None]*0, [None]*0
    info = MyBlackholeInterp([lltype.Signed,
                              lltype.Signed]).get_current_position_info()
    reader.consume_boxes(info, bi, br, bf)
    assert_same(bi, [ConstInt(222), ConstInt(333)])
    bi, br, bf = [None]*2, [None]*1, [None]*0
    info = MyBlackholeInterp([lltype.Signed, llmemory.GCREF,
                              lltype.Signed]).get_current_position_info()
    reader.consume_boxes(info, bi, br, bf)
    b3s = reader.liveboxes[2]
    assert_same(bi, [b1s, b3s])
    assert_same(br, [b2s])
    #

def assert_same(list1, list2):
    assert len(list1) == len(list2)
    for b1, b2 in zip(list1, list2):
        assert b1.same_box(b2)

def test_simple_read_tagged_ints():
    storage = Storage()
    storage.rd_consts = []
    numb = Numbering([tag(100, TAGINT)])
    storage.rd_numb = numb
    #
    cpu = MyCPU([])
    reader = ResumeDataDirectReader(MyMetaInterp(cpu), storage, "deadframe")
    _next_section(reader, 100)


def test_prepare_virtuals():
    class FakeVinfo(object):
        kind = REF
        def allocate(self, decoder, index):
            s = "allocated"
            decoder.virtuals_cache.set_ptr(index, s)
            return s
    class FakeStorage(object):
        rd_virtuals = [FakeVinfo(), None]
        rd_numb = Numbering([])
        rd_consts = []
        rd_pendingfields = None
        rd_count = 0
    class FakeMetainterp(object):
        _already_allocated_resume_virtuals = None
        cpu = None
    reader = ResumeDataDirectReader(MyMetaInterp(None), FakeStorage(),
                                    "deadframe")
    cache = reader.force_all_virtuals()
    assert cache.virtuals_ptr_cache == ["allocated", reader.virtual_ptr_default]

# ____________________________________________________________

class FakeResumeDataReader(AbstractResumeDataReader):
    VirtualCache = get_VirtualCache_class('Fake')
    
    def allocate_with_vtable(self, descr):
        return FakeBuiltObject(vtable=descr)
    def allocate_struct(self, typedescr):
        return FakeBuiltObject(typedescr=typedescr)
    def allocate_array(self, length, arraydescr, clear):
        assert not clear     # the only test uses VArrayInfoNotClear
        return FakeBuiltObject(arraydescr=arraydescr, items=[None]*length)
    def setfield(self, struct, fieldnum, descr):
        setattr(struct, descr, fieldnum)
    def setarrayitem_int(self, array, i, fieldnum, arraydescr):
        assert 0 <= i < len(array.items)
        assert arraydescr is array.arraydescr
        array.items[i] = fieldnum
    def allocate_string(self, length):
        return FakeBuiltObject(string=[None]*length)
    def string_setitem(self, string, i, fieldnum):
        value, tag = untag(fieldnum)
        assert tag == TAGINT
        assert 0 <= i < len(string.string)
        string.string[i] = value
    def concat_strings(self, left, right):
        return FakeBuiltObject(strconcat=[left, right])
    def slice_string(self, str, start, length):
        return FakeBuiltObject(strslice=[str, start, length])
    def allocate_unicode(self, length):
        return FakeBuiltObject(unistring=[None]*length)
    def unicode_setitem(self, unistring, i, fieldnum):
        value, tag = untag(fieldnum)
        assert tag == TAGINT
        assert 0 <= i < len(unistring.unistring)
        unistring.unistring[i] = value
    def concat_unicodes(self, left, right):
        return FakeBuiltObject(uniconcat=[left, right])
    def slice_unicode(self, str, start, length):
        return FakeBuiltObject(unislice=[str, start, length])

class FakeBuiltObject(object):
    def __init__(self, **kwds):
        self.__dict__ = kwds
    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.__dict__ == other.__dict__)
    def __repr__(self):
        return 'FakeBuiltObject(%s)' % (
            ', '.join(['%s=%r' % item for item in self.__dict__.items()]))

class FakeArrayDescr(object):
    def is_array_of_pointers(self): return False
    def is_array_of_floats(self): return False

def test_virtualinfo():
    info = VirtualInfo(123, ["fielddescr1"])
    info.fieldnums = [tag(456, TAGINT)]
    reader = FakeResumeDataReader()
    reader._prepare_virtuals([info])
    cache = reader.force_all_virtuals()
    assert cache.virtuals_ptr_cache == [
        FakeBuiltObject(vtable=123, fielddescr1=tag(456, TAGINT))]

def test_vstructinfo():
    info = VStructInfo(124, ["fielddescr1"])
    info.fieldnums = [tag(456, TAGINT)]
    reader = FakeResumeDataReader()
    reader._prepare_virtuals([info])
    cache = reader.force_all_virtuals()
    assert cache.virtuals_ptr_cache == [
        FakeBuiltObject(typedescr=124, fielddescr1=tag(456, TAGINT))]

def test_varrayinfo():
    arraydescr = FakeArrayDescr()
    info = VArrayInfoNotClear(arraydescr)
    info.fieldnums = [tag(456, TAGINT)]
    reader = FakeResumeDataReader()
    reader._prepare_virtuals([info])
    assert reader.force_all_virtuals().virtuals_ptr_cache == [
        FakeBuiltObject(arraydescr=arraydescr, items=[tag(456, TAGINT)])]

def test_vstrplaininfo():
    info = VStrPlainInfo()
    info.fieldnums = [tag(60, TAGINT)]
    reader = FakeResumeDataReader()
    reader._prepare_virtuals([info])
    assert reader.force_all_virtuals().virtuals_ptr_cache == [
        FakeBuiltObject(string=[60])]

def test_vstrconcatinfo():
    info = VStrConcatInfo()
    info.fieldnums = [tag(10, TAGBOX), tag(20, TAGBOX)]
    reader = FakeResumeDataReader()
    reader._prepare_virtuals([info])
    assert reader.force_all_virtuals().virtuals_ptr_cache == [
        FakeBuiltObject(strconcat=info.fieldnums)]

def test_vstrsliceinfo():
    info = VStrSliceInfo()
    info.fieldnums = [tag(10, TAGBOX), tag(20, TAGBOX), tag(30, TAGBOX)]
    reader = FakeResumeDataReader()
    reader._prepare_virtuals([info])
    assert reader.force_all_virtuals().virtuals_ptr_cache == [
        FakeBuiltObject(strslice=info.fieldnums)]

def test_vuniplaininfo():
    info = VUniPlainInfo()
    info.fieldnums = [tag(60, TAGINT)]
    reader = FakeResumeDataReader()
    reader._prepare_virtuals([info])
    assert reader.force_all_virtuals().virtuals_ptr_cache == [
        FakeBuiltObject(unistring=[60])]

def test_vuniconcatinfo():
    info = VUniConcatInfo()
    info.fieldnums = [tag(10, TAGBOX), tag(20, TAGBOX)]
    reader = FakeResumeDataReader()
    reader._prepare_virtuals([info])
    assert reader.force_all_virtuals().virtuals_ptr_cache == [
        FakeBuiltObject(uniconcat=info.fieldnums)]

def test_vunisliceinfo():
    info = VUniSliceInfo()
    info.fieldnums = [tag(10, TAGBOX), tag(20, TAGBOX), tag(30, TAGBOX)]
    reader = FakeResumeDataReader()
    reader._prepare_virtuals([info])
    assert reader.force_all_virtuals().virtuals_ptr_cache == [
        FakeBuiltObject(unislice=info.fieldnums)]

# ____________________________________________________________



class FakeFrame(object):
    parent_resume_position = -1

    def __init__(self, code, pc, *boxes):
        self.jitcode = code
        self.pc = pc
        self._env = list(boxes)

    def get_list_of_active_boxes(self, flag):
        return self._env

    def setup_resume_at_op(self, pc, exception_target, env):
        self.__init__(self.jitcode, pc, exception_target, *env)
    
    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    def __ne__(self, other):
        return self.__dict__ != other.__dict__
    def __repr__(self):
        return "<FF %s %s %s>" % (self.jitcode, self.pc, self._env)

class FakeJitCode(object):
    def __init__(self, name, index):
        self.name = name
        self.index = index

class FakeMetaInterpStaticData:
    cpu = LLtypeMixin.cpu
    all_descrs = []

    class options:
        failargs_limit = 100

def test_rebuild_from_resumedata():
    py.test.skip("XXX rewrite")
    b1, b2, b3 = [BoxInt(), InputArgRef(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    
    storage = Storage()
    fs = [FakeFrame("code0", 0, b1, c1, b2),
          FakeFrame("code1", 3, b3, c2, b1),
          FakeFrame("code2", 9, c3, b2)]
    capture_resumedata(fs, None, [], storage)
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(FakeOptimizer(), storage, storage, memo)
    liveboxes = modifier.finish()
    metainterp = MyMetaInterp()

    b1t, b2t, b3t = [BoxInt(), InputArgRef(), BoxInt()]
    newboxes = _resume_remap(liveboxes, [b1, b2, b3], b1t, b2t, b3t)

    result = rebuild_from_resumedata(metainterp, storage, False)
    assert result == (None, [])
    fs2 = [FakeFrame("code0", 0, b1t, c1, b2t),
           FakeFrame("code1", 3, b3t, c2, b1t),
           FakeFrame("code2", 9, c3, b2t)]
    assert metainterp.framestack == fs2

def test_rebuild_from_resumedata_with_virtualizable():
    py.test.skip("XXX rewrite")
    b1, b2, b3, b4 = [BoxInt(), InputArgRef(), BoxInt(), InputArgRef()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    
    storage = Storage()
    fs = [FakeFrame("code0", 0, b1, c1, b2),
          FakeFrame("code1", 3, b3, c2, b1),
          FakeFrame("code2", 9, c3, b2)]
    capture_resumedata(fs, [b4], [], storage)
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(FakeOptimizer({}), storage, memo)
    liveboxes = modifier.finish()
    metainterp = MyMetaInterp()

    b1t, b2t, b3t, b4t = [BoxInt(), InputArgRef(), BoxInt(), InputArgRef()]
    newboxes = _resume_remap(liveboxes, [b1, b2, b3, b4], b1t, b2t, b3t, b4t)

    result = rebuild_from_resumedata(metainterp, newboxes, storage,
                                     True)
    assert result == ([b4t], [])
    fs2 = [FakeFrame("code0", 0, b1t, c1, b2t),
           FakeFrame("code1", 3, b3t, c2, b1t),
           FakeFrame("code2", 9, c3, b2t)]
    assert metainterp.framestack == fs2

def test_rebuild_from_resumedata_two_guards():
    py.test.skip("XXX rewrite")
    b1, b2, b3, b4 = [BoxInt(), InputArgRef(), BoxInt(), BoxInt()]
    c1, c2, c3 = [ConstInt(1), ConstInt(2), ConstInt(3)]    
    storage = Storage()
    fs = [FakeFrame("code0", 0, b1, c1, b2),
          FakeFrame("code1", 3, b3, c2, b1),
          FakeFrame("code2", 9, c3, b2)]
    capture_resumedata(fs, None, [], storage)
    storage2 = Storage()
    fs = fs[:-1] + [FakeFrame("code2", 10, c3, b2, b4)]
    capture_resumedata(fs, None, [], storage2)
    
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(FakeOptimizer({}), storage, memo)
    liveboxes = modifier.finish()

    modifier = ResumeDataVirtualAdder(FakeOptimizer({}), storage2, memo)
    liveboxes2 = modifier.finish()

    metainterp = MyMetaInterp()

    b1t, b2t, b3t, b4t = [BoxInt(), InputArgRef(), BoxInt(), BoxInt()]
    newboxes = _resume_remap(liveboxes, [b1, b2, b3], b1t, b2t, b3t)

    result = rebuild_from_resumedata(metainterp, newboxes, storage,
                                     False)
    assert result == (None, [])
    fs2 = [FakeFrame("code0", 0, b1t, c1, b2t),
           FakeFrame("code1", 3, b3t, c2, b1t),
           FakeFrame("code2", 9, c3, b2t)]
    assert metainterp.framestack == fs2

    newboxes = _resume_remap(liveboxes2, [b1, b2, b3, b4], b1t, b2t, b3t, b4t)

    metainterp.framestack = []
    result = rebuild_from_resumedata(metainterp, newboxes, storage2,
                                     False)
    assert result == (None, [])
    fs2 = fs2[:-1] + [FakeFrame("code2", 10, c3, b2t, b4t)]
    assert metainterp.framestack == fs2


class FakeOptimizer_VirtualValue(object):
    class optimizer:
        class cpu:
            pass
fakeoptimizer = FakeOptimizer_VirtualValue()

def ConstAddr(addr, cpu):   # compatibility
    return ConstInt(heaptracker.adr2int(addr))

def virtual_value(keybox, value, next):
    vv = VirtualValue(fakeoptimizer, ConstAddr(LLtypeMixin.node_vtable_adr,
                                     LLtypeMixin.cpu), keybox)
    if not isinstance(next, OptValue):
        next = OptValue(next)
    vv.setfield(LLtypeMixin.valuedescr, OptValue(value))
    vv.setfield(LLtypeMixin.nextdescr, next)
    return vv

def test_rebuild_from_resumedata_two_guards_w_virtuals():
    py.test.skip("XXX rewrite")
    
    b1, b2, b3, b4, b5 = [BoxInt(), InputArgRef(), BoxInt(), BoxInt(), BoxInt()]
    c1, c2, c3, c4 = [ConstInt(1), ConstInt(2), ConstInt(3),
                      LLtypeMixin.nodebox.constbox()]
    storage = Storage()
    fs = [FakeFrame("code0", 0, b1, c1, b2),
          FakeFrame("code1", 3, b3, c2, b1),
          FakeFrame("code2", 9, c3, b2)]
    capture_resumedata(fs, None, [], storage)
    storage2 = Storage()
    fs = fs[:-1] + [FakeFrame("code2", 10, c3, b2, b4)]
    capture_resumedata(fs, None, [], storage2)
    
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    values = {b2: virtual_value(b2, b5, c4)}
    modifier = ResumeDataVirtualAdder(FakeOptimizer(values), storage, memo)
    liveboxes = modifier.finish()
    assert len(storage.rd_virtuals) == 1
    assert storage.rd_virtuals[0].fieldnums == [tag(-1, TAGBOX),
                                                tag(0, TAGCONST)]

    b6 = InputArgRef()
    v6 = virtual_value(b6, c2, None)
    v6.setfield(LLtypeMixin.nextdescr, v6)    
    values = {b2: virtual_value(b2, b4, v6), b6: v6}
    memo.clear_box_virtual_numbers()
    modifier = ResumeDataVirtualAdder(FakeOptimizer(values), storage2, memo)
    liveboxes2 = modifier.finish()
    assert len(storage2.rd_virtuals) == 2    
    assert storage2.rd_virtuals[0].fieldnums == [tag(len(liveboxes2)-1, TAGBOX),
                                                 tag(-1, TAGVIRTUAL)]
    assert storage2.rd_virtuals[1].fieldnums == [tag(2, TAGINT),
                                                 tag(-1, TAGVIRTUAL)]

    # now on to resuming
    metainterp = MyMetaInterp()

    b1t, b3t, b4t, b5t = [BoxInt(), BoxInt(), BoxInt(), BoxInt()]
    newboxes = _resume_remap(liveboxes, [b1, b3, b5], b1t, b3t, b5t)

    result = rebuild_from_resumedata(metainterp, newboxes, storage,
                                     False)

    b2t = metainterp.resboxes[0]
    fs2 = [FakeFrame("code0", 0, b1t, c1, b2t),
           FakeFrame("code1", 3, b3t, c2, b1t),
           FakeFrame("code2", 9, c3, b2t)]
    assert metainterp.framestack == fs2

    newboxes = _resume_remap(liveboxes2, [b1, b3, b4], b1t, b3t, b4t)

    metainterp = MyMetaInterp()
    result = rebuild_from_resumedata(metainterp, newboxes, storage2,
                                     False)
    b2t = metainterp.resboxes[0]
    assert len(metainterp.resboxes) == 2
    fs2 = [FakeFrame("code0", 0, b1t, c1, b2t),
           FakeFrame("code1", 3, b3t, c2, b1t),
           FakeFrame("code2", 10, c3, b2t, b4t)]
    assert metainterp.framestack == fs2    

def test_rebuild_from_resumedata_two_guards_w_shared_virtuals():
    py.test.skip("XXX rewrite")
    b1, b2, b3, b4, b5, b6 = [InputArgRef(), InputArgRef(), BoxInt(), InputArgRef(), BoxInt(), BoxInt()]
    c1, c2, c3, c4 = [ConstInt(1), ConstInt(2), ConstInt(3),
                      LLtypeMixin.nodebox.constbox()]
    storage = Storage()
    fs = [FakeFrame("code0", 0, c1, b2, b3)]
    capture_resumedata(fs, None, [], storage)
    
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    values = {b2: virtual_value(b2, b5, c4)}
    modifier = ResumeDataVirtualAdder(FakeOptimizer(values), storage, memo)
    liveboxes = modifier.finish()
    assert len(storage.rd_virtuals) == 1
    assert storage.rd_virtuals[0].fieldnums == [tag(-1, TAGBOX),
                                                tag(0, TAGCONST)]

    storage2 = Storage()
    fs = [FakeFrame("code0", 0, b1, b4, b2)]
    capture_resumedata(fs, None, [], storage2)
    values[b4] = virtual_value(b4, b6, c4)
    modifier = ResumeDataVirtualAdder(FakeOptimizer(values), storage2, memo)
    liveboxes = modifier.finish()
    assert len(storage2.rd_virtuals) == 2
    assert storage2.rd_virtuals[1].fieldnums == storage.rd_virtuals[0].fieldnums
    assert storage2.rd_virtuals[1] is storage.rd_virtuals[0]
    

def test_resumedata_top_recursive_virtuals():
    py.test.skip("XXX rewrite")
    b1, b2, b3 = [InputArgRef(), InputArgRef(), BoxInt()]
    storage = Storage()
    fs = [FakeFrame("code0", 0, b1, b2)]
    capture_resumedata(fs, None, [], storage)
    
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    v1 = virtual_value(b1, b3, None)
    v2 = virtual_value(b2, b3, v1)
    v1.setfield(LLtypeMixin.nextdescr, v2)
    values = {b1: v1, b2: v2}
    modifier = ResumeDataVirtualAdder(FakeOptimizer(values), storage, memo)
    liveboxes = modifier.finish()
    assert liveboxes == [b3]
    assert len(storage.rd_virtuals) == 2
    assert storage.rd_virtuals[0].fieldnums == [tag(-1, TAGBOX),
                                                tag(1, TAGVIRTUAL)]
    assert storage.rd_virtuals[1].fieldnums == [tag(-1, TAGBOX),
                                                tag(0, TAGVIRTUAL)]    


# ____________________________________________________________


def test_ResumeDataLoopMemo_ints():
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    tagged = memo.getconst(ConstInt(44))
    assert untag(tagged) == (44, TAGINT)
    tagged = memo.getconst(ConstInt(-3))
    assert untag(tagged) == (-3, TAGINT)
    const = ConstInt(50000)
    tagged = memo.getconst(const)
    index, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert memo.consts[index - TAG_CONST_OFFSET] is const
    tagged = memo.getconst(ConstInt(50000))
    index2, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert index2 == index

demo55 = lltype.malloc(LLtypeMixin.NODE)
demo55o = lltype.cast_opaque_ptr(llmemory.GCREF, demo55)
demo66 = lltype.malloc(LLtypeMixin.NODE)
demo66o = lltype.cast_opaque_ptr(llmemory.GCREF, demo66)
    
def test_ResumeDataLoopMemo_refs():
    cpu = LLtypeMixin.cpu
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    const = cpu.ts.ConstRef(demo55o)
    tagged = memo.getconst(const)
    index, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert memo.consts[index - TAG_CONST_OFFSET] is const    
    tagged = memo.getconst(cpu.ts.ConstRef(demo55o))
    index2, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert index2 == index
    tagged = memo.getconst(cpu.ts.ConstRef(demo66o))
    index3, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert index3 != index    
    tagged = memo.getconst(cpu.ts.CONST_NULL)
    assert tagged == NULLREF

def test_ResumeDataLoopMemo_other():
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    const = ConstFloat(longlong.getfloatstorage(-1.0))
    tagged = memo.getconst(const)
    index, tagbits = untag(tagged)
    assert tagbits == TAGCONST
    assert memo.consts[index - TAG_CONST_OFFSET] is const

class Frame(object):
    def __init__(self, boxes):
        self.boxes = boxes

    def get_list_of_active_boxes(self, flag, new_array, encode):
        a = new_array(len(self.boxes))
        for i, box in enumerate(self.boxes):
            a[i] = encode(box)
        return a

def test_ResumeDataLoopMemo_number():
    b1, b2, b3, b4, b5 = [IntFrontendOp(0), IntFrontendOp(1), IntFrontendOp(2),
                          RefFrontendOp(3), RefFrontendOp(4)]
    c1, c2, c3, c4 = [ConstInt(1), ConstInt(2), ConstInt(3), ConstInt(4)]    

    env = [b1, c1, b2, b1, c2]
    metainterp_sd = FakeMetaInterpStaticData()
    t = Trace([b1, b2, b3, b4, b5], metainterp_sd)
    snap = t.create_snapshot(FakeJitCode("jitcode", 0), 0, Frame(env), False)
    env1 = [c3, b3, b1, c1]
    t.append(0) # descr index
    snap1 = t.create_top_snapshot(FakeJitCode("jitcode", 0), 2, Frame(env1), False,
        [], [])
    snap1.prev = snap

    env2 = [c3, b3, b1, c3]
    env3 = [c3, b3, b1, c3]
    env4 = [c3, b4, b1, c3]
    env5 = [b1, b4, b5]

    memo = ResumeDataLoopMemo(metainterp_sd)

    iter = t.get_iter()
    b1, b2, b3, b4, b5 = iter.inputargs
    numb_state = memo.number(FakeOptimizer(), 0, iter)
    numb = numb_state.create_numbering()
    assert numb_state.num_virtuals == 0

    assert numb_state.liveboxes == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX),
                                    b3: tag(2, TAGBOX)}
    base = [0, 0, tag(0, TAGBOX), tag(1, TAGINT),
            tag(1, TAGBOX), tag(0, TAGBOX), tag(2, TAGINT)]

    assert unpack_numbering(numb) == [16, 0, 0] + base + [0, 2, tag(3, TAGINT), tag(2, TAGBOX),
                                      tag(0, TAGBOX), tag(1, TAGINT)]
    t.append(0)
    snap2 = t.create_top_snapshot(FakeJitCode("jitcode", 0), 2, Frame(env2),
                                  False, [], [])
    snap2.prev = snap

    numb_state2 = memo.number(FakeOptimizer(), 1, iter)
    numb2 = numb_state2.create_numbering()
    assert numb_state2.num_virtuals == 0

    assert numb_state2.liveboxes == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX),
                                     b3: tag(2, TAGBOX)}
    assert numb_state2.liveboxes is not numb_state.liveboxes
    assert unpack_numbering(numb2) == [16, 0, 0] + base + [0, 2, tag(3, TAGINT), tag(2, TAGBOX),
                                       tag(0, TAGBOX), tag(3, TAGINT)]

    t.append(0)
    snap3 = t.create_top_snapshot(FakeJitCode("jitcode", 0), 2, Frame([]),
                                  False, [], env3)
    snap3.prev = snap

    class FakeVirtualInfo(info.AbstractInfo):
        def __init__(self, virt):
            self.virt = virt

        def is_virtual(self):
            return self.virt

    # renamed
    b3.set_forwarded(c4)
    numb_state3 = memo.number(FakeOptimizer(), 2, iter)
    numb3 = numb_state3.create_numbering()
    assert numb_state3.num_virtuals == 0
    
    assert numb_state3.liveboxes == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX)}
    assert unpack_numbering(numb3) == ([16, 0, 2, tag(3, TAGINT), tag(4, TAGINT),
                                       tag(0, TAGBOX), tag(3, TAGINT)] +
                                       base + [0, 2])

    # virtual
    t.append(0)
    snap4 = t.create_top_snapshot(FakeJitCode("jitcode", 0), 2, Frame([]),
                                  False, [], env4)
    snap4.prev = snap

    b4.set_forwarded(FakeVirtualInfo(True))
    numb_state4 = memo.number(FakeOptimizer(), 3, iter)
    numb4 = numb_state4.create_numbering()
    assert numb_state4.num_virtuals == 1
    
    assert numb_state4.liveboxes == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX),
                                     b4: tag(0, TAGVIRTUAL)}
    assert unpack_numbering(numb4) == [16, 0, 2, tag(3, TAGINT), tag(0, TAGVIRTUAL),
                                       tag(0, TAGBOX), tag(3, TAGINT)] + base + [0, 2]

    t.append(0)
    snap4 = t.create_snapshot(FakeJitCode("jitcode", 2), 1, Frame(env4), False)
    t.append(0)
    snap4.prev = snap
    snap5 = t.create_top_snapshot(FakeJitCode("jitcode", 0), 0, Frame([]), False,
                                  env5, [])
    snap5.prev = snap4

    b4.set_forwarded(FakeVirtualInfo(True))
    b5.set_forwarded(FakeVirtualInfo(True))
    numb_state5 = memo.number(FakeOptimizer(), 4, iter)
    numb5 = numb_state5.create_numbering()
    assert numb_state5.num_virtuals == 2

    assert numb_state5.liveboxes == {b1: tag(0, TAGBOX), b2: tag(1, TAGBOX),
                                     b4: tag(0, TAGVIRTUAL), b5: tag(1, TAGVIRTUAL)}
    assert unpack_numbering(numb5) == [21,
        3, tag(0, TAGBOX), tag(0, TAGVIRTUAL), tag(1, TAGVIRTUAL),
        0] + base + [
        2, 1, tag(3, TAGINT), tag(0, TAGVIRTUAL), tag(0, TAGBOX), tag(3, TAGINT)
        ] + [0, 0]

@given(strategies.lists(strategies.builds(IntFrontendOp, strategies.just(0)) | intconsts,
       min_size=1))
def test_ResumeDataLoopMemo_random(lst):
    inpargs = [box for box in lst if not isinstance(box, Const)]
    metainterp_sd = FakeMetaInterpStaticData()
    t = Trace(inpargs, metainterp_sd)
    t.append(0)
    i = t.get_iter()
    t.create_top_snapshot(FakeJitCode("", 0), 0, Frame(lst), False, [], [])
    memo = ResumeDataLoopMemo(metainterp_sd)
    numb_state = memo.number(FakeOptimizer(), 0, i)
    numb = numb_state.create_numbering()
    l = unpack_numbering(numb)
    assert l[0] == len(l)
    assert l[1] == 0
    assert l[2] == 0
    assert l[3] == 0
    assert l[4] == 0
    mapping = dict(zip(inpargs, i.inputargs))
    for i, item in enumerate(lst):
        v, tag = untag(l[i + 5])
        if tag == TAGBOX:
            assert l[i + 5] == numb_state.liveboxes[mapping[item]]
        elif tag == TAGCONST:
            assert memo.consts[v].getint() == item.getint()
        elif tag == TAGINT:
            assert v == item.getint()
    
def test_ResumeDataLoopMemo_number_boxes():
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    b1, b2 = [IntFrontendOp(0), IntFrontendOp(0)]
    assert memo.num_cached_boxes() == 0
    boxes = []
    num = memo.assign_number_to_box(b1, boxes)
    assert num == -1
    assert boxes == [b1]
    assert memo.num_cached_boxes() == 1
    boxes = [None]
    num = memo.assign_number_to_box(b1, boxes)
    assert num == -1
    assert boxes == [b1]
    num = memo.assign_number_to_box(b2, boxes)
    assert num == -2
    assert boxes == [b1, b2]

    assert memo.num_cached_boxes() == 2
    boxes = [None, None]
    num = memo.assign_number_to_box(b2, boxes)
    assert num == -2
    assert boxes == [None, b2]
    num = memo.assign_number_to_box(b1, boxes)
    assert num == -1
    assert boxes == [b1, b2]

    memo.clear_box_virtual_numbers()
    assert memo.num_cached_boxes() == 0

def test_ResumeDataLoopMemo_number_virtuals():
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    b1, b2 = [IntFrontendOp(0), IntFrontendOp(0)]
    assert memo.num_cached_virtuals() == 0
    num = memo.assign_number_to_virtual(b1)
    assert num == -1
    assert memo.num_cached_virtuals() == 1
    num = memo.assign_number_to_virtual(b1)
    assert num == -1
    num = memo.assign_number_to_virtual(b2)
    assert num == -2

    assert memo.num_cached_virtuals() == 2
    num = memo.assign_number_to_virtual(b2)
    assert num == -2
    num = memo.assign_number_to_virtual(b1)
    assert num == -1

    memo.clear_box_virtual_numbers()
    assert memo.num_cached_virtuals() == 0

def test_register_virtual_fields():
    b1, b2 = IntFrontendOp(0), IntFrontendOp(1)
    vbox = RefFrontendOp(2)
    modifier = ResumeDataVirtualAdder(FakeOptimizer(), None, None, None, None)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}
    modifier.register_virtual_fields(vbox, [b1, b2])
    assert modifier.liveboxes == {vbox: UNASSIGNEDVIRTUAL, b1: UNASSIGNED,
                                  b2: UNASSIGNED}
    assert modifier.vfieldboxes == {vbox: [b1, b2]}

    modifier = ResumeDataVirtualAdder(FakeOptimizer(), None, None, None, None)
    modifier.liveboxes_from_env = {vbox: tag(0, TAGVIRTUAL)}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}
    modifier.register_virtual_fields(vbox, [b1, b2, vbox])
    assert modifier.liveboxes == {b1: UNASSIGNED, b2: UNASSIGNED,
                                  vbox: tag(0, TAGVIRTUAL)}
    assert modifier.vfieldboxes == {vbox: [b1, b2, vbox]}

def _resume_remap(liveboxes, expected, *newvalues):
    newboxes = []
    for box in liveboxes:
        i = expected.index(box)
        newboxes.append(newvalues[i])
    assert len(newboxes) == len(expected)
    return newboxes

def make_storage(b1, b2, b3):
    t = Trace([box for box in [b1, b2, b3] if not isinstance(box, Const)],
              FakeMetaInterpStaticData())
    t.append(0)
    storage = Storage()
    snap1 = t.create_snapshot(FakeJitCode("code3", 41), 42,
                              Frame([b1, ConstInt(1), b1, b2]), False)
    snap2 = t.create_snapshot(FakeJitCode("code2", 31), 32,
                              Frame([ConstInt(2), ConstInt(3)]), False)
    snap3 = t.create_top_snapshot(FakeJitCode("code1", 21), 22,
                                  Frame([b1, b2, b3]), False, [], [])
    snap3.prev = snap2
    snap2.prev = snap1
    storage.rd_resume_position = 0
    return storage, t

def test_virtual_adder_int_constants():
    b1s, b2s, b3s = [ConstInt(sys.maxint), ConstInt(2**16), ConstInt(-65)]
    storage, t = make_storage(b1s, b2s, b3s)
    metainterp_sd = FakeMetaInterpStaticData()
    memo = ResumeDataLoopMemo(metainterp_sd)  
    i = t.get_iter()
    modifier = ResumeDataVirtualAdder(FakeOptimizer(i), storage, storage, i, memo)
    liveboxes = modifier.finish()
    cpu = MyCPU([])
    reader = ResumeDataDirectReader(MyMetaInterp(cpu), storage, "deadframe")
    reader.consume_vref_and_vable(None, None, None)
    reader.cur_index += 2 # framestack
    _next_section(reader, sys.maxint, 1, sys.maxint, 2**16)
    reader.cur_index += 2 # framestack
    _next_section(reader, 2, 3)
    reader.cur_index += 2 # framestack
    _next_section(reader, sys.maxint, 2**16, -65)

def test_virtual_adder_memo_const_sharing():
    b1s, b2s, b3s = [ConstInt(sys.maxint), ConstInt(2**16), ConstInt(-65)]
    storage, t = make_storage(b1s, b2s, b3s)
    metainterp_sd = FakeMetaInterpStaticData()
    memo = ResumeDataLoopMemo(metainterp_sd)
    i = t.get_iter()
    modifier = ResumeDataVirtualAdder(FakeOptimizer(i), storage, storage, i, memo)
    modifier.finish()
    assert len(memo.consts) == 2
    assert storage.rd_consts is memo.consts

    b1s, b2s, b3s = [ConstInt(sys.maxint), ConstInt(2**17), ConstInt(-65)]
    storage2, t = make_storage(b1s, b2s, b3s)
    i = t.get_iter()
    modifier2 = ResumeDataVirtualAdder(FakeOptimizer(i), storage2, storage2,
                                       i, memo)
    modifier2.finish()
    assert len(memo.consts) == 3    
    assert storage2.rd_consts is memo.consts


class ResumeDataFakeReader(ResumeDataBoxReader):
    """Another subclass of AbstractResumeDataReader meant for tests."""
    def __init__(self, storage, newboxes, metainterp):
        self._init(metainterp.cpu, storage)
        self.liveboxes = newboxes
        self.metainterp = metainterp
        self._prepare(storage)

    def consume_boxes(self):
        self.lst = []
        class Whatever:
            def __eq__(self, other):
                return True
        class MyInfo:
            @staticmethod
            def enumerate_vars(callback_i, callback_r, callback_f, _, index):
                while index < max_index:
                    tagged, _ = resumecode.numb_next_item(self.numb, index)
                    _, tag = untag(tagged)
                    if tag == TAGVIRTUAL:
                        kind = REF
                    else:
                        kind = Whatever()
                    box = self.decode_box(tagged, kind)
                    if box.type == INT:
                        index = callback_i(index, index)
                    elif box.type == REF:
                        index = callback_r(index, index)
                    elif box.type == FLOAT:
                        index = callback_f(index, index)
                    else:
                        assert 0

        size_section, self.cur_index = resumecode.numb_next_item(self.numb, 0)
        max_index = resumecode.numb_next_n_items(self.numb, size_section, 0)
        size, self.cur_index = resumecode.numb_next_item(self.numb, self.cur_index)
        assert size == 0
        size, self.cur_index = resumecode.numb_next_item(self.numb, self.cur_index)
        assert size == 0
        pc, self.cur_index = resumecode.numb_next_item(self.numb, self.cur_index)
        jitcode_pos, self.cur_index = resumecode.numb_next_item(self.numb, self.cur_index)

        self._prepare_next_section(MyInfo())
        return self.lst

    def write_an_int(self, count_i, box):
        assert box.type == INT
        self.lst.append(box)
    def write_a_ref(self, count_r, box):
        assert box.type == REF
        self.lst.append(box)
    def write_a_float(self, count_f, box):
        assert box.type == FLOAT
        self.lst.append(box)


def test_virtual_adder_no_op_renaming():
    py.test.skip("rewrite fake reader")
    b1s, b2s, b3s = [InputArgInt(1), InputArgInt(2), InputArgInt(3)]
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    b1_2 = InputArgInt()
    modifier = ResumeDataVirtualAdder(FakeOptimizer(), storage, storage, memo)

    b1s.set_forwarded(b1_2)
    b2s.set_forwarded(b1_2)
    liveboxes = modifier.finish()
    assert storage.rd_snapshot is None
    b1t, b3t = [InputArgInt(11), InputArgInt(33)]
    newboxes = _resume_remap(liveboxes, [b1_2, b3s], b1t, b3t)
    metainterp = MyMetaInterp()
    reader = ResumeDataFakeReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    assert_same(lst, [b1t, b1t, b3t])
    lst = reader.consume_boxes()
    assert_same(lst, [ConstInt(2), ConstInt(3)])
    lst = reader.consume_boxes()
    assert_same(lst, [b1t, ConstInt(1), b1t, b1t])
    assert metainterp.trace == []    


def test_virtual_adder_make_constant():
    py.test.skip("rewrite fake reader")
    b1s, b2s, b3s = [InputArgInt(1), InputArgRef(), InputArgInt(3)]
    b1s = ConstInt(111)
    storage = make_storage(b1s, b2s, b3s)
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())        
    modifier = ResumeDataVirtualAdder(FakeOptimizer(), storage, storage, memo)
    liveboxes = modifier.finish()
    b2t, b3t = [InputArgRef(demo55o), InputArgInt(33)]
    newboxes = _resume_remap(liveboxes, [b2s, b3s], b2t, b3t)
    metainterp = MyMetaInterp()
    reader = ResumeDataFakeReader(storage, newboxes, metainterp)
    lst = reader.consume_boxes()
    c1t = ConstInt(111)
    assert_same(lst, [c1t, b2t, b3t])
    lst = reader.consume_boxes()
    assert_same(lst, [ConstInt(2), ConstInt(3)])
    lst = reader.consume_boxes()
    assert_same(lst, [c1t, ConstInt(1), c1t, b2t])
    assert metainterp.trace == []


def test_virtual_adder_make_virtual():
    b2s, b3s, b4s, b5s = [IntFrontendOp(0), IntFrontendOp(0), RefFrontendOp(0),
                          RefFrontendOp(0)]  
    c1s = ConstInt(111)
    storage = Storage()
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(FakeOptimizer(), storage, storage, None, memo)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}

    vdescr = LLtypeMixin.nodesize2
    ca = ConstAddr(LLtypeMixin.node_vtable_adr2, LLtypeMixin.cpu)
    v4 = info.InstancePtrInfo(vdescr, ca, True)
    b4s.set_forwarded(v4)
    v4.setfield(LLtypeMixin.nextdescr, ca, b2s)
    v4.setfield(LLtypeMixin.valuedescr, ca, b3s)
    v4.setfield(LLtypeMixin.otherdescr, ca, b5s)
    ca = ConstAddr(LLtypeMixin.node_vtable_adr, LLtypeMixin.cpu)
    v2 = info.InstancePtrInfo(LLtypeMixin.nodesize, ca, True)
    v2.setfield(LLtypeMixin.nextdescr, b4s, ca)
    v2.setfield(LLtypeMixin.valuedescr, c1s, ca)
    b2s.set_forwarded(v2)

    modifier.register_virtual_fields(b2s, [c1s, None, None, None, b4s])
    modifier.register_virtual_fields(b4s, [b3s, None, None, None, b2s, b5s])

    liveboxes = []
    modifier._number_virtuals(liveboxes, FakeOptimizer(), 0)
    storage.rd_consts = memo.consts[:]
    storage.rd_numb = Numbering([])
    # resume
    b3t, b5t = [IntFrontendOp(0), RefFrontendOp(0)]
    b5t.setref_base(demo55o)
    b3t.setint(33)
    newboxes = _resume_remap(liveboxes, [#b2s -- virtual
                                         b3s,
                                         #b4s -- virtual
                                         #b2s -- again, shared
                                         #b3s -- again, shared
                                         b5s], b3t, b5t)

    metainterp = MyMetaInterp()
    reader = ResumeDataFakeReader(storage, newboxes, metainterp)
    assert len(reader.virtuals_cache.virtuals_ptr_cache) == 2
    b2t = reader.decode_ref(modifier._gettagged(b2s))
    b4t = reader.decode_ref(modifier._gettagged(b4s))
    trace = metainterp.trace
    b2new = (rop.NEW_WITH_VTABLE, [], b2t.getref_base(), LLtypeMixin.nodesize)
    b4new = (rop.NEW_WITH_VTABLE, [], b4t.getref_base(), LLtypeMixin.nodesize2)
    b2set = [(rop.SETFIELD_GC, [b2t, b4t],      None, LLtypeMixin.nextdescr),
             (rop.SETFIELD_GC, [b2t, c1s],      None, LLtypeMixin.valuedescr)]
    b4set = [(rop.SETFIELD_GC, [b4t, b2t],     None, LLtypeMixin.nextdescr),
             (rop.SETFIELD_GC, [b4t, b3t],     None, LLtypeMixin.valuedescr),
             (rop.SETFIELD_GC, [b4t, b5t],     None, LLtypeMixin.otherdescr)]
    expected = [b2new, b4new] + b4set + b2set

    # check that we get the operations in 'expected', in a possibly different
    # order.
    assert len(trace) == len(expected)
    orig = trace[:]
    with CompareableConsts():
        for x in trace:
            assert x in expected
            expected.remove(x)

    ptr = b2t.getref_base()._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(LLtypeMixin.NODE)
    assert ptr.value == 111
    ptr2 = ptr.next
    ptr2 = lltype.cast_pointer(lltype.Ptr(LLtypeMixin.NODE2), ptr2)
    assert ptr2.other == demo55
    assert ptr2.parent.value == 33
    assert ptr2.parent.next == ptr

class CompareableConsts(object):
    def __enter__(self):
        Const.__eq__ = Const.same_box

    def __exit__(self, type, value, traceback):
        del Const.__eq__

def test_virtual_adder_make_varray():
    b2s, b4s = [IntFrontendOp(0), IntFrontendOp(0)]
    b4s.setint(4)
    c1s = ConstInt(111)
    storage = Storage()
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(FakeOptimizer(), storage, storage, None, memo)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}

    v2 = info.ArrayPtrInfo(LLtypeMixin.arraydescr, size=2, is_virtual=True)
    b2s.set_forwarded(v2)
    v2._items = [b4s, c1s]
    modifier.register_virtual_fields(b2s, [b4s, c1s])
    liveboxes = []
    modifier._number_virtuals(liveboxes, FakeOptimizer(), 0)
    dump_storage(storage, liveboxes)
    storage.rd_consts = memo.consts[:]
    storage.rd_numb = Numbering([])
    # resume
    b1t, b3t, b4t = [IntFrontendOp(0), IntFrontendOp(0), IntFrontendOp(0)]
    b1t.setint(11)
    b3t.setint(33)
    b4t.setint(44)
    newboxes = _resume_remap(liveboxes, [#b2s -- virtual
                                         b4s],
                                         b4t)
    # resume
    metainterp = MyMetaInterp()
    reader = ResumeDataFakeReader(storage, newboxes, metainterp)
    assert len(reader.virtuals_cache.virtuals_ptr_cache) == 1
    b2t = reader.decode_ref(tag(0, TAGVIRTUAL))
    trace = metainterp.trace
    expected = [
        (rop.NEW_ARRAY, [ConstInt(2)], b2t.getref_base(),
         LLtypeMixin.arraydescr),
        (rop.SETARRAYITEM_GC, [b2t,ConstInt(0), b4t],None,
                              LLtypeMixin.arraydescr),
        (rop.SETARRAYITEM_GC, [b2t,ConstInt(1), c1s], None,
                              LLtypeMixin.arraydescr),
        ]
    with CompareableConsts():
        for x, y in zip(expected, trace):
            assert x == y
    #
    ptr = b2t.getref_base()._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(lltype.GcArray(lltype.Signed))
    assert len(ptr) == 2
    assert ptr[0] == 44
    assert ptr[1] == 111


def test_virtual_adder_make_vstruct():
    b2s, b4s = [RefFrontendOp(0), RefFrontendOp(0)]
    c1s = ConstInt(111)
    storage = Storage()
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(FakeOptimizer(), storage, storage, None, memo)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}
    v2 = info.StructPtrInfo(LLtypeMixin.ssize, is_virtual=True)
    b2s.set_forwarded(v2)
    v2.setfield(LLtypeMixin.adescr, b2s, c1s)
    v2.setfield(LLtypeMixin.abisdescr, b2s, c1s)
    v2.setfield(LLtypeMixin.bdescr, b2s, b4s)
    modifier.register_virtual_fields(b2s, [c1s, c1s, b4s])
    liveboxes = []
    modifier._number_virtuals(liveboxes, FakeOptimizer(), 0)
    dump_storage(storage, liveboxes)
    storage.rd_consts = memo.consts[:]
    storage.rd_numb = Numbering([])
    b4t = RefFrontendOp(0)
    newboxes = _resume_remap(liveboxes, [#b2s -- virtual
                                         b4s], b4t)
    #
    NULL = ConstPtr.value
    metainterp = MyMetaInterp()
    reader = ResumeDataFakeReader(storage, newboxes, metainterp)
    assert len(reader.virtuals_cache.virtuals_ptr_cache) == 1
    b2t = reader.decode_ref(tag(0, TAGVIRTUAL))

    trace = metainterp.trace
    expected = [
        (rop.NEW, [], b2t.getref_base(), LLtypeMixin.ssize),
        (rop.SETFIELD_GC, [b2t, c1s],  None, LLtypeMixin.adescr),
        (rop.SETFIELD_GC, [b2t, c1s],  None, LLtypeMixin.abisdescr),
        (rop.SETFIELD_GC, [b2t, b4t], None, LLtypeMixin.bdescr),
        ]
    with CompareableConsts():
        for x, y in zip(expected, trace):
            assert x == y
    #
    ptr = b2t.getref_base()._obj.container._as_ptr()
    assert lltype.typeOf(ptr) == lltype.Ptr(LLtypeMixin.S)
    assert ptr.a == 111
    assert ptr.b == lltype.nullptr(LLtypeMixin.NODE)


def test_virtual_adder_pending_fields():
    b2s, b4s = [RefFrontendOp(0), RefFrontendOp(0)]
    storage = Storage()
    memo = ResumeDataLoopMemo(FakeMetaInterpStaticData())
    modifier = ResumeDataVirtualAdder(None, storage, storage, None, memo)
    modifier.liveboxes_from_env = {}
    modifier.liveboxes = {}
    modifier.vfieldboxes = {}

    modifier.register_box(b2s)
    modifier.register_box(b4s)

    liveboxes = []
    modifier._number_virtuals(liveboxes, FakeOptimizer(), 0)
    assert liveboxes == [b2s, b4s] or liveboxes == [b4s, b2s]
    modifier._add_pending_fields(FakeOptimizer(), [
        ResOperation(rop.SETFIELD_GC, [b2s, b4s], descr=LLtypeMixin.nextdescr)])
    storage.rd_consts = memo.consts[:]
    storage.rd_numb = Numbering([])
    # resume
    demo55.next = lltype.nullptr(LLtypeMixin.NODE)
    b2t = RefFrontendOp(0)
    b2t.setref_base(demo55o)
    b4t = RefFrontendOp(0)
    b4t.setref_base(demo66o)
    newboxes = _resume_remap(liveboxes, [b2s, b4s], b2t, b4t)

    metainterp = MyMetaInterp()
    reader = ResumeDataFakeReader(storage, newboxes, metainterp)
    assert reader.virtuals_cache is None
    trace = metainterp.trace
    b2set = (rop.SETFIELD_GC, [b2t, b4t], None, LLtypeMixin.nextdescr)
    expected = [b2set]

    for x, y in zip(expected, trace):
        assert x == y
    assert len(expected) == len(trace)
    assert demo55.next == demo66

def test_virtual_adder_pending_fields_and_arrayitems():
    class Storage(object):
        pass
    storage = Storage()
    modifier = ResumeDataVirtualAdder(None, storage, storage, None, None)
    modifier._add_pending_fields(None, [])
    assert not storage.rd_pendingfields
    #
    class FieldDescr(AbstractDescr):
        def is_array_of_primitives(self):
            return False
    field_a = FieldDescr()
    storage = Storage()
    modifier = ResumeDataVirtualAdder(None, storage, storage, None, None)
    a = IntFrontendOp(0)
    b = IntFrontendOp(0)
    modifier.liveboxes_from_env = {a: rffi.cast(rffi.SHORT, 1042),
                                   b: rffi.cast(rffi.SHORT, 1061)}
    modifier._add_pending_fields(FakeOptimizer(), [
        ResOperation(rop.SETFIELD_GC, [a, b],
                     descr=field_a)])
    pf = storage.rd_pendingfields
    assert len(pf) == 1
    assert (annlowlevel.cast_base_ptr_to_instance(FieldDescr, pf[0].lldescr)
            is field_a)
    assert rffi.cast(lltype.Signed, pf[0].num) == 1042
    assert rffi.cast(lltype.Signed, pf[0].fieldnum) == 1061
    assert rffi.cast(lltype.Signed, pf[0].itemindex) == -1
    #
    array_a = FieldDescr()
    storage = Storage()
    modifier = ResumeDataVirtualAdder(None, storage, storage, None, None)
    a42 = IntFrontendOp(0)
    a61 = IntFrontendOp(0)
    a62 = IntFrontendOp(0)
    a63 = IntFrontendOp(0)
    modifier.liveboxes_from_env = {a42: rffi.cast(rffi.SHORT, 1042),
                                   a61: rffi.cast(rffi.SHORT, 1061),
                                   a62: rffi.cast(rffi.SHORT, 1062),
                                   a63: rffi.cast(rffi.SHORT, 1063)}
    modifier._add_pending_fields(FakeOptimizer(), [
        ResOperation(rop.SETARRAYITEM_GC, [a42, ConstInt(0), a61],
                     descr=array_a),
        ResOperation(rop.SETARRAYITEM_GC, [a42, ConstInt(2147483647), a62],
                     descr=array_a)])
    pf = storage.rd_pendingfields
    assert len(pf) == 2
    assert (annlowlevel.cast_base_ptr_to_instance(FieldDescr, pf[0].lldescr)
            is array_a)
    assert rffi.cast(lltype.Signed, pf[0].num) == 1042
    assert rffi.cast(lltype.Signed, pf[0].fieldnum) == 1061
    assert rffi.cast(lltype.Signed, pf[0].itemindex) == 0
    assert (annlowlevel.cast_base_ptr_to_instance(FieldDescr, pf[1].lldescr)
            is array_a)
    assert rffi.cast(lltype.Signed, pf[1].num) == 1042
    assert rffi.cast(lltype.Signed, pf[1].fieldnum) == 1062
    assert rffi.cast(lltype.Signed, pf[1].itemindex) == 2147483647
    #
    if sys.maxint >= 2147483648:
        py.test.raises(TagOverflow, modifier._add_pending_fields,
                       FakeOptimizer(),
                       [ResOperation(rop.SETARRAYITEM_GC,
                                     [a42, ConstInt(2147483648), a63],
                                     descr=array_a)])

def test_resume_reader_fields_and_arrayitems():
    class ResumeReader(AbstractResumeDataReader):
        def __init__(self, got=None, got_array=None):
            self.got = got
            self.got_array = got_array
        def setfield(self, struct, fieldnum, descr):
            assert lltype.typeOf(struct) is lltype.Signed
            assert lltype.typeOf(fieldnum) is rffi.SHORT
            fieldnum = rffi.cast(lltype.Signed, fieldnum)
            self.got.append((descr, struct, fieldnum))
        def setarrayitem(self, array, index, fieldnum, arraydescr):
            assert lltype.typeOf(array) is lltype.Signed
            assert lltype.typeOf(index) is lltype.Signed
            assert lltype.typeOf(fieldnum) is rffi.SHORT
            fieldnum = rffi.cast(lltype.Signed, fieldnum)
            self.got_array.append((arraydescr, array, index, fieldnum))
        def decode_ref(self, num):
            return rffi.cast(lltype.Signed, num) * 100
    got = []
    pf = lltype.nullptr(PENDINGFIELDSP.TO)
    ResumeReader(got)._prepare_pendingfields(pf)
    assert got == []
    #
    class FieldDescr(AbstractDescr):
        pass
    field_a = FieldDescr()
    field_b = FieldDescr()
    pf = lltype.malloc(PENDINGFIELDSP.TO, 2)
    pf[0].lldescr = annlowlevel.cast_instance_to_base_ptr(field_a)
    pf[0].num = rffi.cast(rffi.SHORT, 1042)
    pf[0].fieldnum = rffi.cast(rffi.SHORT, 1061)
    pf[0].itemindex = rffi.cast(rffi.INT, -1)
    pf[1].lldescr = annlowlevel.cast_instance_to_base_ptr(field_b)
    pf[1].num = rffi.cast(rffi.SHORT, 2042)
    pf[1].fieldnum = rffi.cast(rffi.SHORT, 2061)
    pf[1].itemindex = rffi.cast(rffi.INT, -1)
    got = []
    ResumeReader(got)._prepare_pendingfields(pf)
    assert got == [(field_a, 104200, 1061), (field_b, 204200, 2061)]
    #
    array_a = FieldDescr()
    pf = lltype.malloc(PENDINGFIELDSP.TO, 1)
    pf[0].lldescr = annlowlevel.cast_instance_to_base_ptr(array_a)
    pf[0].num = rffi.cast(rffi.SHORT, 1042)
    pf[0].fieldnum = rffi.cast(rffi.SHORT, 1063)
    pf[0].itemindex = rffi.cast(rffi.INT, 123)
    got_array = []
    ResumeReader(got_array=got_array)._prepare_pendingfields(pf)
    assert got_array == [(array_a, 104200, 123, 1063)]


def test_invalidation_needed():
    class options:
        failargs_limit = 10
        
    metainterp_sd = FakeMetaInterpStaticData()
    metainterp_sd.options = options
    memo = ResumeDataLoopMemo(metainterp_sd)
    modifier = ResumeDataVirtualAdder(None, None, None, None, memo)

    for i in range(5):
        assert not modifier._invalidation_needed(5, i)

    assert not modifier._invalidation_needed(7, 2)
    assert modifier._invalidation_needed(7, 3)

    assert not modifier._invalidation_needed(10, 2)
    assert not modifier._invalidation_needed(10, 3)
    assert modifier._invalidation_needed(10, 4)        
    
