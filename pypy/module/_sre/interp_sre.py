from pypy.interpreter.baseobjspace import ObjSpace, Wrappable
# XXX is it allowed to import app-level module like this?
from pypy.module._sre.app_info import CODESIZE
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
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
        self.w_context_stack = self.space.newlist([])
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

    def lower(self, char_ord):
        return self.space.int_w(self.w_lower(self.space.wrap(char_ord)))

    def w_lower(self, w_char_ord):
        return getlower(self.space, w_char_ord, self.space.wrap(self.flags))

def interp_attrproperty_int(name, cls):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, obj):
        return space.wrap(getattr(obj, name))
    def fset(space, obj, w_value):
        setattr(obj, name, space.int_w(w_value))
    return GetSetProperty(fget, fset, cls=cls)

def interp_attrproperty_list_w(name, cls):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, obj):
        return space.newlist(getattr(obj, name))
    return GetSetProperty(fget, cls=cls)

def interp_attrproperty_obj_w(name, cls):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, obj):
        return getattr(obj, name)
    def fset(space, obj, w_value):
        setattr(obj, name, w_value)
    return GetSetProperty(fget, fset, cls=cls)

W_State.typedef = TypeDef("W_State",
    string = interp_attrproperty_obj_w("w_string", W_State),
    start = interp_attrproperty_int("start", W_State),
    end = interp_attrproperty_int("end", W_State),
    string_position = interp_attrproperty_int("string_position", W_State),
    pos = interp_attrproperty("pos", W_State),
    lastindex = interp_attrproperty("lastindex", W_State),
    context_stack = interp_attrproperty_w("w_context_stack", W_State),
    repeat = interp_attrproperty_obj_w("w_repeat", W_State),
    reset = interp2app(W_State.reset),
    set_mark = interp2app(W_State.set_mark),
    get_marks = interp2app(W_State.get_marks),
    create_regs = interp2app(W_State.create_regs),
    marks_push = interp2app(W_State.marks_push),
    marks_pop = interp2app(W_State.marks_pop),
    marks_pop_keep = interp2app(W_State.marks_pop_keep),
    marks_pop_discard = interp2app(W_State.marks_pop_discard),
    lower = interp2app(W_State.w_lower),
)

def make_context(space, w_state, w_pattern_codes):
    # XXX Uhm, temporary
    return space.wrap(W_MatchContext(space, w_state, w_pattern_codes))

class W_MatchContext(Wrappable):

    UNDECIDED = 0
    MATCHED = 1
    NOT_MATCHED = 2

    def __init__(self, space, w_state, w_pattern_codes):
        self.space = space
        self.state = w_state
        self.pattern_codes_w = space.unpackiterable(w_pattern_codes)
        self.string_position = w_state.string_position
        self.code_position = 0
        self.has_matched = self.UNDECIDED

    def push_new_context(self, w_pattern_offset):
        """Creates a new child context of this context and pushes it on the
        stack. pattern_offset is the offset off the current code position to
        start interpreting from."""
        pattern_offset = self.space.int_w(w_pattern_offset)
        pattern_codes_w = self.pattern_codes_w[self.code_position + pattern_offset:]
        w_child_context = self.space.wrap(W_MatchContext(self.space, self.state,
                                           self.space.newlist(pattern_codes_w)))
        self.space.call_method(self.state.w_context_stack, "append", w_child_context)
        return w_child_context

    def peek_char(self, w_peek=0):
        # XXX temporary hack
        if w_peek == 0:
            w_peek = self.space.wrap(0)
        return self.space.getitem(self.state.w_string,
                self.space.add(self.space.wrap(self.string_position), w_peek))

    def peek_char_ord(self, peek=0):
        return self.space.int_w(self.space.ord(self.peek_char(self.space.wrap(peek))))

    def skip_char(self, skip_count):
        self.string_position = self.string_position + skip_count

    def w_skip_char(self, w_skip_count):
        self.skip_char(self.space.int_w(w_skip_count))

    def remaining_chars(self):
        return self.state.end - self.string_position

    def w_remaining_chars(self):
        return self.space.wrap(self.remaining_chars())

    def peek_code(self, peek=0):
        return self.space.int_w(self.pattern_codes_w[self.code_position + peek])

    def w_peek_code(self, w_peek=0):
        return self.space.wrap(self.peek_code(self.space.int_w(w_peek)))

    def skip_code(self, skip_count):
        self.code_position = self.code_position + skip_count

    def w_skip_code(self, w_skip_count):
        self.skip_code(self.space.int_w(w_skip_count))

    def remaining_codes(self):
        return self.space.wrap(len(self.pattern_codes_w) - self.code_position)

    def at_beginning(self):
        return self.string_position == 0

    def at_end(self):
        return self.string_position == self.state.end

    def w_at_end(self):
        return self.space.newbool(self.at_end())

    def at_linebreak(self):
        return not self.at_end() and is_linebreak(self.space, self.peek_char())

    def at_boundary(self, word_checker):
        if self.at_beginning() and self.at_end():
            return False
        that = not self.at_beginning() \
                            and word_checker(self.space, self.peek_char(self.space.wrap(-1)))
        this = not self.at_end() \
                            and word_checker(self.space, self.peek_char())
        return this != that

W_MatchContext.typedef = TypeDef("W_MatchContext",
    state = interp_attrproperty_w("state", W_MatchContext),
    string_position = interp_attrproperty_int("string_position", W_MatchContext),
    pattern_codes = interp_attrproperty_list_w("pattern_codes_w", W_MatchContext),
    code_position = interp_attrproperty_int("code_position", W_MatchContext),
    has_matched = interp_attrproperty_int("has_matched", W_MatchContext),
    push_new_context = interp2app(W_MatchContext.push_new_context),
    peek_char = interp2app(W_MatchContext.peek_char),
    skip_char = interp2app(W_MatchContext.w_skip_char),
    remaining_chars = interp2app(W_MatchContext.w_remaining_chars),
    peek_code = interp2app(W_MatchContext.w_peek_code),
    skip_code = interp2app(W_MatchContext.w_skip_code),
    remaining_codes = interp2app(W_MatchContext.remaining_codes),
    at_end = interp2app(W_MatchContext.w_at_end),
)

def make_repeat_context(space, w_context):
    # XXX Uhm, temporary
    return space.wrap(W_RepeatContext(space, w_context))

class W_RepeatContext(W_MatchContext):
    
    def __init__(self, space, w_context):
        W_MatchContext.__init__(self, space, w_context.state,
            space.newlist(w_context.pattern_codes_w[w_context.code_position:]))
        self.w_count = space.wrap(-1)
        self.w_previous = w_context.state.w_repeat
        self.w_last_position = space.w_None

W_RepeatContext.typedef = TypeDef("W_RepeatContext", W_MatchContext.typedef,
    count = interp_attrproperty_obj_w("w_count", W_RepeatContext),
    previous = interp_attrproperty_obj_w("w_previous", W_RepeatContext),
    last_position = interp_attrproperty_obj_w("w_last_position", W_RepeatContext),
)

#### Opcode dispatch

def opcode_dispatch(space, w_opcode, w_context):
    opcode = space.int_w(w_opcode)
    if opcode >= len(opcode_dispatch_table):
        return space.newbool(False)
    return space.newbool(opcode_dispatch_table[opcode](space, w_context))

def opcode_is_at_interplevel(space, w_opcode):
    opcode = space.int_w(w_opcode)
    return space.newbool(opcode_dispatch_table[opcode] is not None)

def op_success(space, ctx):
    # end of pattern
    ctx.state.string_position = ctx.string_position
    ctx.has_matched = ctx.MATCHED
    return True

def op_failure(space, ctx):
    # immediate failure
    ctx.has_matched = ctx.NOT_MATCHED
    return True

def op_literal(space, ctx):
    # match literal string
    # <LITERAL> <code>
    if ctx.at_end() or ctx.peek_char_ord() != ctx.peek_code(1):
        ctx.has_matched = ctx.NOT_MATCHED
    ctx.skip_code(2)
    ctx.skip_char(1)
    return True

def op_not_literal(space, ctx):
    # match anything that is not the given literal character
    # <NOT_LITERAL> <code>
    if ctx.at_end() or ctx.peek_char_ord() == ctx.peek_code(1):
        ctx.has_matched = ctx.NOT_MATCHED
    ctx.skip_code(2)
    ctx.skip_char(1)
    return True

def op_literal_ignore(space, ctx):
    # match literal regardless of case
    # <LITERAL_IGNORE> <code>
    if ctx.at_end() or \
      ctx.state.lower(ctx.peek_char_ord()) != ctx.state.lower(ctx.peek_code(1)):
        ctx.has_matched = ctx.NOT_MATCHED
    ctx.skip_code(2)
    ctx.skip_char(1)
    return True

def op_not_literal_ignore(space, ctx):
    # match literal regardless of case
    # <LITERAL_IGNORE> <code>
    if ctx.at_end() or \
      ctx.state.lower(ctx.peek_char_ord()) == ctx.state.lower(ctx.peek_code(1)):
        ctx.has_matched = ctx.NOT_MATCHED
    ctx.skip_code(2)
    ctx.skip_char(1)
    return True

def op_at(space, ctx):
    # match at given position
    # <AT> <code>
    if not at_dispatch(space, ctx.peek_code(1), ctx):
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    ctx.skip_code(2)
    return True

def op_any(self, ctx):
    # match anything (except a newline)
    # <ANY>
    if ctx.at_end() or ctx.at_linebreak():
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    ctx.skip_code(1)
    ctx.skip_char(1)
    return True

opcode_dispatch_table = [
    op_failure, op_success,
    op_any, None, #ANY, ANY_ALL,
    None, None, #ASSERT, ASSERT_NOT,
    op_at,
    None, #BRANCH,
    None, #CALL,
    None, #CATEGORY,
    None, None, #CHARSET, BIGCHARSET,
    None, None, None, #GROUPREF, GROUPREF_EXISTS, GROUPREF_IGNORE,
    None, None, #IN, IN_IGNORE,
    None, #INFO,
    None, #JUMP,
    op_literal, op_literal_ignore,
    None, #MARK,
    None, #MAX_UNTIL,
    None, #MIN_UNTIL,
    op_not_literal, op_not_literal_ignore,
    None, #NEGATE,
    None, #RANGE,
    None, #REPEAT,
    None, #REPEAT_ONE,
    None, #SUBPATTERN,
    None, #MIN_REPEAT_ONE
]


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
    return code < 128 and (ascii_char_info[code] & 1 != 0)

def is_uni_digit(space, w_char):
    return space.is_true(space.call_method(w_char, "isdigit"))

def is_space(space, w_char):
    code = space.int_w(space.ord(w_char))
    return code < 128 and (ascii_char_info[code] & 2 != 0)

def is_uni_space(space, w_char):
    return space.is_true(space.call_method(w_char, "isspace"))

def is_word(space, w_char):
    code = space.int_w(space.ord(w_char))
    return code < 128 and (ascii_char_info[code] & 16 != 0)

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

def at_dispatch(space, atcode, context):
    try:
        function, negate = at_dispatch_table[atcode]
    except IndexError:
        return False
    result = function(space, context)
    if negate:
        return not result
    else:
        return result

def at_beginning(space, ctx):
    return ctx.at_beginning()

def at_beginning_line(space, ctx):
    return ctx.at_beginning() or is_linebreak(space, ctx.peek_char(space.wrap(-1)))
    
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
