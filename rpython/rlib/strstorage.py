# Support for str_storage: i.e., reading primitive types out of RPython string
#
# There are various possible ways to implement it, however not all of them are
# easily supported by the JIT:
#
#   1. use _get_raw_str_buf and cast the chars buffer to RAW_STORAGE_PTR: this
#      works well without the JIT, but the cast to RAW_STORAGE_PTR needs to
#      happen inside a short "no GC" section (like the one in
#      rstr.py:copy_string_contents), which has no chance to work during
#      tracing
#
#   2. cast rpy_string to a GcStruct which has the very
#      same layout, with the only difference that its 'chars' field is no
#      longer an Array(Char) but e.e. an Array(Signed). Then, we just need to
#      read the appropriate index into the array.  To support this solution,
#      the JIT's optimizer needed a few workarounds.  This was removed.
#
#   3. use the newly introduced 'llop.gc_load_indexed'.
#


from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem.rstr import STR
from rpython.rtyper.annlowlevel import llstr
from rpython.rlib.objectmodel import specialize


@specialize.ll()
def str_storage_getitem(TP, s, byte_offset):
    # WARNING: the 'byte_offset' is, as its name says, measured in bytes;
    # however, it should be aligned for TP, otherwise on some platforms this
    # code will crash!
    lls = llstr(s)
    base_ofs = (llmemory.offsetof(STR, 'chars') +
                llmemory.itemoffsetof(STR.chars, 0))
    scale_factor = llmemory.sizeof(lltype.Char)
    return llop.gc_load_indexed(TP, lls, byte_offset,
                                scale_factor, base_ofs)
