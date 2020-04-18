import sys
from rpython.rlib.debug import check_nonneg
from rpython.rlib.rsre.rsre_core import AbstractMatchContext, EndOfString
from rpython.rlib.rsre import rsre_char
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib import rutf8, jit


class Utf8MatchContext(AbstractMatchContext):
    """A context that matches unicode, but encoded in a utf8 string.
    Be careful because most positions taken by, handled in, and returned
    by this class are expressed in *bytes*, not in characters.
    """

    def __init__(self, utf8string, match_start, end):
        AbstractMatchContext.__init__(self, match_start, end)
        self._utf8 = utf8string

    def str(self, index):
        check_nonneg(index)
        return rutf8.codepoint_at_pos(self._utf8, index)

    def lowstr(self, index, flags):
        c = self.str(index)
        return rsre_char.getlower(c, flags)

    def get_single_byte(self, base_position, index):
        return self._utf8[base_position + index]

    @jit.unroll_safe
    def matches_literal(self, position, ordch):
        # do a bytewise compare against the utf-8 encoded version of ordch
        # this is cheap because ordch is always constant in the trace
        utf8 = rutf8.unichr_as_utf8(ordch, allow_surrogates=True)
        check_nonneg(position)
        for byte in utf8:
            if self._utf8[position] != byte:
                return False
            position += 1
        return True

    @jit.unroll_safe
    def matches_many_literals(self, ptr, pattern, ppos, n):
        assert ppos >= 0
        utf8_size = compute_utf8_size_n_literals(pattern, ppos, n)
        # do a single range check
        if ptr + utf8_size > self.end:
            return -1
        for i in range(n):
            ordch = pattern.pat(ppos + 2 * i + 1)
            if not self.matches_literal(ptr, ordch):
                return -1
            ptr += rutf8.codepoint_size_in_utf8(ordch)
        return ptr

    def next(self, position):
        return rutf8.next_codepoint_pos(self._utf8, position)
    next_indirect = next

    def prev(self, position):
        if position <= 0:
            raise EndOfString
        position = rutf8.prev_codepoint_pos(self._utf8, position)
        assert position >= 0
        return position
    prev_indirect = prev

    @jit.look_inside_iff(lambda self, position, n, end_position: n <= 1)
    def next_n(self, position, n, end_position):
        i = 0
        # avoid range(n) since n can be quite large
        while i < n:
            if position >= end_position:
                raise EndOfString
            position = rutf8.next_codepoint_pos(self._utf8, position)
            i += 1
        return position

    def prev_n(self, position, n, start_position):
        i = 0
        # avoid range(n) since n can be quite large
        while i < n:
            if position <= start_position:
                raise EndOfString
            position = rutf8.prev_codepoint_pos(self._utf8, position)
            i += 1
        assert position >= 0
        return position

    def debug_check_pos(self, position):
        if we_are_translated():
            return
        if position == len(self._utf8):
            return   # end of string is fine
        assert not (0x80 <= self._utf8[position] < 0xC0)   # continuation byte

    def maximum_distance(self, position_low, position_high):
        # may overestimate if there are non-ascii chars
        return position_high - position_low


@jit.elidable
def compute_utf8_size_n_literals(pattern, ppos, n):
    total_size = 0
    for i in range(n):
        ordch = pattern.pat(ppos + 2 * i + 1)
        total_size += rutf8.codepoint_size_in_utf8(ordch)
    return total_size


def make_utf8_ctx(utf8string, bytestart, byteend):
    if bytestart < 0: bytestart = 0
    elif bytestart > len(utf8string): bytestart = len(utf8string)
    if byteend < 0: byteend = 0
    elif byteend > len(utf8string): byteend = len(utf8string)
    ctx = Utf8MatchContext(utf8string, bytestart, byteend)
    ctx.debug_check_pos(bytestart)
    ctx.debug_check_pos(byteend)
    return ctx

def utf8search(pattern, utf8string, bytestart=0, byteend=sys.maxint):
    # bytestart and byteend must be valid byte positions inside the
    # utf8string.
    from rpython.rlib.rsre.rsre_core import search_context

    ctx = make_utf8_ctx(utf8string, bytestart, byteend)
    if search_context(ctx, pattern):
        return ctx
    else:
        return None

def utf8match(pattern, utf8string, bytestart=0, byteend=sys.maxint,
              fullmatch=False):
    # bytestart and byteend must be valid byte positions inside the
    # utf8string.
    from rpython.rlib.rsre.rsre_core import match_context

    ctx = make_utf8_ctx(utf8string, bytestart, byteend)
    ctx.fullmatch_only = fullmatch
    if match_context(ctx, pattern):
        return ctx
    else:
        return None
