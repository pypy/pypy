"""
Character categories and charsets.
"""
import sys
from pypy.rlib.rsre._rsre_platform import tolower, isalnum
from pypy.rlib.unroll import unrolling_iterable

# Note: the unicode parts of this module require you to call
# rsre.set_unicode_db() first, to select one of the modules
# pypy.module.unicodedata.unicodedb_x_y_z.  This allows PyPy to use sre
# with the same version of the unicodedb as it uses for
# unicodeobject.py.  If unset, the RPython program cannot use unicode
# matching.

unicodedb = None       # possibly patched by rsre.set_unicode_db()


#### Constants

# Identifying as _sre from Python 2.3 or 2.4
MAGIC = 20031017

# In _sre.c this is bytesize of the code word type of the C implementation.
# There it's 2 for normal Python builds and more for wide unicode builds (large 
# enough to hold a 32-bit UCS-4 encoded character). Since here in pure Python
# we only see re bytecodes as Python longs, we shouldn't have to care about the
# codesize. But sre_compile will compile some stuff differently depending on the
# codesize (e.g., charsets).
from pypy.rlib.runicode import MAXUNICODE
if MAXUNICODE == 65535:
    CODESIZE = 2
else:
    CODESIZE = 4

copyright = "_sre.py 2.4 Copyright 2005 by Nik Haldimann"

BIG_ENDIAN = sys.byteorder == "big"

# XXX can we import those safely from sre_constants?
SRE_INFO_PREFIX = 1
SRE_INFO_LITERAL = 2
SRE_FLAG_LOCALE = 4 # honour system locale
SRE_FLAG_UNICODE = 32 # use unicode locale
OPCODE_INFO = 17
OPCODE_LITERAL = 19
MAXREPEAT = 65535


def getlower(char_ord, flags):
    if flags & SRE_FLAG_UNICODE:
        assert unicodedb is not None
        char_ord = unicodedb.tolower(char_ord)
    elif flags & SRE_FLAG_LOCALE:
        return tolower(char_ord)
    else:
        if ord('A') <= char_ord <= ord('Z'):   # ASCII lower
            char_ord += ord('a') - ord('A')
    return char_ord


class MatchContextBase(object):

    UNDECIDED = 0
    MATCHED = 1
    NOT_MATCHED = 2

    def peek_code(self, peek=0):
        return self.pattern_codes[self.code_position + peek]

    def skip_code(self, skip_count):
        self.code_position = self.code_position + skip_count

    def has_remaining_codes(self):
        return len(self.pattern_codes) != self.code_position


#### Category helpers

ascii_char_info = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 6, 2,
2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0,
0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 25, 25, 25, 25, 25, 25, 25, 25,
25, 25, 0, 0, 0, 0, 0, 0, 0, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24,
24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 0, 0,
0, 0, 16, 0, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24,
24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 0, 0, 0, 0, 0 ]

linebreak = ord("\n")
underline = ord("_")

def is_digit(code):
    return code < 128 and (ascii_char_info[code] & 1 != 0)

def is_uni_digit(code):
    assert unicodedb is not None
    return unicodedb.isdigit(code)

def is_space(code):
    return code < 128 and (ascii_char_info[code] & 2 != 0)

def is_uni_space(code):
    assert unicodedb is not None
    return unicodedb.isspace(code)

def is_word(code):
    return code < 128 and (ascii_char_info[code] & 16 != 0)

def is_uni_word(code):
    assert unicodedb is not None
    return unicodedb.isalnum(code) or code == underline

def is_loc_alnum(code):
    return code < 256 and isalnum(code)

def is_loc_word(code):
    return code == underline or is_loc_alnum(code)

def is_linebreak(code):
    return code == linebreak

def is_uni_linebreak(code):
    assert unicodedb is not None
    return unicodedb.islinebreak(code)


#### Category dispatch

def category_dispatch(category_code, char_code):
    i = 0
    for function, negate in category_dispatch_unroll:
        if category_code == i:
            result = function(char_code)
            if negate:
                return not result
            else:
                return result
        i = i + 1
    else:
        return False

# Maps opcodes by indices to (function, negate) tuples.
category_dispatch_table = [
    (is_digit, False), (is_digit, True), (is_space, False),
    (is_space, True), (is_word, False), (is_word, True),
    (is_linebreak, False), (is_linebreak, True), (is_loc_word, False),
    (is_loc_word, True), (is_uni_digit, False), (is_uni_digit, True),
    (is_uni_space, False), (is_uni_space, True), (is_uni_word, False),
    (is_uni_word, True), (is_uni_linebreak, False),
    (is_uni_linebreak, True)
]
category_dispatch_unroll = unrolling_iterable(category_dispatch_table)

##### Charset evaluation

SET_OK = -1
SET_NOT_OK = -2

def check_charset(char_code, context):
    """Checks whether a character matches set of arbitrary length. Currently
    assumes the set starts at the first member of pattern_codes."""
    pattern_codes = context.pattern_codes
    index = context.code_position
    negated = SET_OK
    while index >= 0:
        opcode = pattern_codes[index]
        i = 0
        for function in set_dispatch_unroll:
            if function is not None and opcode == i:
                index = function(pattern_codes, index, char_code)
                break
            i = i + 1
        else:
            if opcode == 26:   # NEGATE
                negated ^= (SET_OK ^ SET_NOT_OK)
                index += 1
            else:
                return False
    return index == negated

def set_failure(pat, index, char_code):
    return SET_NOT_OK

def set_literal(pat, index, char_code):
    # <LITERAL> <code>
    if pat[index+1] == char_code:
        return SET_OK
    else:
        return index + 2

def set_category(pat, index, char_code):
    # <CATEGORY> <code>
    if category_dispatch(pat[index+1], char_code):
        return SET_OK
    else:
        return index + 2

def set_charset(pat, index, char_code):
    # <CHARSET> <bitmap> (16 bits per code word)
    if CODESIZE == 2:
        if char_code < 256 and pat[index+1+(char_code >> 4)] \
                                        & (1 << (char_code & 15)):
            return SET_OK
        return index + 17  # skip bitmap
    else:
        if char_code < 256 and pat[index+1+(char_code >> 5)] \
                                        & (1 << (char_code & 31)):
            return SET_OK
        return index + 9   # skip bitmap

def set_range(pat, index, char_code):
    # <RANGE> <lower> <upper>
    if pat[index+1] <= char_code <= pat[index+2]:
        return SET_OK
    return index + 3

def set_bigcharset(pat, index, char_code):
    # <BIGCHARSET> <blockcount> <256 blockindices> <blocks>
    # XXX this function probably needs a makeover
    count = pat[index+1]
    index += 2
    if char_code < 65536:
        block_index = char_code >> 8
        # NB: there are CODESIZE block indices per bytecode
        a = to_byte_array(pat[index+(block_index / CODESIZE)])
        block = a[block_index % CODESIZE]
        index += 256 / CODESIZE  # skip block indices
        if CODESIZE == 2:
            shift = 4
        else:
            shift = 5
        block_value = pat[index+(block * (32 / CODESIZE)
                                 + ((char_code & 255) >> shift))]
        if block_value & (1 << (char_code & ((8 * CODESIZE) - 1))):
            return SET_OK
    else:
        index += 256 / CODESIZE  # skip block indices
    index += count * (32 / CODESIZE)  # skip blocks
    return index

def to_byte_array(int_value):
    """Creates a list of bytes out of an integer representing data that is
    CODESIZE bytes wide."""
    byte_array = [0] * CODESIZE
    for i in range(CODESIZE):
        byte_array[i] = int_value & 0xff
        int_value = int_value >> 8
    if BIG_ENDIAN:
        byte_array.reverse()
    return byte_array

set_dispatch_table = [
    set_failure, None, None, None, None, None, None, None, None,
    set_category, set_charset, set_bigcharset, None, None, None,
    None, None, None, None, set_literal, None, None, None, None,
    None, None,
    None,  # NEGATE
    set_range
]
set_dispatch_unroll = unrolling_iterable(set_dispatch_table)
