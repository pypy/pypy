from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib.objectmodel import specialize
from rpython.rlib.debug import ll_assert
from rpython.rlib.objectmodel import enforceargs

SIZEOFSIGNED = rffi.sizeof(lltype.Signed)
IS_32BIT = (SIZEOFSIGNED == 4)

# this is an info that only depends on the assembler executed, copied from
# compiled loop token (in fact we could use this as a compiled loop token
# XXX do this

GCMAP = lltype.Array(lltype.Unsigned)
NULLGCMAP = lltype.nullptr(GCMAP)

@enforceargs(None, int, int)
def jitframeinfo_update_depth(jfi, base_ofs, new_depth):
    if new_depth > jfi.jfi_frame_depth:
        jfi.jfi_frame_depth = new_depth
        jfi.jfi_frame_size = base_ofs + new_depth * SIZEOFSIGNED

JITFRAMEINFO_SIZE = 2 * SIZEOFSIGNED # make sure this stays correct

JITFRAMEINFO = lltype.Struct(
    'JITFRAMEINFO',
    # the depth of the frame
    ('jfi_frame_depth', lltype.Signed),
    # the total size of the frame, in bytes
    ('jfi_frame_size', lltype.Signed),
    adtmeths = {
        'update_frame_depth': jitframeinfo_update_depth,
    },
)

NULLFRAMEINFO = lltype.nullptr(JITFRAMEINFO)
JITFRAMEINFOPTR = lltype.Ptr(JITFRAMEINFO)

# the JITFRAME that's stored on the heap. See backend/<backend>/arch.py for
# detailed explanation how it is on your architecture

def jitframe_allocate(frame_info):
    frame = lltype.malloc(JITFRAME, frame_info.jfi_frame_depth, zero=True)
    frame.jf_frame_info = frame_info
    return frame

def jitframe_resolve(frame):
    while frame.jf_forward:
        frame = frame.jf_forward
    return frame

JITFRAME = lltype.GcForwardReference()

JITFRAME.become(lltype.GcStruct(
    'JITFRAME',
    ('jf_frame_info', lltype.Ptr(JITFRAMEINFO)),
    # Once the execute_token() returns, the field 'jf_descr' stores the
    # descr of the last executed operation (either a GUARD, or FINISH).
    # This field is also set immediately before doing CALL_MAY_FORCE
    # or CALL_ASSEMBLER.
    ('jf_descr', llmemory.GCREF),
    # guard_not_forced descr
    ('jf_force_descr', llmemory.GCREF),
    # a map of GC pointers
    ('jf_gcmap', lltype.Ptr(GCMAP)),
    # how much we decrease stack pointer. Used around calls and malloc slowpath
    ('jf_extra_stack_depth', lltype.Signed),
    # For the front-end: a GCREF for the savedata
    ('jf_savedata', llmemory.GCREF),
    # For GUARD_(NO)_EXCEPTION and GUARD_NOT_FORCED: the exception we
    # got.  (Note that in case of a regular FINISH generated from
    # RPython code that finishes the function with an exception, the
    # exception is not stored there, but is simply kept as a variable there)
    ('jf_guard_exc', llmemory.GCREF),
    # in case the frame got reallocated, we have to forward it somewhere
    ('jf_forward', lltype.Ptr(JITFRAME)),
    # absolutely useless field used to make up for tracing hooks inflexibilities
    ('jf_gc_trace_state', lltype.Signed),
    # the actual frame
    ('jf_frame', lltype.Array(lltype.Signed)),
    # note that we keep length field, because it's crucial to have the data
    # about GCrefs here and not in frame info which might change
    adtmeths = {
        'allocate': jitframe_allocate,
        'resolve': jitframe_resolve,
    },
    rtti = True,
))

@specialize.memo()
def getofs(name):
    return llmemory.offsetof(JITFRAME, name)

GCMAPLENGTHOFS = llmemory.arraylengthoffset(GCMAP)
GCMAPBASEOFS = llmemory.itemoffsetof(GCMAP, 0)
BASEITEMOFS = llmemory.itemoffsetof(JITFRAME.jf_frame, 0)
LENGTHOFS = llmemory.arraylengthoffset(JITFRAME.jf_frame)
SIGN_SIZE = llmemory.sizeof(lltype.Signed)
UNSIGN_SIZE = llmemory.sizeof(lltype.Unsigned)
STACK_DEPTH_OFS = getofs('jf_extra_stack_depth')

def jitframe_trace(obj_addr, prev):
    if prev == llmemory.NULL:
        (obj_addr + getofs('jf_gc_trace_state')).signed[0] = -1
        return obj_addr + getofs('jf_descr')
    fld = (obj_addr + getofs('jf_gc_trace_state')).signed[0]
    if fld < 0:
        if fld == -1:
            (obj_addr + getofs('jf_gc_trace_state')).signed[0] = -2
            return obj_addr + getofs('jf_force_descr')
        elif fld == -2:
            (obj_addr + getofs('jf_gc_trace_state')).signed[0] = -3
            return obj_addr + getofs('jf_savedata')
        elif fld == -3:
            (obj_addr + getofs('jf_gc_trace_state')).signed[0] = -4
            return obj_addr + getofs('jf_guard_exc')
        elif fld == -4:
            (obj_addr + getofs('jf_gc_trace_state')).signed[0] = -5
            return obj_addr + getofs('jf_forward')
        else:
            if not (obj_addr + getofs('jf_gcmap')).address[0]:
                return llmemory.NULL    # done
            else:
                fld = 0    # fall-through
    # bit pattern
    # decode the pattern
    if IS_32BIT:
        # 32 possible bits
        state = fld & 0x1f
        no = fld >> 5
        MAX = 32
    else:
        # 64 possible bits
        state = fld & 0x3f
        no = fld >> 6
        MAX = 64
    gcmap = (obj_addr + getofs('jf_gcmap')).address[0]
    gcmap_lgt = (gcmap + GCMAPLENGTHOFS).signed[0]
    while no < gcmap_lgt:
        cur = (gcmap + GCMAPBASEOFS + UNSIGN_SIZE * no).unsigned[0]
        while not (cur & (1 << state)):
            state += 1
            if state == MAX:
                no += 1
                state = 0
                break      # next iteration of the outermost loop
        else:
            # found it
            index = no * SIZEOFSIGNED * 8 + state
            # save new state
            state += 1
            if state == MAX:
                no += 1
                state = 0
            if IS_32BIT:
                new_state = state | (no << 5)
            else:
                new_state = state | (no << 6)
            (obj_addr + getofs('jf_gc_trace_state')).signed[0] = new_state
            # sanity check
            frame_lgt = (obj_addr + getofs('jf_frame') + LENGTHOFS).signed[0]
            ll_assert(index < frame_lgt, "bogus frame field get")
            return (obj_addr + getofs('jf_frame') + BASEITEMOFS + SIGN_SIZE *
                    (index))
    return llmemory.NULL

CUSTOMTRACEFUNC = lltype.FuncType([llmemory.Address, llmemory.Address],
                                  llmemory.Address)
jitframe_trace_ptr = llhelper(lltype.Ptr(CUSTOMTRACEFUNC), jitframe_trace)

lltype.attachRuntimeTypeInfo(JITFRAME, customtraceptr=jitframe_trace_ptr)

JITFRAMEPTR = lltype.Ptr(JITFRAME)
