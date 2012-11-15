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

    # All values are stored in the following array, for now not very
    # compactly on 32-bit machines.
    ('jf_values', lltype.Array(VALUEUNION)))

DEADFRAMEPTR = lltype.Ptr(DEADFRAME)
