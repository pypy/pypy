from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.jit.backend.llsupport.symbolic import WORD


GCREFTRACER = lltype.GcStruct(
    'GCREFTRACER',
    ('array_base_addr', lltype.Signed),
    ('array_length', lltype.Signed),
    rtti=True)

def gcrefs_trace(gc, obj_addr, callback, arg):
    obj = llmemory.cast_adr_to_ptr(obj_addr, lltype.Ptr(GCREFTRACER))
    i = 0
    length = obj.array_length
    addr = obj.array_base_addr
    while i < length:
        gc._trace_callback(callback, arg, addr + i * WORD)
        i += 1
lambda_gcrefs_trace = lambda: gcrefs_trace
