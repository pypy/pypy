from pypy.interpreter.baseobjspace import ObjSpace, Wrappable
# XXX is it allowed to import app-level module like this?
from pypy.module._sre.app_info import CODESIZE
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.gateway import interp2app

import sys
BIG_ENDIAN = sys.byteorder == "big"

#### Exposed functions

# XXX can we import those safely from sre_constants?
SRE_FLAG_LOCALE = 4 # honour system locale
SRE_FLAG_UNICODE = 32 # use unicode locale

def getlower(space, w_char_ord, w_flags):
    char_ord = space.int_w(w_char_ord)
    flags = space.int_w(w_flags)
    if (char_ord < 128) or (flags & SRE_FLAG_UNICODE) \
                              or (flags & SRE_FLAG_LOCALE and char_ord < 256):
        w_uni_char = space.newunicode([char_ord])
        w_lowered = space.call_method(w_uni_char, "lower")
        return space.ord(w_lowered)
    else:
        return space.wrap(char_ord)

#### Core classes

# XXX the wrapped/unwrapped semantics of the following classes are currently
# very confusing because they are still used at app-level.

def make_state(space, w_string, w_start, w_end, w_flags):
    # XXX Uhm, temporary
    return space.wrap(W_State(space, w_string, w_start, w_end, w_flags))

class W_State(Wrappable):

    def __init__(self, space, w_string, w_start, w_end, w_flags):
        self.space = space
        self.w_string = w_string
        start = space.int_w(w_start)
        end = space.int_w(w_end)
        if start < 0:
            start = 0
        if end > space.int_w(space.len(w_string)):
            end = space.int_w(space.len(w_string))
        self.start = start
        self.string_position = start
        self.end = end
        self.pos = start
        self.flags = space.int_w(w_flags)
        self.reset()

    def reset(self):
        self.marks = []
        self.lastindex = -1
        self.marks_stack = []
        self.context_stack = self.space.newlist([])
        self.w_repeat = self.space.w_None

    def set_mark(self, w_mark_nr, w_position):
        mark_nr = self.space.int_w(w_mark_nr)
        if mark_nr & 1:
            # This id marks the end of a group.
            self.lastindex = mark_nr / 2 + 1
        if mark_nr >= len(self.marks):
            self.marks.extend([-1] * (mark_nr - len(self.marks) + 1))
        self.marks[mark_nr] = self.space.int_w(w_position)

    def get_marks(self, w_group_index):
        marks_index = 2 * self.space.int_w(w_group_index)
        if len(self.marks) > marks_index + 1:
            return self.space.newtuple([self.space.wrap(self.marks[marks_index]),
                                  self.space.wrap(self.marks[marks_index + 1])])
        else:
            return self.space.newtuple([self.space.w_None, self.space.w_None])

    def create_regs(self, w_group_count):
        """Creates a tuple of index pairs representing matched groups, a format
        that's convenient for SRE_Match."""
        regs = [self.space.newtuple([self.space.wrap(self.start), self.space.wrap(self.string_position)])]
        for group in range(self.space.int_w(w_group_count)):
            mark_index = 2 * group
            if mark_index + 1 < len(self.marks):
                regs.append(self.space.newtuple([self.space.wrap(self.marks[mark_index]),
                                                 self.space.wrap(self.marks[mark_index + 1])]))
            else:
                regs.append(self.space.newtuple([self.space.wrap(-1),
                                                        self.space.wrap(-1)]))
        return self.space.newtuple(regs)

    def marks_push(self):
        self.marks_stack.append((self.marks[:], self.lastindex))

    def marks_pop(self):
        self.marks, self.lastindex = self.marks_stack.pop()

    def marks_pop_keep(self):
        self.marks, self.lastindex = self.marks_stack[-1]

    def marks_pop_discard(self):
        self.marks_stack.pop()

    def lower(self, w_char_ord):
        return getlower(self.space, w_char_ord, self.space.wrap(self.flags))

W_State.typedef = TypeDef("W_State",
    string = GetSetProperty(lambda space, state: state.w_string,
        lambda space, state, value: setattr(state, "w_string", value)),
    start = GetSetProperty(lambda space, state: space.wrap(state.start),
        lambda space, state, value: setattr(state, "start", space.int_w(value))),
    end = GetSetProperty(lambda space, state: space.wrap(state.end)),
    string_position = GetSetProperty(lambda space, state: space.wrap(state.string_position),
        lambda space, state, value: setattr(state, "string_position", space.int_w(value))),
    pos = GetSetProperty(lambda space, state: space.wrap(state.pos)),
    lastindex = GetSetProperty(lambda space, state: space.wrap(state.lastindex)),
    context_stack = GetSetProperty(lambda space, state: state.context_stack),
    repeat = GetSetProperty(lambda space, state: state.w_repeat,
        lambda space, state, value: setattr(state, "w_repeat", value)),
    reset = interp2app(W_State.reset, unwrap_spec = ["self"]),
    set_mark = interp2app(W_State.set_mark),
    get_marks = interp2app(W_State.get_marks),
    create_regs = interp2app(W_State.create_regs),
    marks_push = interp2app(W_State.marks_push, unwrap_spec = ["self"]),
    marks_pop = interp2app(W_State.marks_pop, unwrap_spec = ["self"]),
    marks_pop_keep = interp2app(W_State.marks_pop_keep, unwrap_spec = ["self"]),
    marks_pop_discard = interp2app(W_State.marks_pop_discard, unwrap_spec = ["self"]),
    lower = interp2app(W_State.lower),
)

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
uni_linebreaks = [10, 13, 28, 29, 30, 133, 8232, 8233]

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
    return code in uni_linebreaks


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

    # XXX These constants should maybe not be here    
    OK = 1
    NOT_OK = -1
    NOT_FINISHED = 0
    
    def __init__(self, space, pattern_codes, w_string, string_position, end):
        self.space = space
        self.pattern_codes = pattern_codes
        self.w_string = w_string
        self.string_position = string_position
        self.end = end
        self.code_position = 0
        self.set_ok = self.OK # XXX maybe get rid of this

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
    result = MatchContext.NOT_FINISHED
    while result == MatchContext.NOT_FINISHED:
        opcode = context.peek_code()
        if opcode >= len(set_dispatch_table):
            return space.newbool(False)
        function = set_dispatch_table[opcode]
        result = function(space, context, char_code)
    return space.newbool(result == MatchContext.OK)

def set_failure(space, ctx, char_code):
    return -ctx.set_ok

def set_literal(space, ctx, char_code):
    # <LITERAL> <code>
    if ctx.peek_code(1) == char_code:
        return ctx.set_ok
    else:
        ctx.skip_code(2)
        return MatchContext.NOT_FINISHED

def set_category(space, ctx, char_code):
    # <CATEGORY> <code>
    if space.is_true(
       category_dispatch(space, space.wrap(ctx.peek_code(1)), ctx.peek_char())):
        return ctx.set_ok
    else:
        ctx.skip_code(2)
        return MatchContext.NOT_FINISHED

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
    return MatchContext.NOT_FINISHED

def set_range(space, ctx, char_code):
    # <RANGE> <lower> <upper>
    if ctx.peek_code(1) <= char_code <= ctx.peek_code(2):
        return ctx.set_ok
    ctx.skip_code(3)
    return MatchContext.NOT_FINISHED

def set_negate(space, ctx, char_code):
    ctx.set_ok = -ctx.set_ok
    ctx.skip_code(1)
    return MatchContext.NOT_FINISHED

def set_bigcharset(space, ctx, char_code):
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
    return MatchContext.NOT_FINISHED

def to_byte_array(int_value):
    """Creates a list of bytes out of an integer representing data that is
    CODESIZE bytes wide."""
    byte_array = [0] * CODESIZE
    for i in range(CODESIZE):
        byte_array[i] = int_value & 0xff
        int_value = int_value >> 8
    if BIG_ENDIAN:
        # Uhm, maybe there's a better way to reverse lists
        byte_array_reversed = [0] * CODESIZE
        for i in range(CODESIZE):
            byte_array_reversed[-i-1] = byte_array[i]
        byte_array = byte_array_reversed
    return byte_array

set_dispatch_table = [
    set_failure, None, None, None, None, None, None, None, None,
    set_category, set_charset, set_bigcharset, None, None, None,
    None, None, None, None, set_literal, None, None, None, None,
    None, None, set_negate, set_range
]
