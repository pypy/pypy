from rpython.rlib import rgc, jit
from rpython.rlib.objectmodel import enforceargs, specialize
from rpython.rlib.rarithmetic import ovfcheck, r_uint
from rpython.rlib.debug import ll_assert
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
# XXX too much a mess to handle the case where the JIT sees this code.
# Think about an easier alternative, like using raw_store(current_buf, ..)
# uniformly, where current_buf is a GC pointer that can be NULL.  We'd
# need support in the JIT to map that to virtual string index.  We'd also
# need a way to express c_memcpy() below --- similar to copystrcontent,
# but without the assumption that it's about a string (or unicode).
#
# XXX alternatively, a simpler solution might be to allocate all pieces
# as GC-managed rstr.STR.  To avoid filling the old generation with
# garbage we could add a weakref holding the most recently built chain
# of STRs, and reuse it the next time if it's still there.
#
# ------------------------------------------------------------


def always_inline(func):
    func._always_inline_ = True
    return func


def new_grow_funcs(name, mallocfn):

    @enforceargs(None, int)
    def stringbuilder_grow(ll_builder, needed):
        try:
            needed = ovfcheck(needed + ll_builder.total_size)
            needed = ovfcheck(needed + 63) & ~63
            total_size = ll_builder.total_size + needed
        except OverflowError:
            raise MemoryError
        #
        new_string = mallocfn(needed)
        #
        old_piece = lltype.malloc(STRINGPIECE)
        old_piece.buf = ll_builder.current_buf
        old_piece.prev_piece = ll_builder.extra_pieces
        ll_builder.extra_pieces = old_piece
        ll_builder.current_buf = new_string
        ll_builder.current_pos = 0
        ll_builder.current_end = needed
        ll_builder.total_size = total_size

    def stringbuilder_append_overflow(ll_builder, ll_str, size):
        # First, the part that still fits in the current piece
        part1 = ll_builder.current_end - ll_builder.current_pos
        start = ll_builder.skip
        ll_builder.copy_string_contents(ll_str, ll_builder.current_buf,
                                        start, ll_builder.current_pos,
                                        part1)
        ll_builder.skip += part1
        stringbuilder_grow(ll_builder, size - part1)

    return (func_with_new_name(stringbuilder_grow, '%s_grow' % name),
            func_with_new_name(stringbuilder_append_overflow,
                               '%s_append_overflow' % name))

stringbuilder_grows = new_grow_funcs('stringbuilder', rstr.mallocstr)
unicodebuilder_grows = new_grow_funcs('unicodebuilder', rstr.mallocunicode)

STRINGPIECE = lltype.GcStruct('stringpiece',
    ('buf', lltype.Ptr(STR)),
    ('prev_piece', lltype.Ptr(lltype.GcForwardReference())))
STRINGPIECE.prev_piece.TO.become(STRINGPIECE)

STRINGBUILDER = lltype.GcStruct('stringbuilder',
    ('current_buf', lltype.Ptr(STR)),
    ('current_pos', lltype.Signed),
    ('current_end', lltype.Signed),
    ('total_size', lltype.Signed),
    ('skip', lltype.Signed),
    ('extra_pieces', lltype.Ptr(STRINGPIECE)),
    adtmeths={
        'grow': staticAdtMethod(stringbuilder_grows[0]),
        'append_overflow': staticAdtMethod(stringbuilder_grows[1]),
        'copy_string_contents': staticAdtMethod(rstr.copy_string_contents),
        'copy_raw_to_string': staticAdtMethod(rstr.copy_raw_to_string),
    }
)

UNICODEBUILDER = lltype.GcStruct('unicodebuilder',
    ('current_buf', lltype.Ptr(UNICODE)),
    ('current_ofs', lltype.Signed),     # position measured in *bytes*
    ('current_end', lltype.Signed),     # position measured in *bytes*
    ('total_size', lltype.Signed),
    ('extra_pieces', lltype.Ptr(STRINGPIECE)),
    ('initial_buf', lltype.Ptr(UNICODE)),
    adtmeths={
        'grow': staticAdtMethod(unicodebuilder_grows[0]),
        'append_overflow': staticAdtMethod(unicodebuilder_grows[1]),
        'copy_raw_to_string': staticAdtMethod(rstr.copy_raw_to_unicode),
    }
)


@always_inline
def ll_str2raw(ll_str, charoffset):
    STRTYPE = lltype.typeOf(ll_str).TO
    ofs = (rffi.offsetof(STRTYPE, 'chars') +
           rffi.itemoffsetof(STRTYPE.chars, 0))
    ofs = llmemory.raw_malloc_usage(ofs)    # for direct run
    ofs += rffi.sizeof(STRTYPE.chars.OF) * charoffset
    return rffi.ptradd(rffi.cast(rffi.CCHARP, ll_str), ofs)


class BaseStringBuilderRepr(AbstractStringBuilderRepr):
    def empty(self):
        return nullptr(self.lowleveltype.TO)

    @classmethod
    def ll_new(cls, init_size):
        init_size = min(init_size, 1280)
        ll_builder = lltype.malloc(cls.lowleveltype.TO)
        ll_builder.current_buf = cls.mallocfn(init_size)
        ll_builder.current_pos = 0
        ll_builder.current_end = init_size
        ll_builder.total_size = init_size
        return ll_builder

    @staticmethod
    @always_inline
    def ll_append(ll_builder, ll_str):
        BaseStringBuilderRepr.ll_append_slice(ll_builder, ll_str,
                                              0, len(ll_str.chars))

    @staticmethod
    @always_inline
    def ll_append_char(ll_builder, char):
        jit.conditional_call(ll_builder.current_pos == ll_builder.current_end,
                             ll_builder.grow, ll_builder, 1)
        pos = ll_builder.current_pos
        ll_builder.current_pos = pos + 1
        ll_builder.current_buf.chars[pos] = char

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
        if uint_gt(end, ll_builder.current_end):
            BaseStringBuilderRepr._ll_append_char(ll_builder, char0)
            BaseStringBuilderRepr._ll_append_char(ll_builder, char1)
            return
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
        if bool(ll_builder.current_buf) and uint_le(end,
                                                    ll_builder.current_end):
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
        size = end - start
        if jit.we_are_jitted():
            if BaseStringBuilderRepr._ll_jit_try_append_slice(
                    ll_builder, ll_str, size):
                return
        ll_builder.skip = start
        jit.conditional_call(
            size > ll_builder.current_end - ll_builder.current_pos,
            ll_builder.append_overflow, ll_builder, ll_str, size)
        start = ll_builder.skip
        size = end - start
        pos = ll_builder.current_pos
        ll_builder.copy_string_contents(ll_str, ll_builder.current_buf,
                                        start, pos, size)
        ll_builder.current_pos = pos + size

    @staticmethod
    def _ll_jit_try_append_slice(ll_builder, ll_str, size):
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
            end = ofs + size * ll_builder.charsize
            if uint_le(end, ll_builder.current_end):
                ll_builder.current_ofs = end
                buf = ll_builder.current_buf
                index = (ofs - ll_baseofs(buf)) // ll_builder.charsize
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
        part1 = ll_builder.current_end - ll_builder.current_pos
        if times > part1:
            times -= part1
            buf = ll_builder.current_buf
            for i in xrange(ll_builder.current_pos, ll_builder.current_end):
                buf.chars[i] = char
            ll_builder.grow(ll_builder, times)
        #
        buf = ll_builder.current_buf
        pos = ll_builder.current_pos
        end = pos + times
        ll_builder.current_pos = end
        for i in xrange(pos, end):
            buf.chars[i] = char

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
        part1 = ll_builder.current_end - ll_builder.current_pos
        if size > part1:
            # First, the part that still fits
            ll_builder.copy_raw_to_string(charp, ll_builder.current_buf,
                                          ll_builder.current_pos, part1)
            charp = rffi.ptradd(charp, part1)
            size -= part1
            ll_builder.grow(ll_builder, size)
        #
        pos = ll_builder.current_pos
        ll_builder.current_pos = pos + size
        ll_builder.copy_raw_to_string(charp, ll_builder.current_buf, pos, size)

    @staticmethod
    @always_inline
    def ll_getlength(ll_builder):
        num_chars_missing_from_last_piece = (
            ll_builder.current_end - ll_builder.current_pos)
        return ll_builder.total_size - num_chars_missing_from_last_piece

    @classmethod
    def ll_build(cls, ll_builder):
        if not ll_builder.extra_pieces:
            # fast-path: the result fits in a single buf.
            final_size = ll_builder.current_pos
            buf = ll_builder.current_buf
            if ll_builder.total_size != final_size:
                ll_assert(final_size < ll_builder.total_size,
                          "final_size > ll_builder.total_size?")
                buf = rgc.ll_shrink_array(buf, final_size)
                ll_builder.current_buf = buf
                ll_builder.current_end = final_size
                ll_builder.total_size = final_size
            return buf
        else:
            return BaseStringBuilderRepr._ll_build_extra(cls, ll_builder)

    @staticmethod
    @jit.dont_look_inside
    def _ll_build_extra(cls, ll_builder):
        final_size = cls.ll_getlength(ll_builder)
        ll_assert(final_size >= 0, "negative final_size")
        extra = ll_builder.extra_pieces
        ll_builder.extra_pieces = lltype.nullptr(STRINGPIECE)
        #
        result = cls.mallocfn(final_size)
        piece = ll_builder.current_buf
        piece_lgt = ll_builder.current_pos
        ll_assert(ll_builder.current_end == len(piece.chars),
                  "bogus last piece_lgt")
        ll_builder.total_size = final_size
        ll_builder.current_buf = result
        ll_builder.current_pos = final_size
        ll_builder.current_end = final_size

        dst = final_size
        while True:
            dst -= piece_lgt
            ll_assert(dst >= 0, "rbuilder build: overflow")
            ll_builder.copy_string_contents(piece, result, 0, dst, piece_lgt)
            if not extra:
                break
            piece = extra.buf
            piece_lgt = len(piece.chars)
            extra = extra.prev_piece
        ll_assert(dst == 0, "rbuilder build: underflow")
        return result

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
