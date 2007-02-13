"""
Core routines for regular expression matching and searching.
"""

# This module should not be imported directly; it is execfile'd by rsre.py,
# possibly more than once.  This is done to create specialized version of
# this code: each copy is used with a 'state' that is an instance of a
# specific subclass of BaseState, so all the inner-loop calls to methods
# like state.get_char_ord() can be compiled as direct calls, which can be
# inlined.

from pypy.rlib.rsre import rsre_char
from pypy.rlib.rsre.rsre_char import SRE_INFO_PREFIX, SRE_INFO_LITERAL
from pypy.rlib.rsre.rsre_char import OPCODE_INFO, MAXREPEAT

#### Core classes

class StateMixin(object):

    def reset(self):
        self.string_position = self.start
        self.marks = []
        self.lastindex = -1
        self.marks_stack = []
        self.context_stack = []
        self.repeat = None

    def search(self, pattern_codes):
        return search(self, pattern_codes)

    def match(self, pattern_codes):
        return match(self, pattern_codes)

    def create_regs(self, group_count):
        """Creates a tuple of index pairs representing matched groups, a format
        that's convenient for SRE_Match."""
        regs = [(self.start, self.string_position)]
        for group in range(group_count):
            mark_index = 2 * group
            start = end = -1
            if mark_index + 1 < len(self.marks):
                start1 = self.marks[mark_index]
                end1   = self.marks[mark_index + 1]
                if start1 >= 0 and end1 >= 0:
                    start = start1
                    end   = end1
            regs.append((start, end))
        return regs

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
        marks, self.lastindex = self.marks_stack[-1]
        self.marks = marks[:]

    def marks_pop_discard(self):
        self.marks_stack.pop()


class MatchContext(rsre_char.MatchContextBase):

    def __init__(self, state, pattern_codes, offset=0):
        self.state = state
        self.pattern_codes = pattern_codes
        self.string_position = state.string_position
        self.code_position = offset
        self.has_matched = self.UNDECIDED
        self.backup = []
        self.resume_at_opcode = -1

    def push_new_context(self, pattern_offset):
        """Creates a new child context of this context and pushes it on the
        stack. pattern_offset is the offset off the current code position to
        start interpreting from."""
        offset = self.code_position + pattern_offset
        assert offset >= 0
        child_context = MatchContext(self.state, self.pattern_codes, offset)
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
        return self.state.get_char_ord(self.string_position + peek)

    def skip_char(self, skip_count):
        self.string_position = self.string_position + skip_count

    def remaining_chars(self):
        return self.state.end - self.string_position

    def at_beginning(self):
        return self.string_position == 0

    def at_end(self):
        return self.string_position == self.state.end

    def at_linebreak(self):
        return not self.at_end() and self.peek_char() == rsre_char.linebreak

    def at_boundary(self, word_checker):
        if self.at_beginning() and self.at_end():
            return False
        that = not self.at_beginning() and word_checker(self.peek_char(-1))
        this = not self.at_end()       and word_checker(self.peek_char())
        return this != that
    at_boundary._annspecialcase_ = 'specialize:arg(1)'


class RepeatContext(MatchContext):
    
    def __init__(self, context):
        offset = context.code_position
        assert offset >= 0
        MatchContext.__init__(self, context.state,
                                context.pattern_codes, offset)
        self.count = -1
        self.previous = context.state.repeat
        self.last_position = -1
        self.repeat_stack = []

StateMixin._MatchContext = MatchContext    # for tests

#### Main opcode dispatch loop

def search(state, pattern_codes):
    flags = 0
    if pattern_codes[0] == OPCODE_INFO:
        # optimization info block
        # <INFO> <1=skip> <2=flags> <3=min> <4=max> <5=prefix info>
        if pattern_codes[2] & SRE_INFO_PREFIX and pattern_codes[5] > 1:
            return fast_search(state, pattern_codes)
        flags = pattern_codes[2]
        offset = pattern_codes[1] + 1
        assert offset >= 0
        #pattern_codes = pattern_codes[offset:]

    string_position = state.start
    while string_position <= state.end:
        state.reset()
        state.start = state.string_position = string_position
        if match(state, pattern_codes):
            return True
        string_position += 1
    return False

def fast_search(state, pattern_codes):
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
    assert overlap_offset >= 0
    pattern_offset = pattern_codes[1] + 1
    assert pattern_offset >= 0
    i = 0
    string_position = state.string_position
    while string_position < state.end:
        while True:
            char_ord = state.get_char_ord(string_position)
            if char_ord != prefix[i]:
                if i == 0:
                    break
                else:
                    i = pattern_codes[overlap_offset + i]
            else:
                i += 1
                if i == prefix_len:
                    # found a potential match
                    state.start = string_position + 1 - prefix_len
                    state.string_position = string_position + 1 \
                                                 - prefix_len + prefix_skip
                    if flags & SRE_INFO_LITERAL:
                        return True # matched all of pure literal pattern
                    start = pattern_offset + 2 * prefix_skip
                    if match(state, pattern_codes[start:]):
                        return True
                    i = pattern_codes[overlap_offset + i]
                break
        string_position += 1
    return False

def match(state, pattern_codes):
    # Optimization: Check string length. pattern_codes[3] contains the
    # minimum length for a string to possibly match.
    if pattern_codes[0] == OPCODE_INFO and pattern_codes[3] > 0:
        if state.end - state.string_position < pattern_codes[3]:
            return False
    state.context_stack.append(MatchContext(state, pattern_codes))
    has_matched = MatchContext.UNDECIDED
    while len(state.context_stack) > 0:
        context = state.context_stack[-1]
        if context.has_matched == context.UNDECIDED:
            has_matched = dispatch_loop(context)
        else:
            has_matched = context.has_matched
        if has_matched != context.UNDECIDED: # don't pop if context isn't done
            state.context_stack.pop()
    return has_matched == MatchContext.MATCHED

def dispatch_loop(context):
    """Returns MATCHED if the current context matches, NOT_MATCHED if it doesn't
    and UNDECIDED if matching is not finished, ie must be resumed after child
    contexts have been matched."""
    while context.has_remaining_codes() and context.has_matched == context.UNDECIDED:
        if context.is_resumed():
            opcode = context.resume_at_opcode
        else:
            opcode = context.peek_code()
        try:
            has_finished = opcode_dispatch_table[opcode](context)
        except IndexError:
            raise RuntimeError("Internal re error. Unknown opcode: %s" % opcode)
        if not has_finished:
            context.resume_at_opcode = opcode
            return context.UNDECIDED
        context.resume_at_opcode = -1
    if context.has_matched == context.UNDECIDED:
        context.has_matched = context.NOT_MATCHED
    return context.has_matched

def op_success(ctx):
    # end of pattern
    ctx.state.string_position = ctx.string_position
    ctx.has_matched = ctx.MATCHED
    return True

def op_failure(ctx):
    # immediate failure
    ctx.has_matched = ctx.NOT_MATCHED
    return True

def op_literal(ctx):
    # match literal string
    # <LITERAL> <code>
    if ctx.at_end() or ctx.peek_char() != ctx.peek_code(1):
        ctx.has_matched = ctx.NOT_MATCHED
    ctx.skip_code(2)
    ctx.skip_char(1)
    return True

def op_not_literal(ctx):
    # match anything that is not the given literal character
    # <NOT_LITERAL> <code>
    if ctx.at_end() or ctx.peek_char() == ctx.peek_code(1):
        ctx.has_matched = ctx.NOT_MATCHED
    ctx.skip_code(2)
    ctx.skip_char(1)
    return True

def op_literal_ignore(ctx):
    # match literal regardless of case
    # <LITERAL_IGNORE> <code>
    if ctx.at_end() or \
      ctx.state.lower(ctx.peek_char()) != ctx.state.lower(ctx.peek_code(1)):
        ctx.has_matched = ctx.NOT_MATCHED
    ctx.skip_code(2)
    ctx.skip_char(1)
    return True

def op_not_literal_ignore(ctx):
    # match literal regardless of case
    # <LITERAL_IGNORE> <code>
    if ctx.at_end() or \
      ctx.state.lower(ctx.peek_char()) == ctx.state.lower(ctx.peek_code(1)):
        ctx.has_matched = ctx.NOT_MATCHED
    ctx.skip_code(2)
    ctx.skip_char(1)
    return True

def op_at(ctx):
    # match at given position
    # <AT> <code>
    if not at_dispatch(ctx.peek_code(1), ctx):
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    ctx.skip_code(2)
    return True

def op_category(ctx):
    # match at given category
    # <CATEGORY> <code>
    if ctx.at_end() or \
            not rsre_char.category_dispatch(ctx.peek_code(1), ctx.peek_char()):
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    ctx.skip_code(2)
    ctx.skip_char(1)
    return True

def op_any(ctx):
    # match anything (except a newline)
    # <ANY>
    if ctx.at_end() or ctx.at_linebreak():
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    ctx.skip_code(1)
    ctx.skip_char(1)
    return True

def op_any_all(ctx):
    # match anything
    # <ANY_ALL>
    if ctx.at_end():
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    ctx.skip_code(1)
    ctx.skip_char(1)
    return True

def general_op_in(ctx, ignore=False):
    if ctx.at_end():
        ctx.has_matched = ctx.NOT_MATCHED
        return
    skip = ctx.peek_code(1)
    ctx.skip_code(2) # set op pointer to the set code
    char_code = ctx.peek_char()
    if ignore:
        char_code = ctx.state.lower(char_code)
    if not rsre_char.check_charset(char_code, ctx):
        ctx.has_matched = ctx.NOT_MATCHED
        return
    ctx.skip_code(skip - 1)
    ctx.skip_char(1)

def op_in(ctx):
    # match set member (or non_member)
    # <IN> <skip> <set>
    general_op_in(ctx)
    return True

def op_in_ignore(ctx):
    # match set member (or non_member), disregarding case of current char
    # <IN_IGNORE> <skip> <set>
    general_op_in(ctx, ignore=True)
    return True

def op_branch(ctx):
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

def op_repeat_one(ctx):
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
        count = count_repetitions(ctx, maxcount)
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

def op_min_repeat_one(ctx):
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
            count = count_repetitions(ctx, mincount)
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
        if count_repetitions(ctx, 1) == 0:
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

def op_repeat(ctx):
    # create repeat context.  all the hard work is done by the UNTIL
    # operator (MAX_UNTIL, MIN_UNTIL)
    # <REPEAT> <skip> <1=min> <2=max> item <UNTIL> tail
    if not ctx.is_resumed():
        ctx.repeat = RepeatContext(ctx)
        ctx.state.repeat = ctx.repeat
        ctx.state.string_position = ctx.string_position
        ctx.push_new_context(ctx.peek_code(1) + 1)
        return False
    else:
        ctx.state.repeat = ctx.repeat
        ctx.has_matched = ctx.child_context.has_matched
        return True

def op_max_until(ctx):
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

def op_min_until(ctx):
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

def op_jump(ctx):
    # jump forward
    # <JUMP>/<INFO> <offset>
    ctx.skip_code(ctx.peek_code(1) + 1)
    return True

def op_mark(ctx):
    # set mark
    # <MARK> <gid>
    ctx.state.set_mark(ctx.peek_code(1), ctx.string_position)
    ctx.skip_code(2)
    return True

def general_op_groupref(ctx, ignore=False):
    group_start, group_end = ctx.state.get_marks(ctx.peek_code(1))
    if group_start == -1 or group_end == -1 or group_end < group_start \
                            or group_end - group_start > ctx.remaining_chars():
        ctx.has_matched = ctx.NOT_MATCHED
        return True
    while group_start < group_end:
        new_char = ctx.peek_char()
        old_char = ctx.state.get_char_ord(group_start)
        if ctx.at_end() or (not ignore and old_char != new_char) \
                or (ignore and ctx.state.lower(old_char) != ctx.state.lower(new_char)):
            ctx.has_matched = ctx.NOT_MATCHED
            return True
        group_start += 1
        ctx.skip_char(1)
    ctx.skip_code(2)
    return True

def op_groupref(ctx):
    # match backreference
    # <GROUPREF> <zero-based group index>
    return general_op_groupref(ctx)

def op_groupref_ignore(ctx):
    # match backreference case-insensitive
    # <GROUPREF_IGNORE> <zero-based group index>
    return general_op_groupref(ctx, ignore=True)

def op_groupref_exists(ctx):
    # <GROUPREF_EXISTS> <group> <skip> codeyes <JUMP> codeno ...
    group_start, group_end = ctx.state.get_marks(ctx.peek_code(1))
    if group_start == -1 or group_end == -1 or group_end < group_start:
        ctx.skip_code(ctx.peek_code(2) + 1)
    else:
        ctx.skip_code(3)
    return True

def op_assert(ctx):
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

def op_assert_not(ctx):
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

def count_repetitions(ctx, maxcount):
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
        opcode_dispatch_table[ctx.peek_code()](ctx)
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

##### At dispatch

def at_dispatch(atcode, context):
    try:
        function, negate = at_dispatch_table[atcode]
    except IndexError:
        return False
    result = function(context)
    if negate:
        return not result
    else:
        return result

def at_beginning(ctx):
    return ctx.at_beginning()

def at_beginning_line(ctx):
    return ctx.at_beginning() or ctx.peek_char(-1) == rsre_char.linebreak
    
def at_end(ctx):
    return ctx.at_end() or (ctx.remaining_chars() == 1 and ctx.at_linebreak())

def at_end_line(ctx):
    return ctx.at_linebreak() or ctx.at_end()

def at_end_string(ctx):
    return ctx.at_end()

def at_boundary(ctx):
    return ctx.at_boundary(rsre_char.is_word)

def at_loc_boundary(ctx):
    return ctx.at_boundary(rsre_char.is_loc_word)

def at_uni_boundary(ctx):
    return ctx.at_boundary(rsre_char.is_uni_word)

# Maps opcodes by indices to (function, negate) tuples.
at_dispatch_table = [
    (at_beginning, False), (at_beginning_line, False), (at_beginning, False),
    (at_boundary, False), (at_boundary, True),
    (at_end, False), (at_end_line, False), (at_end_string, False),
    (at_loc_boundary, False), (at_loc_boundary, True), (at_uni_boundary, False),
    (at_uni_boundary, True)
]
