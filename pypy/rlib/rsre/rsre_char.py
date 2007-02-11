"""
Character categories and charsets.
"""
import sys

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
if sys.maxunicode == 65535:
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
    # XXX no platform-dependent locale support for now
    if flags & SRE_FLAG_UNICODE:
        char_ord = unicodedb.tolower(char_ord)
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
    return unicodedb.isdigit(code)

def is_space(code):
    return code < 128 and (ascii_char_info[code] & 2 != 0)

def is_uni_space(code):
    return unicodedb.isspace(code)

def is_word(code):
    return code < 128 and (ascii_char_info[code] & 16 != 0)

def is_uni_word(code):
    return unicodedb.isalnum(code) or code == underline

is_loc_word = is_word      # XXX no support for platform locales anyway

def is_linebreak(code):
    return code == linebreak

def is_uni_linebreak(code):
    return unicodedb.islinebreak(code)


#### Category dispatch

def category_dispatch(category_code, char_code):
    try:
        function, negate = category_dispatch_table[category_code]
    except IndexError:
        return False
    result = function(char_code)
    if negate:
        return not result
    else:
        return result

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

##### Charset evaluation

SET_OK = 1
SET_NOT_OK = -1
SET_NOT_FINISHED = 0

def check_charset(char_code, context):
    """Checks whether a character matches set of arbitrary length. Currently
    assumes the set starts at the first member of pattern_codes."""
    result = SET_NOT_FINISHED
    context.set_ok = SET_OK
    backup_code_position = context.code_position
    while result == SET_NOT_FINISHED:
        opcode = context.peek_code()
        try:
            function = set_dispatch_table[opcode]
        except IndexError:
            return False
        result = function(context, char_code)
    context.code_position = backup_code_position
    return result == SET_OK

def set_failure(ctx, char_code):
    return -ctx.set_ok

def set_literal(ctx, char_code):
    # <LITERAL> <code>
    if ctx.peek_code(1) == char_code:
        return ctx.set_ok
    else:
        ctx.skip_code(2)
        return SET_NOT_FINISHED

def set_category(ctx, char_code):
    # <CATEGORY> <code>
    if category_dispatch(ctx.peek_code(1), char_code):
        return ctx.set_ok
    else:
        ctx.skip_code(2)
        return SET_NOT_FINISHED

def set_charset(ctx, char_code):
    # <CHARSET> <bitmap> (16 bits per code word)
    ctx.skip_code(1) # point to beginning of bitmap
    if CODESIZE == 2:
        if char_code < 256 and ctx.peek_code(char_code >> 4) \
                                        & (1 << (char_code & 15)):
            return ctx.set_ok
        ctx.skip_code(16) # skip bitmap
    else:
        if char_code < 256 and ctx.peek_code(char_code >> 5) \
                                        & (1 << (char_code & 31)):
            return ctx.set_ok
        ctx.skip_code(8) # skip bitmap
    return SET_NOT_FINISHED

def set_range(ctx, char_code):
    # <RANGE> <lower> <upper>
    if ctx.peek_code(1) <= char_code <= ctx.peek_code(2):
        return ctx.set_ok
    ctx.skip_code(3)
    return SET_NOT_FINISHED

def set_negate(ctx, char_code):
    ctx.set_ok = -ctx.set_ok
    ctx.skip_code(1)
    return SET_NOT_FINISHED

def set_bigcharset(ctx, char_code):
    # <BIGCHARSET> <blockcount> <256 blockindices> <blocks>
    # XXX this function probably needs a makeover
    count = ctx.peek_code(1)
    ctx.skip_code(2)
    if char_code < 65536:
        block_index = char_code >> 8
        # NB: there are CODESIZE block indices per bytecode
        a = to_byte_array(ctx.peek_code(block_index / CODESIZE))
        block = a[block_index % CODESIZE]
        ctx.skip_code(256 / CODESIZE) # skip block indices
        if CODESIZE == 2:
            shift = 4
        else:
            shift = 5
        block_value = ctx.peek_code(block * (32 / CODESIZE)
                                                + ((char_code & 255) >> shift))
        if block_value & (1 << (char_code & ((8 * CODESIZE) - 1))):
            return ctx.set_ok
    else:
        ctx.skip_code(256 / CODESIZE) # skip block indices
    ctx.skip_code(count * (32 / CODESIZE)) # skip blocks
    return SET_NOT_FINISHED

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
    None, None, set_negate, set_range
]
