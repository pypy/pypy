from rpython.rlib import rgc, jit
from rpython.rlib.objectmodel import enforceargs, specialize
from rpython.rlib.rarithmetic import ovfcheck, r_uint, intmask
from rpython.rlib.debug import ll_assert
from rpython.rlib.rgc import must_be_light_finalizer
from rpython.rtyper.rptr import PtrRepr
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rstr
from rpython.rtyper.lltypesystem.lltype import staticAdtMethod, nullptr
from rpython.rtyper.lltypesystem.rstr import (STR, UNICODE, char_repr,
    string_repr, unichar_repr, unicode_repr)
from rpython.rtyper.rbuilder import AbstractStringBuilderRepr
from rpython.tool.sourcetools import func_with_new_name
from rpython.rtyper.llannotation import SomePtr
from rpython.rtyper.annlowlevel import llstr, llunicode


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


def always_inline(func):
    func._always_inline_ = True
    return func


def new_grow_funcs(name, mallocfn):

    @enforceargs(None, int)
    def stringbuilder_grow(ll_builder, needed):
        needed += 7
        try:
            needed = ovfcheck(needed + ll_builder.total_size)
        except OverflowError:
            raise MemoryError
        needed &= ~7
        #
        new_piece = lltype.malloc(STRINGPIECE)
        charsize = ll_builder.charsize
        try:
            new_piece.piece_lgt = ovfcheck(needed * charsize)
        except OverflowError:
            raise MemoryError
        raw_ptr = lltype.malloc(rffi.CCHARP.TO, needed * charsize, flavor='raw')
        new_piece.raw_ptr = raw_ptr
        new_piece.prev_piece = ll_builder.extra_pieces
        ll_builder.extra_pieces = new_piece
        ll_builder.current_ofs = rffi.cast(lltype.Unsigned, raw_ptr)
        ll_builder.current_end = (rffi.cast(lltype.Unsigned, raw_ptr) +
                                  r_uint(needed * charsize))
        try:
            ll_builder.total_size = ovfcheck(ll_builder.total_size + needed)
        except OverflowError:
            raise MemoryError
        if ll_builder.current_buf:
            STRTYPE = lltype.typeOf(ll_builder.current_buf).TO
            ll_builder.initial_buf = ll_builder.current_buf
            ll_builder.current_buf = lltype.nullptr(STRTYPE)
        return ll_builder.current_ofs

    def stringbuilder_append_overflow(ll_builder, ll_str):
        # First, the part that still fits in the current piece
        ofs = ll_builder.current_ofs
        part1 = intmask(ll_builder.current_end - ofs) # in bytes, not (uni)chars
        # --- no GC! ---
        raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
        rffi.c_memcpy(rffi.ptradd(raw, intmask(ofs)),
                      ll_str2raw(ll_str, 0),
                      part1)
        # --- end ---
        # Next, the remaining part, in a new piece
        part1 //= ll_builder.charsize
        part2 = len(ll_str.chars) - part1        # in (uni)chars
        ll_assert(part2 > 0, "append_overflow: no overflow")
        ofs = stringbuilder_grow(ll_builder, part2)
        ll_builder.current_ofs = ofs + r_uint(part2 * ll_builder.charsize)
        # --- no GC! ---
        ll_assert(not ll_builder.current_buf, "after grow(), current_buf!=NULL")
        raw = lltype.nullptr(rffi.CCHARP.TO)
        rffi.c_memcpy(rffi.ptradd(raw, intmask(ofs)),
                      ll_str2raw(ll_str, part1),
                      part2 * ll_builder.charsize)
        # --- end ---

    return (func_with_new_name(stringbuilder_grow, '%s_grow' % name),
            func_with_new_name(stringbuilder_append_overflow,
                               '%s_append_overflow' % name))

stringbuilder_grows = new_grow_funcs('stringbuilder', rstr.mallocstr)
unicodebuilder_grows = new_grow_funcs('unicodebuilder', rstr.mallocunicode)

STRINGPIECE = lltype.GcStruct('stringpiece',
    ('raw_ptr', rffi.CCHARP),
    ('piece_lgt', lltype.Signed),        # in bytes
    ('prev_piece', lltype.Ptr(lltype.GcForwardReference())),
    rtti=True)
STRINGPIECE.prev_piece.TO.become(STRINGPIECE)

@must_be_light_finalizer
def ll_destroy_string_piece(piece):
    if piece.raw_ptr:
        lltype.free(piece.raw_ptr, flavor='raw')

_SbRtti = lltype.getRuntimeTypeInfo(STRINGPIECE)
def ll_string_piece_rtti(piece):
    return _SbRtti

STRINGBUILDER = lltype.GcStruct('stringbuilder',
    ('current_buf', lltype.Ptr(STR)),
    ('current_ofs', lltype.Unsigned),
    ('current_end', lltype.Unsigned),
    ('total_size', lltype.Signed),
    ('extra_pieces', lltype.Ptr(STRINGPIECE)),
    ('initial_buf', lltype.Ptr(STR)),
    adtmeths={
        'grow': staticAdtMethod(stringbuilder_grows[0]),
        'append_overflow': staticAdtMethod(stringbuilder_grows[1]),
        'copy_raw_to_string': staticAdtMethod(rstr.copy_raw_to_string),
        'charsize': 1,
    }
)

UNICODEBUILDER = lltype.GcStruct('unicodebuilder',
    ('current_buf', lltype.Ptr(UNICODE)),
    ('current_ofs', lltype.Unsigned),     # position measured in *bytes*
    ('current_end', lltype.Unsigned),     # position measured in *bytes*
    ('total_size', lltype.Signed),
    ('extra_pieces', lltype.Ptr(STRINGPIECE)),
    ('initial_buf', lltype.Ptr(UNICODE)),
    adtmeths={
        'grow': staticAdtMethod(unicodebuilder_grows[0]),
        'append_overflow': staticAdtMethod(unicodebuilder_grows[1]),
        'copy_raw_to_string': staticAdtMethod(rstr.copy_raw_to_unicode),
        'charsize': rffi.sizeof(lltype.UniChar),
    }
)


def ll_baseofs(ll_str):
    STRTYPE = lltype.typeOf(ll_str).TO
    ofs = rffi.offsetof(STRTYPE, 'chars') + rffi.itemoffsetof(STRTYPE.chars, 0)
    return r_uint(llmemory.raw_malloc_usage(ofs))    # for direct run
ll_baseofs._always_inline_ = True

def ll_str2raw(ll_str, charoffset):
    STRTYPE = lltype.typeOf(ll_str).TO
    ofs = (rffi.offsetof(STRTYPE, 'chars') +
           rffi.itemoffsetof(STRTYPE.chars, 0))
    ofs = llmemory.raw_malloc_usage(ofs)    # for direct run
    ofs += rffi.sizeof(STRTYPE.chars.OF) * charoffset
    return rffi.ptradd(rffi.cast(rffi.CCHARP, ll_str), ofs)
ll_str2raw._always_inline_ = True

def ll_rawsetitem(raw, byteoffset, char):
    raw = rffi.ptradd(raw, intmask(byteoffset))
    if lltype.typeOf(char) == lltype.Char:
        raw[0] = char
    else:
        rffi.cast(rffi.CWCHARP, raw)[0] = char
ll_rawsetitem._always_inline_ = True


class BaseStringBuilderRepr(AbstractStringBuilderRepr):

    def rtyper_new(self, hop):
        destrptr = hop.rtyper.annotate_helper_fn(
            ll_destroy_string_piece, [SomePtr(lltype.Ptr(STRINGPIECE))])
        hop.rtyper.attachRuntimeTypeInfoFunc(STRINGPIECE, ll_string_piece_rtti,
                                             STRINGPIECE, destrptr)
        return AbstractStringBuilderRepr.rtyper_new(self, hop)

    def empty(self):
        return nullptr(self.lowleveltype.TO)

    @classmethod
    def ll_new(cls, init_size):
        init_size = max(min(init_size, 1280), 32)
        ll_builder = lltype.malloc(cls.lowleveltype.TO)
        ll_builder.current_buf = cls.mallocfn(init_size)
        ofs = ll_baseofs(ll_builder.current_buf)
        ll_builder.current_ofs = ofs
        ll_builder.current_end = ofs + init_size * ll_builder.charsize
        ll_builder.total_size = init_size
        return ll_builder

    @staticmethod
    @always_inline
    def ll_append(ll_builder, ll_str):
        if jit.we_are_jitted():
            if BaseStringBuilderRepr._ll_jit_try_append_slice(
                    ll_builder, ll_str, 0, len(ll_str.chars)):
                return
        BaseStringBuilderRepr._ll_append(ll_builder, ll_str)

    @staticmethod
    @always_inline
    @jit.dont_look_inside
    def _ll_append(ll_builder, ll_str):
        lgt = len(ll_str.chars) * ll_builder.charsize      # in bytes
        ofs = ll_builder.current_ofs
        newofs = ofs + r_uint(lgt)
        if newofs > ll_builder.current_end:
            ll_builder.append_overflow(ll_builder, ll_str)
        else:
            ll_builder.current_ofs = newofs
            # --- no GC! ---
            raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
            rffi.c_memcpy(rffi.ptradd(raw, intmask(ofs)),
                          ll_str2raw(ll_str, 0),
                          lgt)
            # --- end ---

    @staticmethod
    @always_inline
    def ll_append_char(ll_builder, char):
        if jit.we_are_jitted():
            BaseStringBuilderRepr._ll_jit_append_char(ll_builder, char)
        else:
            BaseStringBuilderRepr._ll_append_char(ll_builder, char)

    @staticmethod
    @always_inline
    @jit.dont_look_inside
    def _ll_append_char(ll_builder, char):
        ofs = ll_builder.current_ofs
        if ofs == ll_builder.current_end:
            ofs = ll_builder.grow(ll_builder, 1)
        # --- no GC! ---
        raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
        ll_rawsetitem(raw, ofs, char)
        # --- end ---
        ll_builder.current_ofs = ofs + ll_builder.charsize

    @staticmethod
    def _ll_jit_append_char(ll_builder, char):
        ofs = ll_builder.current_ofs
        if bool(ll_builder.current_buf) and ofs < ll_builder.current_end:
            ll_builder.current_ofs = ofs + ll_builder.charsize
            buf = ll_builder.current_buf
            index = (ofs - ll_baseofs(buf)) // ll_builder.charsize
            buf.chars[index] = char
            return
        BaseStringBuilderRepr._ll_append_char(ll_builder, char)

    @staticmethod
    def ll_append_char_2(ll_builder, char0, char1):
        if jit.we_are_jitted():
            BaseStringBuilderRepr._ll_jit_append_char_2(ll_builder, char0,char1)
        else:
            BaseStringBuilderRepr._ll_append_char_2(ll_builder, char0, char1)

    @staticmethod
    @jit.dont_look_inside
    def _ll_append_char_2(ll_builder, char0, char1):
        ofs = ll_builder.current_ofs
        end = ofs + 2 * ll_builder.charsize
        if end > ll_builder.current_end:
            ofs = ll_builder.grow(ll_builder, 2)
            end = ofs + 2 * ll_builder.charsize
        ll_builder.current_ofs = end
        # --- no GC! ---
        raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
        ll_rawsetitem(raw, ofs, char0)
        ll_rawsetitem(raw, ofs + ll_builder.charsize, char1)
        # --- end ---

    @staticmethod
    def _ll_jit_append_char_2(ll_builder, char0, char1):
        ofs = ll_builder.current_ofs
        end = ofs + 2 * ll_builder.charsize
        if bool(ll_builder.current_buf) and end <= ll_builder.current_end:
            ll_builder.current_ofs = end
            buf = ll_builder.current_buf
            index = (ofs - ll_baseofs(buf)) // ll_builder.charsize
            buf.chars[index] = char0
            buf.chars[index + 1] = char1
            return
        BaseStringBuilderRepr._ll_append_char_2(ll_builder, char0, char1)

    @staticmethod
    @always_inline
    def ll_append_slice(ll_builder, ll_str, start, end):
        if jit.we_are_jitted():
            if BaseStringBuilderRepr._ll_jit_try_append_slice(
                    ll_builder, ll_str, start, end - start):
                return
        BaseStringBuilderRepr._ll_append_slice(ll_builder, ll_str,
                                               start, end)

    @staticmethod
    @jit.dont_look_inside
    def _ll_append_slice(ll_builder, ll_str, start, end):
        lgt = (end - start) * ll_builder.charsize      # in bytes
        ofs = ll_builder.current_ofs
        newofs = ofs + r_uint(lgt)
        if newofs > ll_builder.current_end:
            ll_str = rstr.LLHelpers.ll_stringslice_startstop(ll_str, start, end)
            ll_builder.append_overflow(ll_builder, ll_str)
        else:
            ll_builder.current_ofs = newofs
            # --- no GC! ---
            raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
            rffi.c_memcpy(rffi.ptradd(raw, intmask(ofs)),
                          ll_str2raw(ll_str, start),
                          lgt)
            # --- end ---

    @staticmethod
    def _ll_jit_try_append_slice(ll_builder, ll_str, start, size):
        if jit.isconstant(size):
            if size == 0:
                return True
            if size == 1:
                BaseStringBuilderRepr.ll_append_char(ll_builder,
                                                     ll_str.chars[start])
                return True
            if size == 2:
                BaseStringBuilderRepr.ll_append_char_2(ll_builder,
                                                       ll_str.chars[start],
                                                       ll_str.chars[start + 1])
                return True
        if bool(ll_builder.current_buf):
            ofs = ll_builder.current_ofs
            end = ofs + r_uint(size * ll_builder.charsize)
            if end <= ll_builder.current_end:
                ll_builder.current_ofs = end
                buf = ll_builder.current_buf
                index = intmask(ofs - ll_baseofs(buf)) // ll_builder.charsize
                if lltype.typeOf(buf).TO.chars.OF == lltype.Char:
                    rstr.copy_string_contents(ll_str, buf, start, index, size)
                else:
                    rstr.copy_unicode_contents(ll_str, buf, start, index, size)
                return True
        return False     # use the fall-back path

    @staticmethod
    @always_inline
    def ll_append_multiple_char(ll_builder, char, times):
        if jit.we_are_jitted():
            if BaseStringBuilderRepr._ll_jit_try_append_multiple_char(
                    ll_builder, char, times):
                return
        BaseStringBuilderRepr._ll_append_multiple_char(ll_builder, char, times)

    @staticmethod
    @jit.dont_look_inside
    def _ll_append_multiple_char(ll_builder, char, times):
        lgt = times * ll_builder.charsize     # in bytes
        ofs = ll_builder.current_ofs
        newofs = ofs + r_uint(lgt)
        if newofs > ll_builder.current_end:
            ll_str = rstr.LLHelpers.ll_char_mul(char, times)
            ll_builder.append_overflow(ll_builder, ll_str)
        else:
            ll_builder.current_ofs = newofs
            # --- no GC! ---
            raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
            while ofs < newofs:
                ll_rawsetitem(raw, ofs, char)
                ofs += ll_builder.charsize
            # --- end ---

    @staticmethod
    def _ll_jit_try_append_multiple_char(ll_builder, char, size):
        if jit.isconstant(size):
            if size == 0:
                return True
            if size == 1:
                BaseStringBuilderRepr.ll_append_char(ll_builder, char)
                return True
            if size == 2:
                BaseStringBuilderRepr.ll_append_char_2(ll_builder, char, char)
                return True
            if size == 3:
                BaseStringBuilderRepr.ll_append_char(ll_builder, char)
                BaseStringBuilderRepr.ll_append_char_2(ll_builder, char, char)
                return True
            if size == 4:
                BaseStringBuilderRepr.ll_append_char_2(ll_builder, char, char)
                BaseStringBuilderRepr.ll_append_char_2(ll_builder, char, char)
                return True
        return False     # use the fall-back path

    @staticmethod
    @jit.dont_look_inside
    def ll_append_charpsize(ll_builder, charp, size):
        lgt = size * ll_builder.charsize     # in bytes
        ofs = ll_builder.current_ofs
        newofs = ofs + r_uint(lgt)
        if newofs > ll_builder.current_end:
            if ll_builder.charsize == 1:
                ll_str = llstr(rffi.charpsize2str(charp, size))
            else:
                ll_str = llunicode(rffi.wcharpsize2unicode(charp, size))
            ll_builder.append_overflow(ll_builder, ll_str)
        else:
            ll_builder.current_ofs = newofs
            # --- no GC! ---
            raw = rffi.cast(rffi.CCHARP, ll_builder.current_buf)
            rffi.c_memcpy(rffi.ptradd(raw, intmask(ofs)),
                          rffi.cast(rffi.CCHARP, charp),
                          lgt)
            # --- end ---

    @staticmethod
    @always_inline
    def ll_getlength(ll_builder):
        num_chars_missing_from_last_piece = intmask(
            (ll_builder.current_end - ll_builder.current_ofs)
            // ll_builder.charsize)
        return ll_builder.total_size - num_chars_missing_from_last_piece

    @classmethod
    def ll_build(cls, ll_builder):
        buf = ll_builder.current_buf
        if buf:
            # fast-path: the result fits in a single buf.
            # it is already a GC string
            final_size = cls.ll_getlength(ll_builder)
            ll_assert(final_size >= 0, "negative final_size")
            if ll_builder.total_size != final_size:
                ll_assert(final_size < ll_builder.total_size,
                          "final_size > ll_builder.total_size?")
                buf = rgc.ll_shrink_array(buf, final_size)
                ll_builder.total_size = final_size
                ll_builder.current_buf = buf
                ll_builder.current_ofs = r_uint(0)
                ll_builder.current_end = r_uint(0)
            return buf
        else:
            return BaseStringBuilderRepr._ll_build_extra(cls, ll_builder)

    @staticmethod
    @jit.dont_look_inside
    def _ll_build_extra(cls, ll_builder):
        final_size = cls.ll_getlength(ll_builder)
        ll_assert(final_size >= 0, "negative final_size")
        extra = ll_builder.extra_pieces
        ll_assert(bool(extra), "build() twice on a StringBuilder")
        ll_builder.extra_pieces = lltype.nullptr(STRINGPIECE)
        result = cls.mallocfn(final_size)
        piece_lgt = intmask(       # in bytes
            ll_builder.current_ofs - rffi.cast(lltype.Unsigned, extra.raw_ptr))
        ll_assert(piece_lgt == intmask(extra.piece_lgt -
                            (ll_builder.current_end - ll_builder.current_ofs)),
                  "bogus last piece_lgt")
        ll_builder.total_size = final_size
        ll_builder.current_buf = result
        ll_builder.current_ofs = r_uint(0)
        ll_builder.current_end = r_uint(0)

        # --- no GC! ---
        dst = ll_str2raw(result, final_size)
        while True:
            dst = rffi.ptradd(dst, -piece_lgt)
            rffi.c_memcpy(dst, extra.raw_ptr, piece_lgt)
            lltype.free(extra.raw_ptr, flavor='raw')
            extra.raw_ptr = lltype.nullptr(rffi.CCHARP.TO)
            extra = extra.prev_piece
            if not extra:
                break
            piece_lgt = extra.piece_lgt
        # --- end ---

        initial_len = len(ll_builder.initial_buf.chars)
        ll_assert(dst == ll_str2raw(result, initial_len),
                  "bad first piece size")
        cls.copy_string_contents_fn(ll_builder.initial_buf, result,
                                    0, 0, initial_len)
        return result

    @classmethod
    def ll_bool(cls, ll_builder):
        return ll_builder != nullptr(cls.lowleveltype.TO)

class StringBuilderRepr(BaseStringBuilderRepr):
    lowleveltype = lltype.Ptr(STRINGBUILDER)
    basetp = STR
    mallocfn = staticmethod(rstr.mallocstr)
    copy_string_contents_fn = staticmethod(rstr.copy_string_contents)
    string_repr = string_repr
    char_repr = char_repr
    raw_ptr_repr = PtrRepr(
        lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True}))
    )

class UnicodeBuilderRepr(BaseStringBuilderRepr):
    lowleveltype = lltype.Ptr(UNICODEBUILDER)
    basetp = UNICODE
    mallocfn = staticmethod(rstr.mallocunicode)
    copy_string_contents_fn = staticmethod(rstr.copy_unicode_contents)
    string_repr = unicode_repr
    char_repr = unichar_repr
    raw_ptr_repr = PtrRepr(
        lltype.Ptr(lltype.Array(lltype.UniChar, hints={'nolength': True}))
    )

unicodebuilder_repr = UnicodeBuilderRepr()
stringbuilder_repr = StringBuilderRepr()
