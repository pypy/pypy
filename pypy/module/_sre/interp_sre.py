from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app
import sys

#### Constants and exposed functions

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

def w_getlower(space, w_char_ord, w_flags):
    return space.wrap(getlower(space, space.int_w(w_char_ord), space.int_w(w_flags)))

def getlower(space, char_ord, flags):
    if (char_ord < 128) or (flags & SRE_FLAG_UNICODE) \
                              or (flags & SRE_FLAG_LOCALE and char_ord < 256):
        w_uni_char = space.newunicode([char_ord])
        w_lowered = space.call_method(w_uni_char, "lower")
        return space.int_w(space.ord(w_lowered))
    else:
        return char_ord

def w_getcodesize(space):
    return space.wrap(CODESIZE)

#### Core classes

def make_state(space, w_string, w_start, w_end, w_flags):
    # XXX maybe turn this into a __new__ method of W_State
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
        self.w_reset()

    def w_reset(self):
        self.marks = []
        self.lastindex = -1
        self.marks_stack = []
        self.context_stack = []
        self.repeat = None

    def w_create_regs(self, w_group_count):
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

    def set_mark(self, mark_nr, position):
        if mark_nr & 1:
            # This id marks the end of a group.
            self.lastindex = mark_nr / 2 + 1
        if mark_nr >= len(self.marks):
            self.marks.extend([-1] * (mark_nr - len(self.marks) + 1))
        self.marks[mark_nr] = position

    def get_marks(self, group_index):
        marks_index = 2 * group_index
        if len(self.marks) > marks_index + 1:
            return self.marks[marks_index], self.marks[marks_index + 1]
        else:
            return -1, -1

    def marks_push(self):
        self.marks_stack.append((self.marks[:], self.lastindex))

    def marks_pop(self):
        self.marks, self.lastindex = self.marks_stack.pop()

    def marks_pop_keep(self):
        self.marks, self.lastindex = self.marks_stack[-1]

    def marks_pop_discard(self):
        self.marks_stack.pop()

    def lower(self, char_ord):
        return getlower(self.space, char_ord, self.flags)

    # Accessors for the typedef
    
    def fget_start(space, self):
        return space.wrap(self.start)

    def fset_start(space, self, w_value):
        self.start = space.int_w(w_value)

    def fget_string_position(space, self):
        return space.wrap(self.string_position)

    def fset_string_position(space, self, w_value):
        self.start = space.int_w(w_value)

getset_start = GetSetProperty(W_State.fget_start, W_State.fset_start, cls=W_State)
getset_string_position = GetSetProperty(W_State.fget_string_position,
                                     W_State.fset_string_position, cls=W_State)

W_State.typedef = TypeDef("W_State",
    string = interp_attrproperty_w("w_string", W_State),
    start = getset_start,
    end = interp_attrproperty("end", W_State),
    string_position = getset_string_position,
    pos = interp_attrproperty("pos", W_State),
    lastindex = interp_attrproperty("lastindex", W_State),
    reset = interp2app(W_State.w_reset),
    create_regs = interp2app(W_State.w_create_regs),
)

class MatchContext:

    UNDECIDED = 0
    MATCHED = 1
    NOT_MATCHED = 2

    def __init__(self, space, state, pattern_codes):
        self.space = space
        self.state = state
        self.pattern_codes = pattern_codes
        self.string_position = state.string_position
        self.code_position = 0
        self.has_matched = self.UNDECIDED
        self.backup = []
        self.resume_at_opcode = -1

    def push_new_context(self, pattern_offset):
        """Creates a new child context of this context and pushes it on the
        stack. pattern_offset is the offset off the current code position to
        start interpreting from."""
        offset = self.code_position + pattern_offset
        assert offset >= 0
        pattern_codes = self.pattern_codes[offset:]
        child_context = MatchContext(self.space, self.state, pattern_codes)
        self.state.context_stack.append(child_context)
        self.child_context = child_context
        return child_context

    def is_resumed(self):
        return self.resume_at_opcode > -1

    def backup_value(self, value):
        self.backup.append(value)

    def restore_values(self):
        values = self.backup
        self.backup = []
        return values

    def peek_char(self, peek=0):
        return self.space.getitem(self.state.w_string,
                                   self.space.wrap(self.string_position + peek))

    def peek_char_ord(self, peek=0):
        # XXX this is not very nice
        return self.space.int_w(self.space.ord(self.peek_char(peek)))

    def skip_char(self, skip_count):
        self.string_position = self.string_position + skip_count

    def remaining_chars(self):
        return self.state.end - self.string_position

    def peek_code(self, peek=0):
        return self.pattern_codes[self.code_position + peek]

    def skip_code(self, skip_count):
        self.code_position = self.code_position + skip_count

    def remaining_codes(self):
        return len(self.pattern_codes) - self.code_position

    def at_beginning(self):
        return self.string_position == 0

    def at_end(self):
        return self.string_position == self.state.end

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


class RepeatContext(MatchContext):
    
    def __init__(self, space, context):
        offset = context.code_position
        assert offset >= 0
        MatchContext.__init__(self, space, context.state,
                                context.pattern_codes[offset:])
        self.count = -1
        self.previous = context.state.repeat
        self.last_position = -1
        self.repeat_stack = []


#### Main opcode dispatch loop

def w_search(space, w_state, w_pattern_codes):
    assert isinstance(w_state, W_State)
    pattern_codes = [space.int_w(code) for code
                                    in space.unpackiterable(w_pattern_codes)]
    return space.newbool(search(space, w_state, pattern_codes))

def search(space, state, pattern_codes):
    flags = 0
    if pattern_codes[0] == OPCODE_INFO:
        # optimization info block
        # <INFO> <1=skip> <2=flags> <3=min> <4=max> <5=prefix info>
        if pattern_codes[2] & SRE_INFO_PREFIX and pattern_codes[5] > 1:
            return fast_search(space, state, pattern_codes)
        flags = pattern_codes[2]
        offset = pattern_codes[1] + 1
        assert offset >= 0
        pattern_codes = pattern_codes[offset:]

    string_position = state.start
    while string_position <= state.end:
        state.w_reset()
        state.start = state.string_position = string_position
        if match(space, state, pattern_codes):
            return True
        string_position += 1
    return False

def fast_search(space, state, pattern_codes):
    """Skips forward in a string as fast as possible using information from
    an optimization info block."""
    # pattern starts with a known prefix
    # <5=length> <6=skip> <7=prefix data> <overlap data>
    flags = pattern_codes[2]
    prefix_len = pattern_codes[5]
    assert prefix_len >= 0
    prefix_skip = pattern_codes[6] # don't really know what this is good for
    assert prefix_skip >= 0
    prefix = pattern_codes[7:7 + prefix_len]
    overlap_offset = 7 + prefix_len - 1
    overlap_stop = pattern_codes[1] + 1
    assert overlap_offset >= 0
    assert overlap_stop >= 0
    overlap = pattern_codes[overlap_offset:overlap_stop]
    pattern_offset = pattern_codes[1] + 1
    assert pattern_offset >= 0
    pattern_codes = pattern_codes[pattern_offset:]
    i = 0
    string_position = state.string_position
    while string_position < state.end:
        while True:
            char_ord = space.int_w(space.ord(
                space.getitem(state.w_string, space.wrap(string_position))))
            if char_ord != prefix[i]:
                if i == 0:
                    break
                else:
                    i = overlap[i]
            else:
                i += 1
                if i == prefix_len:
                    # found a potential match
                    state.start = string_position + 1 - prefix_len
                    state.string_position = string_position + 1 \
                                                 - prefix_len + prefix_skip
                    if flags & SRE_INFO_LITERAL:
                        return True # matched all of pure literal pattern
                    if match(space, state, pattern_codes[2 * prefix_skip:]):
                        return True
                    i = overlap[i]
                break
        string_position += 1
    return False

def w_match(space, w_state, w_pattern_codes):
    assert isinstance(w_state, W_State)
    pattern_codes = [space.int_w(code) for code
                                    in space.unpackiterable(w_pattern_codes)]
    return space.newbool(match(space, w_state, pattern_codes))

def match(space, state, pattern_codes):
    # Optimization: Check string length. pattern_codes[3] contains the
    # minimum length for a string to possibly match.
    if pattern_codes[0] == OPCODE_INFO and pattern_codes[3] > 0:
        if state.end - state.string_position < pattern_codes[3]:
            return False
    state.context_stack.append(MatchContext(space, state, pattern_codes))
    has_matched = MatchContext.UNDECIDED
    while len(state.context_stack) > 0:
        context = state.context_stack[-1]
        if context.has_matched == context.UNDECIDED:
            has_matched = dispatch_loop(space, context)
        else:
            has_matched = context.has_matched
        if has_matched != context.UNDECIDED: # don't pop if context isn't done
            state.context_stack.pop()
    return has_matched == MatchContext.MATCHED

def dispatch_loop(space, context):
    """Returns MATCHED if the current context matches, NOT_MATCHED if it doesn't
    and UNDECIDED if matching is not finished, ie must be resumed after child
    contexts have been matched."""
    while context.remaining_codes() > 0 and context.has_matched == context.UNDECIDED:
        if context.is_resumed():
            opcode = context.resume_at_opcode
        else:
            opcode = context.peek_code()
        try:
            has_finished = opcode_dispatch_table[opcode](space, context)
        except IndexError:
            raise RuntimeError("Internal re error. Unknown opcode: %s" % opcode)
        if not has_finished:
            context.resume_at_opcode = opcode
            return context.UNDECIDED
        context.resume_at_opcode = -1
    if context.has_matched == context.UNDECIDED:
        context.has_matched = context.NOT_MATCHED
    return context.has_matched

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

def op_category(space, ctx):
    # match at given category
    # <CATEGORY> <code>
    if ctx.at_end() or \
                not category_dispatch(space, ctx.peek_code(1), ctx.peek_char()):
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    ctx.skip_code(2)
    ctx.skip_char(1)
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

def op_any_all(space, ctx):
    # match anything
    # <ANY_ALL>
    if ctx.at_end():
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    ctx.skip_code(1)
    ctx.skip_char(1)
    return True

def general_op_in(space, ctx, ignore=False):
    if ctx.at_end():
        ctx.has_matched = ctx.NOT_MATCHED
        return
    skip = ctx.peek_code(1)
    ctx.skip_code(2) # set op pointer to the set code
    char_code = ctx.peek_char_ord()
    if ignore:
        char_code = ctx.state.lower(char_code)
    if not check_charset(space, char_code, ctx):
        ctx.has_matched = ctx.NOT_MATCHED
        return
    ctx.skip_code(skip - 1)
    ctx.skip_char(1)

def op_in(space, ctx):
    # match set member (or non_member)
    # <IN> <skip> <set>
    general_op_in(space, ctx)
    return True

def op_in_ignore(space, ctx):
    # match set member (or non_member), disregarding case of current char
    # <IN_IGNORE> <skip> <set>
    general_op_in(space, ctx, ignore=True)
    return True

def op_branch(space, ctx):
    # alternation
    # <BRANCH> <0=skip> code <JUMP> ... <NULL>
    if not ctx.is_resumed():
        ctx.state.marks_push()
        ctx.skip_code(1)
        current_branch_length = ctx.peek_code(0)
    else:
        if ctx.child_context.has_matched == ctx.MATCHED:
            ctx.has_matched = ctx.MATCHED
            return True
        ctx.state.marks_pop_keep()
        last_branch_length = ctx.restore_values()[0]
        ctx.skip_code(last_branch_length)
        current_branch_length = ctx.peek_code(0)
    if current_branch_length:
        ctx.state.string_position = ctx.string_position
        ctx.push_new_context(1)
        ctx.backup_value(current_branch_length)
        return False
    ctx.state.marks_pop_discard()
    ctx.has_matched = ctx.NOT_MATCHED
    return True

def op_repeat_one(space, ctx):
    # match repeated sequence (maximizing).
    # this operator only works if the repeated item is exactly one character
    # wide, and we're not already collecting backtracking points.
    # <REPEAT_ONE> <skip> <1=min> <2=max> item <SUCCESS> tail
    
    # Case 1: First entry point
    if not ctx.is_resumed():
        mincount = ctx.peek_code(2)
        maxcount = ctx.peek_code(3)
        if ctx.remaining_chars() < mincount:
            ctx.has_matched = ctx.NOT_MATCHED
            return True
        ctx.state.string_position = ctx.string_position
        count = count_repetitions(space, ctx, maxcount)
        ctx.skip_char(count)
        if count < mincount:
            ctx.has_matched = ctx.NOT_MATCHED
            return True
        if ctx.peek_code(ctx.peek_code(1) + 1) == 1: # 1 == OPCODES["success"]
            # tail is empty.  we're finished
            ctx.state.string_position = ctx.string_position
            ctx.has_matched = ctx.MATCHED
            return True
        ctx.state.marks_push()
        # XXX literal optimization missing here

    # Case 2: Repetition is resumed (aka backtracked)
    else:
        if ctx.child_context.has_matched == ctx.MATCHED:
            ctx.has_matched = ctx.MATCHED
            return True
        values = ctx.restore_values()
        mincount = values[0]
        count = values[1]
        ctx.skip_char(-1)
        count -= 1
        ctx.state.marks_pop_keep()
        
    # Initialize the actual backtracking
    if count >= mincount:
        ctx.state.string_position = ctx.string_position
        ctx.push_new_context(ctx.peek_code(1) + 1)
        ctx.backup_value(mincount)
        ctx.backup_value(count)
        return False

    # Backtracking failed
    ctx.state.marks_pop_discard()
    ctx.has_matched = ctx.NOT_MATCHED
    return True

def op_min_repeat_one(space, ctx):
    # match repeated sequence (minimizing)
    # <MIN_REPEAT_ONE> <skip> <1=min> <2=max> item <SUCCESS> tail
    
    # Case 1: First entry point
    if not ctx.is_resumed():
        mincount = ctx.peek_code(2)
        maxcount = ctx.peek_code(3)
        if ctx.remaining_chars() < mincount:
            ctx.has_matched = ctx.NOT_MATCHED
            return True
        ctx.state.string_position = ctx.string_position
        if mincount == 0:
            count = 0
        else:
            count = count_repetitions(space, ctx, mincount)
            if count < mincount:
                ctx.has_matched = ctx.NOT_MATCHED
                return True
            ctx.skip_char(count)
        if ctx.peek_code(ctx.peek_code(1) + 1) == 1: # OPCODES["success"]
            # tail is empty.  we're finished
            ctx.state.string_position = ctx.string_position
            ctx.has_matched = ctx.MATCHED
            return True
        ctx.state.marks_push()

    # Case 2: Repetition resumed, "forwardtracking"
    else:
        if ctx.child_context.has_matched == ctx.MATCHED:
            ctx.has_matched = ctx.MATCHED
            return True
        values = ctx.restore_values()
        maxcount = values[0]
        count = values[1]        
        ctx.state.string_position = ctx.string_position
        if count_repetitions(space, ctx, 1) == 0:
            # Tail didn't match and no more repetitions --> fail
            ctx.state.marks_pop_discard()
            ctx.has_matched = ctx.NOT_MATCHED
            return True
        ctx.skip_char(1)
        count += 1
        ctx.state.marks_pop_keep()

    # Try to match tail
    if maxcount == MAXREPEAT or count <= maxcount:
        ctx.state.string_position = ctx.string_position
        ctx.push_new_context(ctx.peek_code(1) + 1)
        ctx.backup_value(maxcount)
        ctx.backup_value(count)
        return False

    # Failed
    ctx.state.marks_pop_discard()
    ctx.has_matched = ctx.NOT_MATCHED
    return True

def op_repeat(space, ctx):
    # create repeat context.  all the hard work is done by the UNTIL
    # operator (MAX_UNTIL, MIN_UNTIL)
    # <REPEAT> <skip> <1=min> <2=max> item <UNTIL> tail
    if not ctx.is_resumed():
        ctx.repeat = RepeatContext(space, ctx)
        ctx.state.repeat = ctx.repeat
        ctx.state.string_position = ctx.string_position
        ctx.push_new_context(ctx.peek_code(1) + 1)
        return False
    else:
        ctx.state.repeat = ctx.repeat
        ctx.has_matched = ctx.child_context.has_matched
        return True

def op_max_until(space, ctx):
    # maximizing repeat
    # <REPEAT> <skip> <1=min> <2=max> item <MAX_UNTIL> tail
    
    # Case 1: First entry point
    if not ctx.is_resumed():
        repeat = ctx.state.repeat
        if repeat is None:
            raise RuntimeError("Internal re error: MAX_UNTIL without REPEAT.")
        mincount = repeat.peek_code(2)
        maxcount = repeat.peek_code(3)
        ctx.state.string_position = ctx.string_position
        count = repeat.count + 1
        if count < mincount:
            # not enough matches
            repeat.count = count
            repeat.repeat_stack.append(repeat.push_new_context(4))
            ctx.backup_value(mincount)
            ctx.backup_value(maxcount)
            ctx.backup_value(count)
            ctx.backup_value(0) # Dummy for last_position
            ctx.backup_value(0)
            ctx.repeat = repeat
            return False
        if (count < maxcount or maxcount == MAXREPEAT) \
                        and ctx.state.string_position != repeat.last_position:
            # we may have enough matches, if we can match another item, do so
            repeat.count = count
            ctx.state.marks_push()
            repeat.last_position = ctx.state.string_position
            repeat.repeat_stack.append(repeat.push_new_context(4))
            ctx.backup_value(mincount)
            ctx.backup_value(maxcount)
            ctx.backup_value(count)
            ctx.backup_value(repeat.last_position) # zero-width match protection
            ctx.backup_value(2) # more matching
            ctx.repeat = repeat
            return False

        # Cannot match more repeated items here. Make sure the tail matches.
        ctx.state.repeat = repeat.previous
        ctx.push_new_context(1)
        ctx.backup_value(mincount)
        ctx.backup_value(maxcount)
        ctx.backup_value(count)
        ctx.backup_value(repeat.last_position) # zero-width match protection
        ctx.backup_value(1) # tail matching
        ctx.repeat = repeat
        return False

    # Case 2: Resumed
    else:
        repeat = ctx.repeat
        values = ctx.restore_values()
        mincount = values[0]
        maxcount = values[1]
        count = values[2]
        save_last_position = values[3]
        tail_matching = values[4]
        
        if tail_matching == 0:
            ctx.has_matched = repeat.repeat_stack.pop().has_matched
            if ctx.has_matched == ctx.NOT_MATCHED:
                repeat.count = count - 1
                ctx.state.string_position = ctx.string_position
            return True
        elif tail_matching == 2:
            repeat.last_position = save_last_position
            if repeat.repeat_stack.pop().has_matched == ctx.MATCHED:
                ctx.state.marks_pop_discard()
                ctx.has_matched = ctx.MATCHED
                return True
            ctx.state.marks_pop()
            repeat.count = count - 1
            ctx.state.string_position = ctx.string_position

            # Cannot match more repeated items here. Make sure the tail matches.
            ctx.state.repeat = repeat.previous
            ctx.push_new_context(1)
            ctx.backup_value(mincount)
            ctx.backup_value(maxcount)
            ctx.backup_value(count)
            ctx.backup_value(repeat.last_position) # zero-width match protection
            ctx.backup_value(1) # tail matching
            return False

        else: # resuming after tail matching
            ctx.has_matched = ctx.child_context.has_matched
            if ctx.has_matched == ctx.NOT_MATCHED:
                ctx.state.repeat = repeat
                ctx.state.string_position = ctx.string_position
            return True

def op_min_until(space, ctx):
    # minimizing repeat
    # <REPEAT> <skip> <1=min> <2=max> item <MIN_UNTIL> tail
    
    # Case 1: First entry point
    if not ctx.is_resumed():
        repeat = ctx.state.repeat
        if repeat is None:
            raise RuntimeError("Internal re error: MIN_UNTIL without REPEAT.")
        mincount = repeat.peek_code(2)
        maxcount = repeat.peek_code(3)
        ctx.state.string_position = ctx.string_position
        count = repeat.count + 1

        if count < mincount:
            # not enough matches
            repeat.count = count
            repeat.repeat_stack.append(repeat.push_new_context(4))
            ctx.backup_value(mincount)
            ctx.backup_value(maxcount)
            ctx.backup_value(count)
            ctx.backup_value(0)
            ctx.repeat = repeat
            return False

        # see if the tail matches
        ctx.state.marks_push()
        ctx.state.repeat = repeat.previous
        ctx.push_new_context(1)
        ctx.backup_value(mincount)
        ctx.backup_value(maxcount)
        ctx.backup_value(count)
        ctx.backup_value(1)
        ctx.repeat = repeat
        return False

    # Case 2: Resumed
    else:
        repeat = ctx.repeat
        if repeat.has_matched == ctx.MATCHED:
            ctx.has_matched = ctx.MATCHED
            return True
        values = ctx.restore_values()
        mincount = values[0]
        maxcount = values[1]
        count = values[2]
        matching_state = values[3]

        if count < mincount:
            # not enough matches
            ctx.has_matched = repeat.repeat_stack.pop().has_matched
            if ctx.has_matched == ctx.NOT_MATCHED:
                repeat.count = count - 1
                ctx.state.string_position = ctx.string_position
            return True
        
        if matching_state == 1:
            # returning from tail matching
            if ctx.child_context.has_matched == ctx.MATCHED:
                ctx.has_matched = ctx.MATCHED
                return True
            ctx.state.repeat = repeat
            ctx.state.string_position = ctx.string_position
            ctx.state.marks_pop()

        if not matching_state == 2:
            # match more until tail matches
            if count >= maxcount and maxcount != MAXREPEAT:
                ctx.has_matched = ctx.NOT_MATCHED
                return True
            repeat.count = count
            repeat.repeat_stack.append(repeat.push_new_context(4))
            ctx.backup_value(mincount)
            ctx.backup_value(maxcount)
            ctx.backup_value(count)
            ctx.backup_value(2)
            ctx.repeat = repeat
            return False

        # Final return
        ctx.has_matched = repeat.repeat_stack.pop().has_matched
        repeat.has_matched = ctx.has_matched
        if ctx.has_matched == ctx.NOT_MATCHED:
            repeat.count = count - 1
            ctx.state.string_position = ctx.string_position
        return True

def op_jump(space, ctx):
    # jump forward
    # <JUMP>/<INFO> <offset>
    ctx.skip_code(ctx.peek_code(1) + 1)
    return True

def op_mark(space, ctx):
    # set mark
    # <MARK> <gid>
    ctx.state.set_mark(ctx.peek_code(1), ctx.string_position)
    ctx.skip_code(2)
    return True

def general_op_groupref(space, ctx, ignore=False):
    group_start, group_end = ctx.state.get_marks(ctx.peek_code(1))
    if group_start == -1 or group_end == -1 or group_end < group_start \
                            or group_end - group_start > ctx.remaining_chars():
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    while group_start < group_end:
        # XXX This is really a bit unwieldy. Can this be improved?
        new_char = ctx.peek_char_ord()
        old_char = space.int_w(space.ord(
                    space.getitem(ctx.state.w_string, space.wrap(group_start))))
        if ctx.at_end() or (not ignore and old_char != new_char) \
                or (ignore and ctx.state.lower(old_char) != ctx.state.lower(new_char)):
            ctx.has_matched = ctx.NOT_MATCHED
            return True
        group_start += 1
        ctx.skip_char(1)
    ctx.skip_code(2)
    return True

def op_groupref(space, ctx):
    # match backreference
    # <GROUPREF> <zero-based group index>
    return general_op_groupref(space, ctx)

def op_groupref_ignore(space, ctx):
    # match backreference case-insensitive
    # <GROUPREF_IGNORE> <zero-based group index>
    return general_op_groupref(space, ctx, ignore=True)

def op_groupref_exists(space, ctx):
    # <GROUPREF_EXISTS> <group> <skip> codeyes <JUMP> codeno ...
    group_start, group_end = ctx.state.get_marks(ctx.peek_code(1))
    if group_start == -1 or group_end == -1 or group_end < group_start:
        ctx.skip_code(ctx.peek_code(2) + 1)
    else:
        ctx.skip_code(3)
    return True

def op_assert(space, ctx):
    # assert subpattern
    # <ASSERT> <skip> <back> <pattern>
    if not ctx.is_resumed():
        ctx.state.string_position = ctx.string_position - ctx.peek_code(2)
        if ctx.state.string_position < 0:
            ctx.has_matched = ctx.NOT_MATCHED
            return True
        ctx.push_new_context(3)
        return False
    else:
        if ctx.child_context.has_matched == ctx.MATCHED:
            ctx.skip_code(ctx.peek_code(1) + 1)
        else:
            ctx.has_matched = ctx.NOT_MATCHED
        return True

def op_assert_not(space, ctx):
    # assert not subpattern
    # <ASSERT_NOT> <skip> <back> <pattern>
    if not ctx.is_resumed():
        ctx.state.string_position = ctx.string_position - ctx.peek_code(2)
        if ctx.state.string_position >= 0:
            ctx.push_new_context(3)
            return False
    else:
        if ctx.child_context.has_matched == ctx.MATCHED:
            ctx.has_matched = ctx.NOT_MATCHED
            return True
    ctx.skip_code(ctx.peek_code(1) + 1)
    return True

def count_repetitions(space, ctx, maxcount):
    """Returns the number of repetitions of a single item, starting from the
    current string position. The code pointer is expected to point to a
    REPEAT_ONE operation (with the repeated 4 ahead)."""
    count = 0
    real_maxcount = ctx.state.end - ctx.string_position
    if maxcount < real_maxcount and maxcount != MAXREPEAT:
        real_maxcount = maxcount
    # XXX could special case every single character pattern here, as in C.
    # This is a general solution, a bit hackisch, but works and should be
    # efficient.
    code_position = ctx.code_position
    string_position = ctx.string_position
    ctx.skip_code(4)
    reset_position = ctx.code_position
    while count < real_maxcount:
        # this works because the single character pattern is followed by
        # a success opcode
        ctx.code_position = reset_position
        opcode_dispatch_table[ctx.peek_code()](space, ctx)
        if ctx.has_matched == ctx.NOT_MATCHED:
            break
        count += 1
    ctx.has_matched = ctx.UNDECIDED
    ctx.code_position = code_position
    ctx.string_position = string_position
    return count

opcode_dispatch_table = [
    op_failure, op_success,
    op_any, op_any_all,
    op_assert, op_assert_not,
    op_at,
    op_branch,
    None, #CALL,
    op_category,
    None, None, #CHARSET, BIGCHARSET,
    op_groupref, op_groupref_exists, op_groupref_ignore,
    op_in, op_in_ignore,
    op_jump, op_jump,
    op_literal, op_literal_ignore,
    op_mark,
    op_max_until,
    op_min_until,
    op_not_literal, op_not_literal_ignore,
    None, #NEGATE,
    None, #RANGE,
    op_repeat,
    op_repeat_one,
    None, #SUBPATTERN,
    op_min_repeat_one,
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

def category_dispatch(space, chcode, w_char):
    try:
        function, negate = category_dispatch_table[chcode]
    except IndexError:
        return False
    result = function(space, w_char)
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

##### At dispatch

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

SET_OK = 1
SET_NOT_OK = -1
SET_NOT_FINISHED = 0

def check_charset(space, char_code, context):
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
        result = function(space, context, char_code)
    context.code_position = backup_code_position
    return result == SET_OK

def set_failure(space, ctx, char_code):
    return -ctx.set_ok

def set_literal(space, ctx, char_code):
    # <LITERAL> <code>
    if ctx.peek_code(1) == char_code:
        return ctx.set_ok
    else:
        ctx.skip_code(2)
        return SET_NOT_FINISHED

def set_category(space, ctx, char_code):
    # <CATEGORY> <code>
    if category_dispatch(space, ctx.peek_code(1), ctx.peek_char()):
        return ctx.set_ok
    else:
        ctx.skip_code(2)
        return SET_NOT_FINISHED

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
    return SET_NOT_FINISHED

def set_range(space, ctx, char_code):
    # <RANGE> <lower> <upper>
    if ctx.peek_code(1) <= char_code <= ctx.peek_code(2):
        return ctx.set_ok
    ctx.skip_code(3)
    return SET_NOT_FINISHED

def set_negate(space, ctx, char_code):
    ctx.set_ok = -ctx.set_ok
    ctx.skip_code(1)
    return SET_NOT_FINISHED

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
    return SET_NOT_FINISHED

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
