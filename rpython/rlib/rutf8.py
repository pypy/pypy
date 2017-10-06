""" This file is about supporting unicode strings in RPython,
represented by a byte string that is exactly the UTF-8 version
(for some definition of UTF-8).

This doesn't support Python 2's unicode characters beyond 0x10ffff,
which are theoretically possible to obtain using strange tricks like
the array or ctypes modules.

Fun comes from surrogates.  Various functions don't normally accept
any unicode character betwen 0xd800 and 0xdfff, but do if you give
the 'allow_surrogates = True' flag.

This is a minimal reference implementation.  A lot of interpreters
need their own copy-pasted copy of some of the logic here, with
extra code in the middle for error handlers and so on.
"""

from rpython.rlib.objectmodel import enforceargs
from rpython.rlib.rstring import StringBuilder
from rpython.rlib import jit
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rtyper.lltypesystem import lltype


def unichr_as_utf8(code, allow_surrogates=False):
    """Encode code (numeric value) as utf8 encoded string
    """
    code = r_uint(code)
    if code <= r_uint(0x7F):
        # Encode ASCII
        return chr(code)
    if code <= r_uint(0x07FF):
        return chr((0xc0 | (code >> 6))) + chr((0x80 | (code & 0x3f)))
    if code <= r_uint(0xFFFF):
        if not allow_surrogates and 0xD800 <= code <= 0xDfff:
            raise ValueError
        return (chr((0xe0 | (code >> 12))) +
                chr((0x80 | ((code >> 6) & 0x3f))) +
                chr((0x80 | (code & 0x3f))))
    if code <= r_uint(0x10FFFF):
        return (chr((0xf0 | (code >> 18))) +
                chr((0x80 | ((code >> 12) & 0x3f))) +
                chr((0x80 | ((code >> 6) & 0x3f))) +
                chr((0x80 | (code & 0x3f))))
    raise ValueError

def unichr_as_utf8_append(builder, code, allow_surrogates=False):
    """Encode code (numeric value) as utf8 encoded string
    and emit the result into the given StringBuilder.
    """
    code = r_uint(code)
    if code <= r_uint(0x7F):
        # Encode ASCII
        builder.append(chr(code))
        return
    if code <= r_uint(0x07FF):
        builder.append(chr((0xc0 | (code >> 6))))
        builder.append(chr((0x80 | (code & 0x3f))))
        return
    if code <= r_uint(0xFFFF):
        if not allow_surrogates and 0xd800 <= code <= 0xdfff:
            raise ValueError
        builder.append(chr((0xe0 | (code >> 12))))
        builder.append(chr((0x80 | ((code >> 6) & 0x3f))))
        builder.append(chr((0x80 | (code & 0x3f))))
        return
    if code <= r_uint(0x10FFFF):
        builder.append(chr((0xf0 | (code >> 18))))
        builder.append(chr((0x80 | ((code >> 12) & 0x3f))))
        builder.append(chr((0x80 | ((code >> 6) & 0x3f))))
        builder.append(chr((0x80 | (code & 0x3f))))
        return
    raise ValueError

# note - table lookups are really slow. Measured on various elements of obama
#        chinese wikipedia, they're anywhere between 10% and 30% slower.
#        In extreme cases (small, only chinese text), they're 40% slower

def next_codepoint_pos(code, pos):
    """Gives the position of the next codepoint after pos.
    Assumes valid utf8.  'pos' must be before the end of the string.
    """
    chr1 = ord(code[pos])
    assert pos >= 0
    if chr1 <= 0x7F:
        return pos + 1
    if chr1 <= 0xDF:
        return pos + 2
    if chr1 <= 0xEF:
        return pos + 3
    return pos + 4

def prev_codepoint_pos(code, pos):
    """Gives the position of the previous codepoint.
    'pos' must not be zero.
    """
    pos -= 1 # ruint
    if pos >= len(code):     # for the case where pos - 1 == len(code):
        assert pos >= 0
        return pos           # assume there is an extra '\x00' character
    chr1 = ord(code[pos])
    if chr1 <= 0x7F:
        assert pos >= 0
        return pos
    pos -= 1
    if ord(code[pos]) >= 0xC0:
        assert pos >= 0
        return pos
    pos -= 1
    if ord(code[pos]) >= 0xC0:
        assert pos >= 0
        return pos
    pos -= 1
    assert pos >= 0
    return pos

def compute_length_utf8(s):
    continuation_bytes = 0
    for i in range(len(s)):
        if 0x80 <= ord(s[i]) <= 0xBF:    # count the continuation bytes
            continuation_bytes += 1
    return len(s) - continuation_bytes

def codepoint_at_pos(code, pos):
    """ Give a codepoint in code at pos - assumes valid utf8, no checking!
    """
    ordch1 = ord(code[pos])
    if ordch1 <= 0x7F:
        return ordch1

    ordch2 = ord(code[pos+1])
    if ordch1 <= 0xDF:
        # 110yyyyy 10zzzzzz -> 00000000 00000yyy yyzzzzzz
        return (((ordch1 & 0x1F) << 6) +    # 0b00011111
                 (ordch2 & 0x3F))           # 0b00111111

    ordch3 = ord(code[pos+2])
    if ordch1 <= 0xEF:
        # 1110xxxx 10yyyyyy 10zzzzzz -> 00000000 xxxxyyyy yyzzzzzz
        return (((ordch1 & 0x0F) << 12) +     # 0b00001111
                ((ordch2 & 0x3F) << 6) +      # 0b00111111
                (ordch3 & 0x3F))              # 0b00111111

    ordch4 = ord(code[pos+3])
    if True:
        # 11110www 10xxxxxx 10yyyyyy 10zzzzzz -> 000wwwxx xxxxyyyy yyzzzzzz
        return (((ordch1 & 0x07) << 18) +      # 0b00000111
                ((ordch2 & 0x3F) << 12) +      # 0b00111111
                ((ordch3 & 0x3F) << 6) +       # 0b00111111
                (ordch4 & 0x3F))               # 0b00111111
    assert False, "unreachable"

def codepoint_before_pos(code, pos):
    """Give a codepoint in code at the position immediately before pos
    - assumes valid utf8, no checking!
    """
    pos = r_uint(pos)
    ordch1 = ord(code[pos-1])
    if ordch1 <= 0x7F:
        return ordch1

    ordch2 = ordch1
    ordch1 = ord(code[pos-2])
    if ordch1 >= 0xC0:
        # 110yyyyy 10zzzzzz -> 00000000 00000yyy yyzzzzzz
        return (((ordch1 & 0x1F) << 6) +    # 0b00011111
                 (ordch2 & 0x3F))           # 0b00111111

    ordch3 = ordch2
    ordch2 = ordch1
    ordch1 = ord(code[pos-3])
    if ordch1 >= 0xC0:
        # 1110xxxx 10yyyyyy 10zzzzzz -> 00000000 xxxxyyyy yyzzzzzz
        return (((ordch1 & 0x0F) << 12) +     # 0b00001111
                ((ordch2 & 0x3F) << 6) +      # 0b00111111
                (ordch3 & 0x3F))              # 0b00111111

    ordch4 = ordch3
    ordch3 = ordch2
    ordch2 = ordch1
    ordch1 = ord(code[pos-4])
    if True:
        # 11110www 10xxxxxx 10yyyyyy 10zzzzzz -> 000wwwxx xxxxyyyy yyzzzzzz
        return (((ordch1 & 0x07) << 18) +      # 0b00000111
                ((ordch2 & 0x3F) << 12) +      # 0b00111111
                ((ordch3 & 0x3F) << 6) +       # 0b00111111
                (ordch4 & 0x3F))               # 0b00111111
    assert False, "unreachable"

class CheckError(Exception):
    def __init__(self, pos):
        self.pos = pos

#@jit.elidable
def check_ascii(s):
    for i in range(len(s)):
        if ord(s[i]) > 0x7F:
            raise CheckError(i)

def islinebreak(s, pos):
    chr1 = ord(s[pos])
    if 0xa <= chr1 <= 0xd:
        return True
    if 0x1c <= chr1 <= 0x1e:
        return True
    if chr1 == 0xc2:
        chr2 = ord(s[pos + 1])
        return chr2 == 0x85
    elif chr1 == 0xe2:
        chr2 = ord(s[pos + 1])
        if chr2 != 0x80:
            return False
        chr3 = ord(s[pos + 2])
        return chr3 == 0xa8 or chr3 == 0xa9
    return False

def isspace(s, pos):
    chr1 = ord(s[pos])
    if (chr1 == ord(' ') or chr1 == ord('\n') or chr1 == ord('\t') or
        chr1 == ord('\r')):
        return True # common
    if chr1 == 0x0b or chr1 == 0x0c or (chr1 >= 0x1c and chr1 <= 0x1f):
        return True # less common
    if chr1 < 0x80:
        return False
    # obscure cases
    chr2 = ord(s[pos + 1])
    if chr1 == 0xc2:
        return chr2 == 0x85 or chr2 == 0xa0
    if chr1 == 0xe2:
        if chr2 == 0x81 and s[pos + 2] == '\x9f':
            return True
        if chr2 != 0x80:
            return False
        chr3 = ord(s[pos + 2])
        if chr3 >= 0x80 and chr3 <= 0x8a:
            return True
        if chr3 == 0xa9 or chr3 == 0xa8 or chr3 == 0xaf:
            return True
        return False
    if chr1 == 0xe1:
        chr3 = ord(s[pos + 2])
        if chr2 == 0x9a and chr3 == 0x80:
            return True
        if chr2 == 0xa0 and chr3 == 0x8e:
            return True
        return False
    if chr1 == 0xe3 and chr2 == 0x80 and s[pos + 2] == '\x80':
        return True
    return False

def utf8_in_chars(value, pos, chars):
    """Equivalent of u'x' in u'xyz', where the left-hand side is
    a single UTF-8 character extracted from the string 'value' at 'pos'.
    Only works if both 'value' and 'chars' are correctly-formed UTF-8
    strings.
    """
    end = next_codepoint_pos(value, pos)
    i = 0
    while i < len(chars):
        k = pos
        while value[k] == chars[i]:
            k += 1
            i += 1
            if k == end:
                return True
        i += 1
    return False


def _invalid_cont_byte(ordch):
    return ordch>>6 != 0x2    # 0b10

_invalid_byte_2_of_2 = _invalid_cont_byte
_invalid_byte_3_of_3 = _invalid_cont_byte
_invalid_byte_3_of_4 = _invalid_cont_byte
_invalid_byte_4_of_4 = _invalid_cont_byte

@enforceargs(allow_surrogates=bool)
def _invalid_byte_2_of_3(ordch1, ordch2, allow_surrogates):
    return (ordch2>>6 != 0x2 or    # 0b10
            (ordch1 == 0xe0 and ordch2 < 0xa0)
            # surrogates shouldn't be valid UTF-8!
            or (ordch1 == 0xed and ordch2 > 0x9f and not allow_surrogates))

def _invalid_byte_2_of_4(ordch1, ordch2):
    return (ordch2>>6 != 0x2 or    # 0b10
            (ordch1 == 0xf0 and ordch2 < 0x90) or
            (ordch1 == 0xf4 and ordch2 > 0x8f))


#@jit.elidable
def check_utf8(s, allow_surrogates=False):
    """Check that 's' is a utf-8-encoded byte string.
    Returns the length (number of chars) or raise CheckError.
    Note that surrogates are not handled specially here.
    """
    import pdb
    pdb.set_trace()
    pos = 0
    continuation_bytes = 0
    while pos < len(s):
        ordch1 = ord(s[pos])
        pos += 1
        # fast path for ASCII
        if ordch1 <= 0x7F:
            continue

        if ordch1 <= 0xC1:
            raise CheckError(pos - 1)

        if ordch1 <= 0xDF:
            if pos >= len(s):
                raise CheckError(pos - 1)
            ordch2 = ord(s[pos])
            pos += 1

            if _invalid_byte_2_of_2(ordch2):
                raise CheckError(pos - 2)
            # 110yyyyy 10zzzzzz -> 00000000 00000yyy yyzzzzzz
            continuation_bytes += 1
            continue

        if ordch1 <= 0xEF:
            if (pos + 2) > len(s):
                raise CheckError(pos - 1)
            ordch2 = ord(s[pos])
            ordch3 = ord(s[pos + 1])
            pos += 2

            if (_invalid_byte_2_of_3(ordch1, ordch2, allow_surrogates) or
                _invalid_byte_3_of_3(ordch3)):
                raise CheckError(pos - 3)
            # 1110xxxx 10yyyyyy 10zzzzzz -> 00000000 xxxxyyyy yyzzzzzz
            continuation_bytes += 2
            continue

        if ordch1 <= 0xF4:
            if (pos + 3) > len(s):
                raise CheckError(pos - 1)
            ordch2 = ord(s[pos])
            ordch3 = ord(s[pos + 1])
            ordch4 = ord(s[pos + 2])
            pos += 3

            if (_invalid_byte_2_of_4(ordch1, ordch2) or
                _invalid_byte_3_of_4(ordch3) or
                _invalid_byte_4_of_4(ordch4)):
                raise CheckError(pos - 4)
            # 11110www 10xxxxxx 10yyyyyy 10zzzzzz -> 000wwwxx xxxxyyyy yyzzzzzz
            continuation_bytes += 3
            continue

        raise CheckError(pos - 1)

    assert pos == len(s)
    return pos - continuation_bytes

@jit.elidable
def surrogate_in_utf8(value):
    """Check if the UTF-8 byte string 'value' contains a surrogate.
    The 'value' argument must be otherwise correctly formed for UTF-8.
    """
    for i in range(len(value) - 2):
        if value[i] == '\xed' and value[i + 1] >= '\xa0':
            return True
    return False


UTF8_INDEX_STORAGE = lltype.GcArray(lltype.Struct(
    'utf8_loc',
    ('baseindex', lltype.Signed),
    ('ofs', lltype.FixedSizeArray(lltype.Char, 16))
    ))

ASCII_INDEX_STORAGE_BLOCKS = 5
ASCII_INDEX_STORAGE = lltype.malloc(UTF8_INDEX_STORAGE,
                                    ASCII_INDEX_STORAGE_BLOCKS,
                                    immortal=True)
for _i in range(ASCII_INDEX_STORAGE_BLOCKS):
    ASCII_INDEX_STORAGE[_i].baseindex = _i * 64
    for _j in range(16):
        ASCII_INDEX_STORAGE[_i].ofs[_j] = chr(_j * 4 + 1)

def null_storage():
    return lltype.nullptr(UTF8_INDEX_STORAGE)

def create_utf8_index_storage(utf8, utf8len):
    """ Create an index storage which stores index of each 4th character
    in utf8 encoded unicode string.
    """
    if len(utf8) == utf8len < ASCII_INDEX_STORAGE_BLOCKS * 64:
        return ASCII_INDEX_STORAGE
    arraysize = utf8len // 64 + 1
    storage = lltype.malloc(UTF8_INDEX_STORAGE, arraysize)
    baseindex = 0
    current = 0
    while True:
        storage[current].baseindex = baseindex
        next = baseindex
        for i in range(16):
            if utf8len == 0:
                next += 1      # assume there is an extra '\x00' character
            else:
                next = next_codepoint_pos(utf8, next)
            storage[current].ofs[i] = chr(next - baseindex)
            utf8len -= 4
            if utf8len < 0:
                assert current + 1 == len(storage)
                break
            next = next_codepoint_pos(utf8, next)
            next = next_codepoint_pos(utf8, next)
            next = next_codepoint_pos(utf8, next)
        else:
            current += 1
            baseindex = next
            continue
        break
    return storage

@jit.dont_look_inside
def codepoint_position_at_index(utf8, storage, index):
    """ Return byte index of a character inside utf8 encoded string, given
    storage of type UTF8_INDEX_STORAGE.  The index must be smaller than
    the utf8 length: if needed, check explicitly before calling this
    function.
    """
    current = index >> 6
    ofs = ord(storage[current].ofs[(index >> 2) & 0x0F])
    bytepos = storage[current].baseindex + ofs
    index &= 0x3
    if index == 0:
        return prev_codepoint_pos(utf8, bytepos)
    elif index == 1:
        assert bytepos >= 0
        return bytepos
    elif index == 2:
        return next_codepoint_pos(utf8, bytepos)
    else:
        return next_codepoint_pos(utf8, next_codepoint_pos(utf8, bytepos))

@jit.dont_look_inside
def codepoint_at_index(utf8, storage, index):
    """ Return codepoint of a character inside utf8 encoded string, given
    storage of type UTF8_INDEX_STORAGE
    """
    current = index >> 6
    ofs = ord(storage[current].ofs[(index >> 2) & 0x0F])
    bytepos = storage[current].baseindex + ofs
    index &= 0x3
    if index == 0:
        return codepoint_before_pos(utf8, bytepos)
    if index == 3:
        bytepos = next_codepoint_pos(utf8, bytepos)
        index = 2     # fall-through to the next case
    if index == 2:
        bytepos = next_codepoint_pos(utf8, bytepos)
    return codepoint_at_pos(utf8, bytepos)
