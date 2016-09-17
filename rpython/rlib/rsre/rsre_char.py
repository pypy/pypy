"""
Character categories and charsets.
"""
import sys
from rpython.rlib.rlocale import tolower, isalnum
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib import jit
from rpython.rlib.rarithmetic import int_between

# Note: the unicode parts of this module require you to call
# rsre_char.set_unicode_db() first, to select one of the modules
# pypy.module.unicodedata.unicodedb_x_y_z.  This allows PyPy to use sre
# with the same version of the unicodedb as it uses for
# unicodeobject.py.  If unset, the RPython program cannot use unicode
# matching.

unicodedb = None       # possibly patched by set_unicode_db()

def set_unicode_db(newunicodedb):
    global unicodedb
    unicodedb = newunicodedb


#### Constants

if sys.maxint > 2**32:
    MAXREPEAT = int(2**32 - 1)
    MAXGROUPS = int(2**31 - 1)
else:
    MAXREPEAT = int(2**31 - 1)
    MAXGROUPS = int((2**31 / sys.maxint / 2) - 1)

# In _sre.c this is bytesize of the code word type of the C implementation.
# There it's 2 for normal Python builds and more for wide unicode builds (large
# enough to hold a 32-bit UCS-4 encoded character). Since here in pure Python
# we only see re bytecodes as Python longs, we shouldn't have to care about the
# codesize. But sre_compile will compile some stuff differently depending on the
# codesize (e.g., charsets).
from rpython.rlib.runicode import MAXUNICODE
if MAXUNICODE == 65535:
    CODESIZE = 2
else:
    CODESIZE = 4

copyright = "_sre.py 2.4 Copyright 2005 by Nik Haldimann"

BIG_ENDIAN = sys.byteorder == "big"

# XXX can we import those safely from sre_constants?
SRE_INFO_PREFIX = 1
SRE_INFO_LITERAL = 2
SRE_INFO_CHARSET = 4
SRE_FLAG_LOCALE = 4 # honour system locale
SRE_FLAG_UNICODE = 32 # use unicode locale


def getlower(char_ord, flags):
    if flags & SRE_FLAG_LOCALE:
        if char_ord < 256:      # cheating!  Well, CPython does too.
            char_ord = tolower(char_ord)
        return char_ord
    elif flags & SRE_FLAG_UNICODE:
        assert unicodedb is not None
        char_ord = unicodedb.tolower(char_ord)
    else:
        if int_between(ord('A'), char_ord, ord('Z') + 1):   # ASCII lower
            char_ord += ord('a') - ord('A')
    return char_ord

#### Category helpers

is_a_word = [(chr(i).isalnum() or chr(i) == '_') for i in range(256)]
linebreak = ord("\n")
underline = ord("_")

def is_digit(code):
    return int_between(48, code, 58)

def is_uni_digit(code):
    assert unicodedb is not None
    return unicodedb.isdecimal(code)

def is_space(code):
    return (code == 32) | int_between(9, code, 14)

def is_uni_space(code):
    assert unicodedb is not None
    return unicodedb.isspace(code)

def is_word(code):
    assert code >= 0
    return code < 256 and is_a_word[code]

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
                return not result # XXX this might lead to a guard
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

@jit.unroll_safe
def check_charset(pattern, ppos, char_code):
    """Checks whether a character matches set of arbitrary length.
    The set starts at pattern[ppos]."""
    negated = False
    result = False
    while True:
        opcode = pattern[ppos]
        for i, function in set_dispatch_unroll:
            if opcode == i:
                newresult, ppos = function(pattern, ppos, char_code)
                result |= newresult
                break
        else:
            if opcode == 0: # FAILURE
                break
            elif opcode == 26:   # NEGATE
                negated ^= True
                ppos += 1
            else:
                return False
    if negated:
        return not result
    return result

def set_literal(pat, index, char_code):
    # <LITERAL> <code>
    match = pat[index+1] == char_code
    return match, index + 2

def set_category(pat, index, char_code):
    # <CATEGORY> <code>
    match = category_dispatch(pat[index+1], char_code)
    return match, index + 2

def set_charset(pat, index, char_code):
    # <CHARSET> <bitmap> (16 bits per code word)
    if CODESIZE == 2:
        match = char_code < 256 and \
                (pat[index+1+(char_code >> 4)] & (1 << (char_code & 15)))
        return match, index + 17  # skip bitmap
    else:
        match = char_code < 256 and \
                (pat[index+1+(char_code >> 5)] & (1 << (char_code & 31)))
        return match, index + 9   # skip bitmap

def set_range(pat, index, char_code):
    # <RANGE> <lower> <upper>
    match = int_between(pat[index+1], char_code, pat[index+2] + 1)
    return match, index + 3

def set_bigcharset(pat, index, char_code):
    # <BIGCHARSET> <blockcount> <256 blockindices> <blocks>
    count = pat[index+1]
    index += 2

    if CODESIZE == 2:
        # One bytecode is 2 bytes, so contains 2 of the blockindices.
        # So the 256 blockindices are packed in 128 bytecodes, but
        # we need to unpack it as a byte.
        assert char_code < 65536
        shift = 4
    else:
        # One bytecode is 4 bytes, so contains 4 of the blockindices.
        # So the 256 blockindices are packed in 64 bytecodes, but
        # we need to unpack it as a byte.
        if char_code >= 65536:
            index += 256 / CODESIZE + count * (32 / CODESIZE)
            return False, index
        shift = 5

    block = pat[index + (char_code >> (shift + 5))]

    block_shift = char_code >> 5
    if BIG_ENDIAN:
        block_shift = ~block_shift
    block_shift &= (CODESIZE - 1) * 8
    block = (block >> block_shift) & 0xFF

    index += 256 / CODESIZE
    block_value = pat[index+(block * (32 / CODESIZE)
                             + ((char_code & 255) >> shift))]
    match = (block_value & (1 << (char_code & ((8 * CODESIZE) - 1))))
    index += count * (32 / CODESIZE)  # skip blocks
    return match, index

def set_unicode_general_category(pat, index, char_code):
    # Unicode "General category property code" (not used by Python).
    # A general category is two letters.  'pat[index+1]' contains both
    # the first character, and the second character shifted by 8.
    # http://en.wikipedia.org/wiki/Unicode_character_property#General_Category
    # Also supports single-character categories, if the second character is 0.
    # Negative matches are triggered by bit number 7.
    assert unicodedb is not None
    cat = unicodedb.category(char_code)
    category_code = pat[index + 1]
    first_character = category_code & 0x7F
    second_character = (category_code >> 8) & 0x7F
    negative_match = category_code & 0x80
    #
    if second_character == 0:
        # single-character match
        check = ord(cat[0])
        expected = first_character
    else:
        # two-characters match
        check = ord(cat[0]) | (ord(cat[1]) << 8)
        expected = first_character | (second_character << 8)
    #
    if negative_match:
        result = check != expected
    else:
        result = check == expected
    #
    return result, index + 2

set_dispatch_table = {
    9: set_category,
    10: set_charset,
    11: set_bigcharset,
    19: set_literal,
    27: set_range,
    70: set_unicode_general_category,
}
set_dispatch_unroll = unrolling_iterable(sorted(set_dispatch_table.items()))
