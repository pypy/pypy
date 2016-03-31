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

def make_gcref_tracer(array_base_addr, gcrefs):
    # careful about the order here: the allocation of the GCREFTRACER
    # can trigger a GC.  So we must write the gcrefs into the raw
    # array only afterwards...
    tr = lltype.malloc(GCREFTRACER)
    tr.array_base_addr = array_base_addr
    tr.array_length = 0    # incremented as we populate the array_base_addr
    i = 0
    length = len(gcrefs)
    while i < length:
        p = rffi.cast(rffi.SIGNEDP, array_base_addr + i * WORD)
        # --no GC from here--
        p[0] = rffi.cast(lltype.Signed, gcrefs[i])
        tr.array_length += 1
        # --no GC until here--
        i += 1
    return tr
