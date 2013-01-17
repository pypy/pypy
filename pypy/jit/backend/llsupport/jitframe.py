from pypy.rpython.lltypesystem import lltype, llmemory

# this is an info that only depends on the assembler executed, copied from
# compiled loop token (in fact we could use this as a compiled loop token
# XXX do this

GCMAP = lltype.GcArray(lltype.Signed)
NULLGCMAP = lltype.nullptr(GCMAP)
# XXX make it SHORT not Signed

JITFRAMEINFO = lltype.GcStruct(
    'JITFRAMEINFO',
    # the depth of frame
    ('jfi_frame_depth', lltype.Signed),
    # gcindexlist is a list of indexes of GC ptrs
    # in the actual array jf_frame of JITFRAME
    ('jfi_gcmap', lltype.Ptr(GCMAP)),
    ('counter', lltype.Signed),
)

NULLFRAMEINFO = lltype.nullptr(JITFRAMEINFO)

# the JITFRAME that's stored on the heap. See backend/<backend>/arch.py for
# detailed explanation how it is on your architecture

def jitframe_allocate(frame_info):
    frame = lltype.malloc(JITFRAME, frame_info.jfi_frame_depth, zero=True)
    frame.jf_gcmap = frame_info.jfi_gcmap
    frame.jf_frame_info = frame_info
    return frame

def jitframe_copy(frame):
    frame_info = frame.jf_frame_info
    new_frame = lltype.malloc(JITFRAME, frame_info.jfi_frame_depth, zero=True)
    new_frame.jf_gcmap = frame_info.jfi_gcmap
    new_frame.jf_frame_info = frame_info
    return new_frame

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
    # a bitmask of where are GCREFS in the top of the frame (saved registers)
    # used for calls and failures
    ('jf_gcpattern', lltype.Signed),
    # a copy of gcmap from frameinfo
    ('jf_gcmap', lltype.Ptr(GCMAP)),
    # For the front-end: a GCREF for the savedata
    ('jf_savedata', llmemory.GCREF),
    # For GUARD_(NO)_EXCEPTION and GUARD_NOT_FORCED: the exception we
    # got.  (Note that in case of a regular FINISH generated from
    # RPython code that finishes the function with an exception, the
    # exception is not stored there, but is simply kept as a variable there)
    ('jf_guard_exc', llmemory.GCREF),
    # the actual frame
    ('jf_frame', lltype.Array(lltype.Signed)),
    # note that we keep length field, because it's crucial to have the data
    # about GCrefs here and not in frame info which might change
    adtmeths = {
        'allocate': jitframe_allocate,
        'copy': jitframe_copy,
    }
)

JITFRAMEPTR = lltype.Ptr(JITFRAME)
