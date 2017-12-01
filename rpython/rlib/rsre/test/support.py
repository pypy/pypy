import sys, random
from rpython.rlib import debug
from rpython.rlib.rsre.rsre_core import _adjust, match_context
from rpython.rlib.rsre.rsre_core import StrMatchContext, EndOfString


class Position(object):
    def __init__(self, p):
        assert isinstance(p, int)
        if p < 0:
            raise debug.NegativeArgumentNotAllowed(
                "making a Position with byte index %r" % p)
        self._p = p
    def __repr__(self):
        return '<Position %d>' % (self._p)
    def __cmp__(self, other):
        if not isinstance(other, (Position, MinusOnePosition)):
            raise TypeError("cannot compare %r with %r" % (self, other))
        return cmp(self._p, other._p)

class MinusOnePosition(object):
    _p = -1
    def __repr__(self):
        return '<MinusOnePosition>'
    def __cmp__(self, other):
        if not isinstance(other, (Position, MinusOnePosition)):
            raise TypeError("cannot compare %r with %r" % (self, other))
        return cmp(self._p, other._p)


class MatchContextForTests(StrMatchContext):
    """Concrete subclass for matching in a plain string, tweaked for tests"""

    ZERO = Position(0)
    MINUS1 = MinusOnePosition()
    EXACT_DISTANCE = False

    def next(self, position):
        assert isinstance(position, Position)
        return Position(position._p + 1)

    def prev_or_minus1(self, position):
        assert isinstance(position, Position)
        if position._p == 0:
            return self.MINUS1
        return Position(position._p - 1)

    def next_n(self, position, n, end_position):
        assert isinstance(position, Position)
        assert isinstance(end_position, Position)
        assert position._p <= end_position._p
        r = position._p + n
        if r > end_position._p:
            raise EndOfString
        return Position(r)

    def prev_n(self, position, n, start_position):
        assert isinstance(position, Position)
        assert isinstance(start_position, Position)
        assert position._p >= start_position._p
        r = position._p - n
        if r < start_position._p:
            raise EndOfString
        return Position(r)

    def slowly_convert_byte_pos_to_index(self, position):
        assert isinstance(position, Position)
        return position._p

    def str(self, position):
        assert isinstance(position, Position)
        return ord(self._string[position._p])

    def debug_check_pos(self, position):
        assert isinstance(position, Position)

    #def minimum_distance(self, position_low, position_high):
    #    """Return an estimate.  The real value may be higher."""
    #    assert isinstance(position_low, Position)
    #    assert isinstance(position_high, Position)
    #    dist = position_high._p - position_low._p
    #    if dist == 0:
    #        return 0
    #    return random.randrange(1, dist + 1)

    def maximum_distance(self, position_low, position_high):
        """Return an estimate.  The real value may be lower."""
        assert isinstance(position_low, Position)
        assert isinstance(position_high, Position)
        return position_high._p - position_low._p + random.randrange(0, 10)


def match(pattern, string, start=0, end=sys.maxint, flags=0, fullmatch=False):
    start, end = _adjust(start, end, len(string))
    start = Position(start)
    end = Position(end)
    ctx = MatchContextForTests(pattern, string, start, end, flags)
    ctx.fullmatch_only = fullmatch
    if match_context(ctx):
        return ctx
    else:
        return None
