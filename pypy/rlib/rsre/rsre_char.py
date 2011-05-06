"""
Character categories and charsets.
"""
import sys
from pypy.rlib.rlocale import tolower, isalnum
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib import jit
from pypy.rlib.rarithmetic import int_between

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

# Identifying as _sre from Python 2.3 and onwards (at least up to 2.7)
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
SRE_INFO_CHARSET = 4
SRE_FLAG_LOCALE = 4 # honour system locale
SRE_FLAG_UNICODE = 32 # use unicode locale
OPCODE_INFO = 17
OPCODE_LITERAL = 19
MAXREPEAT = 65535


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
        i = 0
        for function in set_dispatch_unroll:
            if function is not None and opcode == i:
                newresult, ppos = function(pattern, ppos, char_code)
                result |= newresult
                break
            i = i + 1
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
    # XXX this function needs a makeover, it's very bad
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
        match = (block_value & (1 << (char_code & ((8 * CODESIZE) - 1)))) != 0
    else:
        index += 256 / CODESIZE  # skip block indices
        match = False
    index += count * (32 / CODESIZE)  # skip blocks
    return match, index

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
    None, # FAILURE
    None, None, None, None, None, None, None, None,
    set_category, set_charset, set_bigcharset, None, None, None,
    None, None, None, None, set_literal, None, None, None, None,
    None, None,
    None,  # NEGATE
    set_range
]
set_dispatch_unroll = unrolling_iterable(set_dispatch_table)
