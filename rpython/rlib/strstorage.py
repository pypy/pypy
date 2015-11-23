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
#   2. use llop.raw_load: despite the name, llop.raw_load DOES support reading
#      from GC pointers. However:
#
#        a. we would like to use a CompositeOffset as the offset (using the
#           same logic as in rstr.py:_get_raw_str_buf), but this is not (yet)
#           supported before translation: it works only if you pass an actual
#           integer
#
#        b. raw_load from a GC pointer is not (yet) supported by the
#           JIT. There are plans to introduce a gc_load operation: when it
#           will be there, we could fix the issue above and actually use it to
#           implement str_storage_getitem
#
#   3. the actual solution: cast rpy_string to a GcStruct which has the very
#      same layout, with the only difference that its 'chars' field is no
#      longer an Array(Char) but e.e. an Array(Signed). Then, we just need to
#      read the appropriate index into the array

from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper.lltypesystem.rstr import STR, _get_raw_str_buf
from rpython.rtyper.annlowlevel import llstr
from rpython.rlib.objectmodel import specialize

def compute_offsetof(TP, field):
    """
    NOT_RPYTHON
    """
    obj = lltype.malloc(TP, 0)
    baseadr = llmemory.cast_ptr_to_adr(obj)
    offset = llmemory.offsetof(TP, field)
    interioradr = baseadr + offset
    return (llmemory.cast_adr_to_int(interioradr, 'forced') -
            llmemory.cast_adr_to_int(baseadr, 'forced'))


@specialize.memo()
def rpy_string_as_type(TP):
    # sanity check that STR is actually what we think it is
    assert STR._flds == {
        'hash': lltype.Signed,
        'chars': lltype.Array(lltype.Char, hints={'immutable': True})
        }
    STR_AS_TP = lltype.GcStruct('rpy_string_as_%s' % TP,
                                ('hash',  lltype.Signed),
                                ('chars', lltype.Array(TP, hints={'immutable': True})))
    # sanity check
    assert compute_offsetof(STR, 'chars') == compute_offsetof(STR_AS_TP, 'chars')
    return STR_AS_TP

@specialize.ll()
def str_storage_getitem(TP, s, index):
    STR_AS_TP = rpy_string_as_type(TP)
    lls = llstr(s)
    str_as_tp = rffi.cast(lltype.Ptr(STR_AS_TP), lls)
    index = index / rffi.sizeof(TP)
    return str_as_tp.chars[index]
