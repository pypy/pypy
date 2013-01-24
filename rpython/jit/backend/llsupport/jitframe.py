from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib.objectmodel import specialize
from rpython.rlib.debug import ll_assert

STATICSIZE = 0 # patch from the assembler backend
SIZEOFSIGNED = rffi.sizeof(lltype.Signed)
IS_32BIT = (SIZEOFSIGNED == 2 ** 31 - 1)

# this is an info that only depends on the assembler executed, copied from
# compiled loop token (in fact we could use this as a compiled loop token
# XXX do this

GCMAP = lltype.GcArray(lltype.Unsigned)
NULLGCMAP = lltype.nullptr(GCMAP)

JITFRAMEINFO = lltype.GcStruct(
    'JITFRAMEINFO',
    # the depth of frame
    ('jfi_frame_depth', lltype.Signed),
)

NULLFRAMEINFO = lltype.nullptr(JITFRAMEINFO)

# the JITFRAME that's stored on the heap. See backend/<backend>/arch.py for
# detailed explanation how it is on your architecture

def jitframe_allocate(frame_info):
    frame = lltype.malloc(JITFRAME, frame_info.jfi_frame_depth, zero=True)
    frame.jf_frame_info = frame_info
    return frame

JITFRAME = lltype.GcStruct(
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
    # For the front-end: a GCREF for the savedata
    ('jf_savedata', llmemory.GCREF),
    # For GUARD_(NO)_EXCEPTION and GUARD_NOT_FORCED: the exception we
    # got.  (Note that in case of a regular FINISH generated from
    # RPython code that finishes the function with an exception, the
    # exception is not stored there, but is simply kept as a variable there)
    ('jf_guard_exc', llmemory.GCREF),
    # absolutely useless field used to make up for tracing hooks inflexibilities
    ('jf_gc_trace_state', lltype.Signed),
    # the actual frame
    ('jf_frame', lltype.Array(lltype.Signed)),
    # note that we keep length field, because it's crucial to have the data
    # about GCrefs here and not in frame info which might change
    adtmeths = {
        'allocate': jitframe_allocate,
    },
    rtti = True,
)

@specialize.memo()
def getofs(name):
    return llmemory.offsetof(JITFRAME, name)

GCMAPLENGTHOFS = llmemory.arraylengthoffset(GCMAP)
GCMAPBASEOFS = llmemory.itemoffsetof(GCMAP, 0)
BASEITEMOFS = llmemory.itemoffsetof(JITFRAME.jf_frame, 0)
SIGN_SIZE = llmemory.sizeof(lltype.Signed)
UNSIGN_SIZE = llmemory.sizeof(lltype.Unsigned)

def jitframe_trace(obj_addr, prev):
    if prev == llmemory.NULL:
        (obj_addr + getofs('jf_gc_trace_state')).signed[0] = 0
        return obj_addr + getofs('jf_frame_info')
    fld = (obj_addr + getofs('jf_gc_trace_state')).signed[0]
    state = fld & 0x7 # 3bits of possible states
    if state == 0:
        (obj_addr + getofs('jf_gc_trace_state')).signed[0] = 1
        return obj_addr + getofs('jf_descr')
    elif state == 1:
        (obj_addr + getofs('jf_gc_trace_state')).signed[0] = 2
        return obj_addr + getofs('jf_force_descr')
    elif state == 2:
        (obj_addr + getofs('jf_gc_trace_state')).signed[0] = 3
        return obj_addr + getofs('jf_gcmap')
    elif state == 3:
        (obj_addr + getofs('jf_gc_trace_state')).signed[0] = 4
        return obj_addr + getofs('jf_savedata')
    elif state == 4:
        (obj_addr + getofs('jf_gc_trace_state')).signed[0] = 5
        return obj_addr + getofs('jf_guard_exc')
    ll_assert(state == 5, "invalid state")
    # bit pattern
    # decode the pattern
    if IS_32BIT:
        # 32 possible bits
        state = (fld >> 3) & 0x1f
        no = fld >> (3 + 5)
        MAX = 31
    else:
        # 64 possible bits
        state = (fld >> 3) & 0x3f
        no = fld >> (3 + 6)
        MAX = 63
    gcmap = (obj_addr + getofs('jf_gcmap')).address[0]
    gcmap_lgt = (gcmap + GCMAPLENGTHOFS).signed[0]
    while no < gcmap_lgt:
        cur = (gcmap + GCMAPBASEOFS + UNSIGN_SIZE * no).unsigned[0]
        while state < MAX and not (cur & (1 << state)):
            state += 1
        if state < MAX:
            # found it
            # save new state
            if IS_32BIT:
                new_state = 5 | ((state + 1) << 3) | (no << 8)
            else:
                new_state = 5 | ((state + 1) << 3) | (no << 9)
            (obj_addr + getofs('jf_gc_trace_state')).signed[0] = new_state
            return (obj_addr + getofs('jf_frame') + BASEITEMOFS + SIGN_SIZE *
                    (no * SIZEOFSIGNED * 8 + state))
        no += 1
        state = 0
    return llmemory.NULL

CUSTOMTRACEFUNC = lltype.FuncType([llmemory.Address, llmemory.Address],
                                  llmemory.Address)
jitframe_trace_ptr = llhelper(lltype.Ptr(CUSTOMTRACEFUNC), jitframe_trace)

lltype.attachRuntimeTypeInfo(JITFRAME, customtraceptr=jitframe_trace_ptr)

JITFRAMEPTR = lltype.Ptr(JITFRAME)
