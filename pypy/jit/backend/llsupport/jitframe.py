from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codewriter import longlong


VALUEUNION = lltype.Struct('VALUEUNION',
                           ('int', lltype.Signed),
                           ('ref', llmemory.GCREF),
                           ('float', longlong.FLOATSTORAGE),
                           hints={'union': True})

DEADFRAME = lltype.GcStruct(
    'DEADFRAME',

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

    # All values are stored in the following array, for now not very
    # compactly on 32-bit machines.
    ('jf_values', lltype.Array(VALUEUNION)))

DEADFRAMEPTR = lltype.Ptr(DEADFRAME)
