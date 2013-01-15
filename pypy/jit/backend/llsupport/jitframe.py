from pypy.rpython.lltypesystem import lltype, llmemory

# this is an info that only depends on the assembler executed, copied from
# compiled loop token (in fact we could use this as a compiled loop token
# XXX do this

JITFRAMEINFO = lltype.GcStruct(
    'JITFRAMEINFO',
    # the depth of frame
    ('jfi_frame_depth', lltype.Signed),
    # gcindexlist is a list of indexes of GC ptrs
    # in the actual array jf_frame of JITFRAME
    ('jfi_gcindexlist', lltype.Ptr(lltype.GcArray(lltype.Signed))),
    )

# the JITFRAME that's stored on the heap. See backend/<backend>/arch.py for
# detailed explanation how it is on your architecture

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
    # For the front-end: a GCREF for the savedata
    ('jf_savedata', llmemory.GCREF),
    # For GUARD_(NO)_EXCEPTION and GUARD_NOT_FORCED: the exception we
    # got.  (Note that in case of a regular FINISH generated from
    # RPython code that finishes the function with an exception, the
    # exception is not stored there, but is simply kept as a variable there)
    ('jf_guard_exc', llmemory.GCREF),
    # the actual frame
    ('jf_frame', lltype.Array(lltype.Signed))
    # it should be: , hints={'nolength': True})), but ll2ctypes is complaining
)

JITFRAMEPTR = lltype.Ptr(JITFRAME)
