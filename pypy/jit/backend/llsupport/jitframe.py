from pypy.rpython.lltypesystem import lltype, llmemory, rffi

GCINDEXLIST = lltype.GcArray(rffi.UINT)

# the JITFRAME that's stored on the heap. See backend/<backend>/arch.py for
# detailed explanation how it is on your architecture

JITFRAME = lltype.GcStruct(
    'JITFRAME',
    # gcindexlist is a list of indexes of GC ptrs
    # in the actual array
    ('jf_gcindexlist', lltype.Ptr(GCINDEXLIST)),
    # Once the execute_token() returns, the field 'jf_descr' stores the
    # descr of the last executed operation (either a GUARD, or FINISH).
    # This field is also set immediately before doing CALL_MAY_FORCE
    # or CALL_ASSEMBLER.
    ('jf_descr', llmemory.GCREF),
    # For the front-end: a GCREF for the savedata
    ('jf_savedata', llmemory.GCREF),
    # For GUARD_(NO)_EXCEPTION and GUARD_NOT_FORCED: the exception we
    # got.  (Note that in case of a regular FINISH generated from
    # RPython code that finishes the function with an exception, the
    # exception is not stored there, but in jf_values[0].ref.)
    ('jf_guard_exc', llmemory.GCREF),
    # the actual frame
    ('jf_frame', lltype.Array(lltype.Signed))
)

JITFRAMEPTR = lltype.Ptr(JITFRAME)
