"""
Validation of caller-supplied SRE bytecode, as produced e.g. by
re._compiler.py and passed to _sre.compile().  This is a port of
CPython's Modules/_sre/sre.c:_validate() (and helpers), which exists
so that a compiled pattern object can never be built from a bytecode
stream that would make rsre_core's matching engine read or jump out
of bounds.

The 'code' argument throughout is the flat list of ints exactly as
stored on CompiledPattern.pattern (i.e. BEFORE it is wrapped into a
CompiledPattern).  Each element started out as an app-level int that
passed space.uint_w() -- so it is never negative before intmask() is
applied, but intmask() can turn very large values (>= 2**63 on a
64-bit build) into negative host ints.  We use r_uint() everywhere we
need to compare such a value against a small, known-good bound, so
that these wrapped-negative values compare as the huge magnitudes
they actually represent instead of as small (or negative) ones.
"""

from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib.rsre import rsre_constants as consts
from rpython.rlib.rsre.rsre_char import MAXREPEAT, MAXGROUPS, BIG_ENDIAN

NUM_AT_CODES = 12
NUM_CATEGORY_CODES = 18

LITERAL_OPS = (
    consts.OPCODE_LITERAL, consts.OPCODE_NOT_LITERAL,
    consts.OPCODE_LITERAL_IGNORE, consts.OPCODE_NOT_LITERAL_IGNORE,
    consts.OPCODE37_LITERAL_UNI_IGNORE, consts.OPCODE37_NOT_LITERAL_UNI_IGNORE,
    consts.OPCODE37_LITERAL_LOC_IGNORE, consts.OPCODE37_NOT_LITERAL_LOC_IGNORE,
)
GROUPREF_OPS = (
    consts.OPCODE_GROUPREF, consts.OPCODE_GROUPREF_IGNORE,
    consts.OPCODE37_GROUPREF_UNI_IGNORE, consts.OPCODE37_GROUPREF_LOC_IGNORE,
)
IN_OPS = (
    consts.OPCODE_IN, consts.OPCODE_IN_IGNORE,
    consts.OPCODE37_IN_UNI_IGNORE, consts.OPCODE37_IN_LOC_IGNORE,
)


class InvalidSRECode(Exception):
    pass

def _fail():
    raise InvalidSRECode


def _get_op(code, pos, end):
    if pos >= end:
        _fail()
    return code[pos], pos + 1

_get_arg = _get_op

def _get_skip(code, pos, end, adj=0):
    if pos >= end:
        _fail()
    skip = code[pos]
    remaining = end - pos
    if r_uint(skip) - r_uint(adj) > r_uint(remaining):
        _fail()
    return skip, pos + 1


def _bigcharset_blockindex_byte(code, pos, i):
    # Mirrors the block-index lookup done at match time by
    # rsre_char.set_bigcharset(): the 256 block-index bytes are packed
    # 4-per-word (little- or big-endian, following BIG_ENDIAN) starting
    # at 'pos'.  i is in range(256).
    word = code[pos + (i >> 2)]
    shift = (i & 3) * 8
    if BIG_ENDIAN:
        shift = 24 - shift
    return (word >> shift) & 0xFF


def _validate_charset(code, pos, end):
    while pos < end:
        op, pos = _get_op(code, pos, end)
        if op == consts.OPCODE_NEGATE:
            pass
        elif op == consts.OPCODE_LITERAL:
            _, pos = _get_arg(code, pos, end)
        elif op == consts.OPCODE_RANGE or op == consts.OPCODE37_RANGE_UNI_IGNORE:
            _, pos = _get_arg(code, pos, end)
            _, pos = _get_arg(code, pos, end)
        elif op == consts.OPCODE_CHARSET:
            offset = 256 // 32       # 256-bit bitmap
            if offset > end - pos:
                _fail()
            pos += offset
        elif op == consts.OPCODE_BIGCHARSET:
            count, pos = _get_arg(code, pos, end)
            offset1 = 256 // 4        # 256 block-index bytes, 4 per word
            if offset1 > end - pos:
                _fail()
            for i in range(256):
                if r_uint(_bigcharset_blockindex_byte(code, pos, i)) >= r_uint(count):
                    _fail()
            pos += offset1
            # XXX can this overflow?
            offset2 = r_uint(count) * r_uint(32 // 4)
            if offset2 > r_uint(end - pos):
                _fail()
            pos += intmask(offset2)
        elif op == consts.OPCODE_CATEGORY:
            arg, pos = _get_arg(code, pos, end)
            if r_uint(arg) >= r_uint(NUM_CATEGORY_CODES):
                _fail()
        else:
            _fail()
    if pos != end:
        _fail()
    return pos


def _validate_info(code, pos, end):
    skip, pos = _get_skip(code, pos, end)
    newcode = pos + skip - 1
    flags, pos = _get_arg(code, pos, end)
    _, pos = _get_arg(code, pos, end)      # min
    _, pos = _get_arg(code, pos, end)      # max
    allowed = consts.SRE_INFO_PREFIX | consts.SRE_INFO_LITERAL | consts.SRE_INFO_CHARSET
    if flags & ~allowed:
        _fail()
    if (flags & consts.SRE_INFO_PREFIX) and (flags & consts.SRE_INFO_CHARSET):
        _fail()
    if (flags & consts.SRE_INFO_LITERAL) and not (flags & consts.SRE_INFO_PREFIX):
        _fail()
    if flags & consts.SRE_INFO_PREFIX:
        prefix_len, pos = _get_arg(code, pos, end)
        _, pos = _get_arg(code, pos, end)  # overlap table skip (unused here)
        if r_uint(prefix_len) > r_uint(newcode - pos):
            _fail()
        pos += prefix_len
        if r_uint(prefix_len) > r_uint(newcode - pos):
            _fail()
        for i in range(prefix_len):
            if r_uint(code[pos + i]) >= r_uint(prefix_len):
                _fail()
        pos += prefix_len
    if flags & consts.SRE_INFO_CHARSET:
        _validate_charset(code, pos, newcode - 1)
        if code[newcode - 1] != consts.OPCODE_FAILURE:
            _fail()
        pos = newcode
    elif pos != newcode:
        _fail()
    return pos


def _validate_branch(code, pos, end, groups):
    target = -1
    while True:
        skip, pos = _get_skip(code, pos, end)
        if skip == 0:
            break
        armend, ends_jump = _validate_inner(code, pos, pos + skip - 3, groups)
        if ends_jump:
            _fail()
        pos = pos + skip - 3
        op, pos = _get_op(code, pos, end)
        if op != consts.OPCODE_JUMP:
            _fail()
        skip, pos = _get_skip(code, pos, end)
        if target == -1:
            target = pos + skip - 1
        elif pos + skip - 1 != target:
            _fail()
    if pos != target:
        _fail()
    return pos


def _validate_repeat_one(code, pos, end, groups, op):
    skip, pos = _get_skip(code, pos, end)
    min, pos = _get_arg(code, pos, end)
    max, pos = _get_arg(code, pos, end)
    if r_uint(min) > r_uint(max):
        _fail()
    if r_uint(max) > r_uint(MAXREPEAT):
        _fail()
    _, ends_jump = _validate_inner(code, pos, pos + skip - 4, groups)
    if ends_jump:
        _fail()
    pos = pos + skip - 4
    subop, pos = _get_op(code, pos, end)
    if subop != consts.OPCODE_SUCCESS:
        _fail()
    return pos


def _validate_repeat(code, pos, end, groups, op):
    skip, pos = _get_skip(code, pos, end)
    min, pos = _get_arg(code, pos, end)
    max, pos = _get_arg(code, pos, end)
    if r_uint(min) > r_uint(max):
        _fail()
    if r_uint(max) > r_uint(MAXREPEAT):
        _fail()
    _, ends_jump = _validate_inner(code, pos, pos + skip - 3, groups)
    if ends_jump:
        _fail()
    pos = pos + skip - 3
    subop, pos = _get_op(code, pos, end)
    if consts.eq(op, consts.OPCODE_POSSESSIVE_REPEAT):
        if subop != consts.OPCODE_SUCCESS:
            _fail()
    else:
        if subop != consts.OPCODE_MAX_UNTIL and subop != consts.OPCODE_MIN_UNTIL:
            _fail()
    return pos


def _validate_atomic_group(code, pos, end, groups):
    skip, pos = _get_skip(code, pos, end)
    _, ends_jump = _validate_inner(code, pos, pos + skip - 2, groups)
    if ends_jump:
        _fail()
    pos = pos + skip - 2
    subop, pos = _get_op(code, pos, end)
    if subop != consts.OPCODE_SUCCESS:
        _fail()
    return pos


def _validate_groupref_exists(code, pos, end, groups):
    arg, pos = _get_arg(code, pos, end)
    if r_uint(arg) >= r_uint(groups):
        _fail()
    skip, pos = _get_skip(code, pos, end, adj=1)
    base = pos - 1     # 'code--': the skip is relative to the skip field itself
    _, ends_jump = _validate_inner(code, base + 1, base + skip - 1, groups)
    if ends_jump:
        pos = base + skip - 2
        # GET_SKIP again: this reuses/overwrites 'skip', matching sre.c
        skip, pos = _get_skip(code, pos, end)
        _, ends_jump2 = _validate_inner(code, pos, pos + skip - 1, groups)
        if ends_jump2:
            _fail()
    else:
        pos = base
    pos = pos + skip - 1
    return pos


def _validate_assert(code, pos, end, groups):
    skip, pos = _get_skip(code, pos, end)
    _, pos = _get_arg(code, pos, end)   # 0 for lookahead, width for lookbehind
    pos -= 1
    _, ends_jump = _validate_inner(code, pos + 1, pos + skip - 2, groups)
    if ends_jump:
        _fail()
    pos = pos + skip - 2
    subop, pos = _get_op(code, pos, end)
    if subop != consts.OPCODE_SUCCESS:
        _fail()
    return pos


def _validate_inner(code, pos, end, groups):
    # Returns (pos, ends_with_jump).  Mirrors CPython's _validate_inner,
    # which returns -1 (we raise instead), 0, or 1 (last op was JUMP).
    if pos > end:
        _fail()
    while pos < end:
        op, pos = _get_op(code, pos, end)

        if op == consts.OPCODE_MARK:
            arg, pos = _get_arg(code, pos, end)
            if r_uint(arg) > r_uint(2 * groups + 1):
                _fail()

        elif op in LITERAL_OPS:
            _, pos = _get_arg(code, pos, end)

        elif op == consts.OPCODE_SUCCESS or op == consts.OPCODE_FAILURE:
            pass

        elif op == consts.OPCODE_AT:
            arg, pos = _get_arg(code, pos, end)
            if r_uint(arg) >= r_uint(NUM_AT_CODES):
                _fail()

        elif op == consts.OPCODE_ANY or op == consts.OPCODE_ANY_ALL:
            pass

        elif op in IN_OPS:
            skip, pos = _get_skip(code, pos, end)
            _validate_charset(code, pos, pos + skip - 2)
            if code[pos + skip - 2] != consts.OPCODE_FAILURE:
                _fail()
            pos = pos + skip - 1

        elif op == consts.OPCODE_INFO:
            pos = _validate_info(code, pos, end)

        elif op == consts.OPCODE_BRANCH:
            pos = _validate_branch(code, pos, end, groups)

        elif (op == consts.OPCODE_REPEAT_ONE or op == consts.OPCODE_MIN_REPEAT_ONE
              or consts.eq(op, consts.OPCODE_POSSESSIVE_REPEAT_ONE)):
            pos = _validate_repeat_one(code, pos, end, groups, op)

        elif op == consts.OPCODE_REPEAT or consts.eq(op, consts.OPCODE_POSSESSIVE_REPEAT):
            pos = _validate_repeat(code, pos, end, groups, op)

        elif consts.eq(op, consts.OPCODE_ATOMIC_GROUP):
            pos = _validate_atomic_group(code, pos, end, groups)

        elif op in GROUPREF_OPS:
            arg, pos = _get_arg(code, pos, end)
            if r_uint(arg) >= r_uint(groups):
                _fail()

        elif op == consts.OPCODE_GROUPREF_EXISTS:
            pos = _validate_groupref_exists(code, pos, end, groups)

        elif op == consts.OPCODE_ASSERT or op == consts.OPCODE_ASSERT_NOT:
            pos = _validate_assert(code, pos, end, groups)

        elif op == consts.OPCODE_JUMP:
            if pos + 1 != end:
                _fail()
            return pos, True

        else:
            _fail()

    return pos, False


def _validate_outer(code, end, groups):
    if groups < 0 or r_uint(groups) > r_uint(MAXGROUPS):
        _fail()
    if end <= 0 or code[end - 1] != consts.OPCODE_SUCCESS:
        _fail()
    _validate_inner(code, 0, end - 1, groups)


def validate(code, groups):
    """Returns True if 'code' (a list of ints) is a well-formed SRE
    bytecode program for the given number of groups, False otherwise.
    Never raises, never indexes out of the 'code' list's bounds."""
    try:
        _validate_outer(code, len(code), groups)
    except InvalidSRECode:
        return False
    except IndexError:
        # extra safety net: should be unreachable if the bounds checks
        # above are correct, but never let a bug here turn into an
        # unvalidated pattern reaching the matching engine.
        return False
    return True
