from pypy.interpreter.baseobjspace import ObjSpace
# XXX is it allowed to import app-level module like this?
from pypy.module._sre.app_info import CODESIZE
from pypy.module.array.app_array import array

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

# Static list of all unicode codepoints reported by Py_UNICODE_ISLINEBREAK.
# Using a dict as a poor man's set.
uni_linebreaks = {10: True, 13: True, 28: True, 29: True, 30: True, 133: True,
                  8232: True, 8233: True}

def is_digit(space, w_char):
    code = space.int_w(space.ord(w_char))
    return code < 128 and ascii_char_info[code] & 1

def is_uni_digit(space, w_char):
    return space.is_true(space.call_method(w_char, "isdigit"))

def is_space(space, w_char):
    code = space.int_w(space.ord(w_char))
    return code < 128 and ascii_char_info[code] & 2

def is_uni_space(space, w_char):
    return space.is_true(space.call_method(w_char, "isspace"))

def is_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    return code < 128 and ascii_char_info[code] & 16

def is_uni_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    w_unichar = space.newunicode([code])
    isalnum = space.is_true(space.call_method(w_unichar, "isalnum"))
    return isalnum or code == underline

def is_loc_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    if code > 255:
        return False
    # Need to use this new w_char_not_uni from here on, because this one is
    # guaranteed to be not unicode.
    w_char_not_uni = space.wrap(chr(code))
    isalnum = space.is_true(space.call_method(w_char_not_uni, "isalnum"))
    return isalnum or code == underline

def is_linebreak(space, w_char):
    return space.int_w(space.ord(w_char)) == linebreak

def is_uni_linebreak(space, w_char):
    code = space.int_w(space.ord(w_char))
    return uni_linebreaks.has_key(code)


#### Category dispatch

def category_dispatch(space, w_chcode, w_char):
    chcode = space.int_w(w_chcode)
    if chcode >= len(category_dispatch_table):
        return space.newbool(False)
    function, negate = category_dispatch_table[chcode]
    result = function(space, w_char)
    if negate:
        return space.newbool(not result)
    else:
        return space.newbool(result)

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

##### At dispatch

class MatchContext:
    # XXX This is not complete. It's tailored to at dispatch currently.
    
    def __init__(self, space, pattern_codes, w_string, string_position, end):
        self.space = space
        self.pattern_codes = pattern_codes
        self.w_string = w_string
        self.string_position = string_position
        self.end = end
        self.code_position = 0
        self.set_ok = True # XXX maybe get rid of this

    def peek_char(self, peek=0):
        return self.space.getitem(self.w_string,
                                   self.space.wrap(self.string_position + peek))

    def remaining_chars(self):
        return self.end - self.string_position

    def peek_code(self, peek=0):
        return self.pattern_codes[self.code_position + peek]

    def skip_code(self, skip_count):
        self.code_position += skip_count

    def at_beginning(self):
        return self.string_position == 0

    def at_end(self):
        return self.string_position == self.end

    def at_linebreak(self):
        return not self.at_end() and is_linebreak(self.space, self.peek_char())

    def at_boundary(self, word_checker):
        if self.at_beginning() and self.at_end():
            return False
        that = not self.at_beginning() \
                            and word_checker(self.space, self.peek_char(-1))
        this = not self.at_end() \
                            and word_checker(self.space, self.peek_char())
        return this != that

def at_dispatch(space, w_atcode, w_string, w_string_position, w_end):
    # XXX temporary ugly method signature until we can call this from
    # interp-level only
    atcode = space.int_w(w_atcode)
    if atcode >= len(at_dispatch_table):
        return space.newbool(False)
    context = MatchContext(space, [], w_string, space.int_w(w_string_position),
                                                            space.int_w(w_end))
    function, negate = at_dispatch_table[atcode]
    result = function(space, context)
    if negate:
        return space.newbool(not result)
    else:
        return space.newbool(result)

def at_beginning(space, ctx):
    return ctx.at_beginning()

def at_beginning_line(space, ctx):
    return ctx.at_beginning() or is_linebreak(space, ctx.peek_char(-1))
    
def at_end(space, ctx):
    return ctx.at_end() or (ctx.remaining_chars() == 1 and ctx.at_linebreak())

def at_end_line(space, ctx):
    return ctx.at_linebreak() or ctx.at_end()

def at_end_string(space, ctx):
    return ctx.at_end()

def at_boundary(space, ctx):
    return ctx.at_boundary(is_word)

def at_loc_boundary(space, ctx):
    return ctx.at_boundary(is_loc_word)

def at_uni_boundary(space, ctx):
    return ctx.at_boundary(is_uni_word)

# Maps opcodes by indices to (function, negate) tuples.
at_dispatch_table = [
    (at_beginning, False), (at_beginning_line, False), (at_beginning, False),
    (at_boundary, False), (at_boundary, True),
    (at_end, False), (at_end_line, False), (at_end_string, False),
    (at_loc_boundary, False), (at_loc_boundary, True), (at_uni_boundary, False),
    (at_uni_boundary, True)
]

##### Charset evaluation

def check_charset(space, w_pattern_codes, w_char_code, w_string, w_string_position):
    """Checks whether a character matches set of arbitrary length. Currently
    assumes the set starts at the first member of pattern_codes."""
    # XXX temporary ugly method signature until we can call this from
    # interp-level only
    pattern_codes_w = space.unpackiterable(w_pattern_codes)
    pattern_codes = [space.int_w(code) for code in pattern_codes_w]
    char_code = space.int_w(w_char_code)
    context = MatchContext(space, pattern_codes, w_string,
              space.int_w(w_string_position), space.int_w(space.len(w_string)))
    result = None
    while result is None:
        opcode = context.peek_code()
        if opcode >= len(set_dispatch_table):
            return space.newbool(False)
        function = set_dispatch_table[opcode]
        result = function(space, context, char_code)
    return space.newbool(result)

def set_failure(space, ctx, char_code):
    return not ctx.set_ok

def set_literal(space, ctx, char_code):
    # <LITERAL> <code>
    if ctx.peek_code(1) == char_code:
        return ctx.set_ok
    else:
        ctx.skip_code(2)

def set_category(space, ctx, char_code):
    # <CATEGORY> <code>
    if space.is_true(
       category_dispatch(space, space.wrap(ctx.peek_code(1)), ctx.peek_char())):
        return ctx.set_ok
    else:
        ctx.skip_code(2)

def set_charset(space, ctx, char_code):
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

def set_range(space, ctx, char_code):
    # <RANGE> <lower> <upper>
    if ctx.peek_code(1) <= char_code <= ctx.peek_code(2):
        return ctx.set_ok
    ctx.skip_code(3)

def set_negate(space, ctx, char_code):
    ctx.set_ok = not ctx.set_ok
    ctx.skip_code(1)

def set_bigcharset(space, ctx, char_code):
    # <BIGCHARSET> <blockcount> <256 blockindices> <blocks>
    # XXX this function probably needs a makeover
    count = ctx.peek_code(1)
    ctx.skip_code(2)
    if char_code < 65536:
        block_index = char_code >> 8
        # NB: there are CODESIZE block indices per bytecode
        # XXX can we really use array here?
        a = array("B")
        a.fromstring(array(CODESIZE == 2 and "H" or "I",
                [ctx.peek_code(block_index / CODESIZE)]).tostring())
        block = a[block_index % CODESIZE]
        ctx.skip_code(256 / CODESIZE) # skip block indices
        block_value = ctx.peek_code(block * (32 / CODESIZE)
                + ((char_code & 255) >> (CODESIZE == 2 and 4 or 5)))
        if block_value & (1 << (char_code & ((8 * CODESIZE) - 1))):
            return ctx.set_ok
    else:
        ctx.skip_code(256 / CODESIZE) # skip block indices
    ctx.skip_code(count * (32 / CODESIZE)) # skip blocks

set_dispatch_table = [
    set_failure, None, None, None, None, None, None, None, None,
    set_category, set_charset, set_bigcharset, None, None, None,
    None, None, None, None, set_literal, None, None, None, None,
    None, None, set_negate, set_range
]
