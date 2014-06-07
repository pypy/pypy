from rpython.rlib import rgc, jit
from rpython.rlib.objectmodel import enforceargs
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rlib.debug import ll_assert
from rpython.rtyper.rptr import PtrRepr
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rstr
from rpython.rtyper.lltypesystem.lltype import staticAdtMethod, nullptr
from rpython.rtyper.lltypesystem.rstr import (STR, UNICODE, char_repr,
    string_repr, unichar_repr, unicode_repr)
from rpython.rtyper.rbuilder import AbstractStringBuilderRepr
from rpython.tool.sourcetools import func_with_new_name
from rpython.rtyper.llannotation import SomePtr
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.rgc import must_be_light_finalizer


# ------------------------------------------------------------
# Basic idea:
#
# - A StringBuilder has a rstr.STR of the specified initial size
#   (100 by default), which is filled gradually.
#
# - When it is full, we allocate extra buffers as *raw* memory
#   held by STRINGPIECE objects.  The STRINGPIECE has a destructor
#   that frees the memory, but usually the memory is freed explicitly
#   at build() time.
#
# - The data is copied at most twice, and only once in case it fits
#   into the initial size (and the GC supports shrinking the STR).
#
# ------------------------------------------------------------


def new_grow_func(name, mallocfn, copycontentsfn):
    @enforceargs(None, int)
    def stringbuilder_grow(ll_builder, needed):
        XXX
        allocated = ll_builder.allocated
        #if allocated < GROW_FAST_UNTIL:
        #    new_allocated = allocated << 1
        #else:
        extra_size = allocated >> 2
        try:
            new_allocated = ovfcheck(allocated + extra_size)
            new_allocated = ovfcheck(new_allocated + needed)
        except OverflowError:
            raise MemoryError
        newbuf = mallocfn(new_allocated)
        copycontentsfn(ll_builder.buf, newbuf, 0, 0, ll_builder.used)
        ll_builder.buf = newbuf
        ll_builder.allocated = new_allocated
    return func_with_new_name(stringbuilder_grow, name)

stringbuilder_grow = new_grow_func('stringbuilder_grow', rstr.mallocstr,
                                   rstr.copy_string_contents)
unicodebuilder_grow = new_grow_func('unicodebuilder_grow', rstr.mallocunicode,
                                    rstr.copy_unicode_contents)

STRINGPIECE = lltype.GcStruct('stringpiece',
    ('raw_ptr', rffi.CCHARP),
    ('piece_size', lltype.Signed),
    ('prev_piece', lltype.Ptr(lltype.GcForwardReference())),
    )
STRINGPIECE.prev_piece.TO.become(STRINGPIECE)

@must_be_light_finalizer
def ll_destroy_string_piece(piece):
    lltype.free(piece.raw_ptr, flavor='raw')

STRINGBUILDER = lltype.GcStruct('stringbuilder',
    ('current_buf', lltype.Ptr(STR)),
    ('current_ofs', lltype.Signed),
    ('current_end', lltype.Signed),
    ('total_size', lltype.Signed),
    ('extra_pieces', lltype.Ptr(STRINGPIECE)),
    adtmeths={
        'grow': staticAdtMethod(stringbuilder_grow),
        'copy_raw_to_string': staticAdtMethod(rstr.copy_raw_to_string),
    }
)

UNICODEBUILDER = lltype.GcStruct('unicodebuilder',
    ('allocated', lltype.Signed),
    ('used', lltype.Signed),
    ('buf', lltype.Ptr(UNICODE)),
    adtmeths={
        'grow': staticAdtMethod(unicodebuilder_grow),
        'copy_raw_to_string': staticAdtMethod(rstr.copy_raw_to_unicode),
    }
)

class BaseStringBuilderRepr(AbstractStringBuilderRepr):

    def rtyper_new(self, hop):
        destrptr = hop.rtyper.annotate_helper_fn(
            ll_destroy_string_piece, [SomePtr(lltype.Ptr(STRINGPIECE))])
        lltype.attachRuntimeTypeInfo(STRINGPIECE, destrptr=destrptr)
        return AbstractStringBuilderRepr.rtyper_new(self, hop)

    def empty(self):
        return nullptr(self.lowleveltype.TO)

    @classmethod
    def ll_new(cls, init_size):
        init_size = max(min(init_size, 1280), 32)
        ll_builder = lltype.malloc(cls.lowleveltype.TO)
        ll_builder.current_buf = cls.mallocfn(init_size)
        ofs = rffi.offsetof(STR, 'chars') + rffi.itemoffsetof(STR.chars, 0)
        if not we_are_translated():
            ofs = llmemory.raw_malloc_usage(ofs)    # for direct run
        ll_builder.current_ofs = ofs
        ll_builder.current_end = ofs + init_size
        ll_builder.total_size = init_size
        return ll_builder

    @staticmethod
    def ll_append(ll_builder, ll_str):
        lgt = len(ll_str.chars)
        ofs = ll_builder.current_ofs
        newofs = ofs + lgt
        if newofs > ll_builder.current_end:
            ll_builder.append_overflow(ll_builder, ll_str)
        else:
            ll_builder.current_ofs = newofs
            # --- no GC! ---
            raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
            data_start = llmemory.cast_ptr_to_adr(ll_str) + \
                rffi.offsetof(STR, 'chars') + rffi.itemoffsetof(STR.chars, 0)
            rffi.c_memcpy(rffi.ptradd(raw, ofs),
                          rffi.cast(rffi.CCHARP, data_start),
                          lgt)
            # --- end ---

    @staticmethod
    def ll_append_char(ll_builder, char):
        ofs = ll_builder.current_ofs
        if ofs == ll_builder.current_end:
            ll_builder.grow(ll_builder, 1)
        # --- no GC! ---
        raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
        raw[ofs] = char
        # --- end ---
        ll_builder.current_ofs = ofs + 1

    @staticmethod
    def ll_append_slice(ll_builder, ll_str, start, end):
        lgt = end - start
        ofs = ll_builder.current_ofs
        newofs = ofs + lgt
        if newofs > ll_builder.current_end:
            ll_str = rstr.LLHelpers.ll_stringslice_startstop(ll_str, start, end)
            ll_builder.append_overflow(ll_builder, ll_str)
        else:
            ll_builder.current_ofs = newofs
            # --- no GC! ---
            raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
            data_start = llmemory.cast_ptr_to_adr(ll_str) + \
               rffi.offsetof(STR, 'chars') + rffi.itemoffsetof(STR.chars, start)
            rffi.c_memcpy(rffi.ptradd(raw, ofs),
                          rffi.cast(rffi.CCHARP, data_start),
                          lgt)
            # --- end ---

    @staticmethod
    @jit.look_inside_iff(lambda ll_builder, char, times: jit.isconstant(times) and times <= 4)
    def ll_append_multiple_char(ll_builder, char, times):
        lgt = times
        ofs = ll_builder.current_ofs
        newofs = ofs + lgt
        if newofs > ll_builder.current_end:
            ll_str = rstr.LLHelpers.ll_char_mul(char, times)
            ll_builder.append_overflow(ll_builder, ll_str)
        else:
            ll_builder.current_ofs = newofs
            # --- no GC! ---
            raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
            while ofs < newofs:
                raw[ofs] = char
                ofs += 1
            # --- end ---

    @staticmethod
    def ll_append_charpsize(ll_builder, charp, size):
        XXX
        used = ll_builder.used
        if used + size > ll_builder.allocated:
            ll_builder.grow(ll_builder, size)
        ll_builder.copy_raw_to_string(charp, ll_builder.buf, used, size)
        ll_builder.used += size

    @staticmethod
    def ll_getlength(ll_builder):
        XXX
        return ll_builder.used

    @staticmethod
    def ll_build(ll_builder):
        final_size = ll_builder.total_size - (ll_builder.current_end -
                                              ll_builder.current_ofs)
        ll_assert(final_size >= 0, "negative final_size")

        buf = ll_builder.current_buf
        if final_size < len(buf.chars):
            buf = rgc.ll_shrink_array(buf, final_size)
        return buf

    @classmethod
    def ll_bool(cls, ll_builder):
        return ll_builder != nullptr(cls.lowleveltype.TO)

class StringBuilderRepr(BaseStringBuilderRepr):
    lowleveltype = lltype.Ptr(STRINGBUILDER)
    basetp = STR
    mallocfn = staticmethod(rstr.mallocstr)
    string_repr = string_repr
    char_repr = char_repr
    raw_ptr_repr = PtrRepr(
        lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True}))
    )

class UnicodeBuilderRepr(BaseStringBuilderRepr):
    lowleveltype = lltype.Ptr(UNICODEBUILDER)
    basetp = UNICODE
    mallocfn = staticmethod(rstr.mallocunicode)
    string_repr = unicode_repr
    char_repr = unichar_repr
    raw_ptr_repr = PtrRepr(
        lltype.Ptr(lltype.Array(lltype.UniChar, hints={'nolength': True}))
    )

unicodebuilder_repr = UnicodeBuilderRepr()
stringbuilder_repr = StringBuilderRepr()
