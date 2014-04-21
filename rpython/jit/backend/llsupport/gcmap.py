from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem import lltype
from rpython.jit.backend.llsupport import jitframe
from rpython.rlib.rarithmetic import r_uint
from rpython.jit.backend.llsupport.symbolic import WORD

GCMAP_STM_LOCATION = 2     # xxx add this only if stm

def allocate_gcmap(assembler, frame_depth, fixed_size, stm_location=None):
    size = frame_depth + fixed_size
    malloc_size = (size // WORD // 8 + 1) + GCMAP_STM_LOCATION + 1
    rawgcmap = assembler.datablockwrapper.malloc_aligned(WORD * malloc_size,
                                                    WORD)
    # set the length field
    rffi.cast(rffi.CArrayPtr(lltype.Signed), rawgcmap)[0] = malloc_size - 1
    gcmap = rffi.cast(lltype.Ptr(jitframe.GCMAP), rawgcmap)
    # zero the area
    for i in range(malloc_size - 3):
        gcmap[i] = r_uint(0)
    # write the stm_location in the last two words
    raw_stm_location = extract_raw_stm_location(stm_location)
    gcmap[malloc_size - 3], gcmap[malloc_size - 2] = raw_stm_location
    return gcmap

def extract_raw_stm_location(stm_location):
    if stm_location is not None:
        num = rffi.cast(lltype.Unsigned, stm_location.num)
        ref = rffi.cast(lltype.Unsigned, stm_location.ref)
    else:
        num = r_uint(0)
        ref = r_uint(0)
    return (num, ref)
