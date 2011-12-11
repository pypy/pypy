import sys
from pypy.rlib.debug import check_nonneg
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rsre import rsre_char
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import jit
from pypy.rlib.rsre.rsre_jit import install_jitdriver, install_jitdriver_spec


OPCODE_FAILURE            = 0
OPCODE_SUCCESS            = 1
OPCODE_ANY                = 2
OPCODE_ANY_ALL            = 3
OPCODE_ASSERT             = 4
OPCODE_ASSERT_NOT         = 5
OPCODE_AT                 = 6
OPCODE_BRANCH             = 7
#OPCODE_CALL              = 8
OPCODE_CATEGORY           = 9
#OPCODE_CHARSET           = 10
#OPCODE_BIGCHARSET        = 11
OPCODE_GROUPREF           = 12
OPCODE_GROUPREF_EXISTS    = 13
OPCODE_GROUPREF_IGNORE    = 14
OPCODE_IN                 = 15
OPCODE_IN_IGNORE          = 16
OPCODE_INFO               = 17
OPCODE_JUMP               = 18
OPCODE_LITERAL            = 19
OPCODE_LITERAL_IGNORE     = 20
OPCODE_MARK               = 21
OPCODE_MAX_UNTIL          = 22
OPCODE_MIN_UNTIL          = 23
OPCODE_NOT_LITERAL        = 24
OPCODE_NOT_LITERAL_IGNORE = 25
#OPCODE_NEGATE            = 26
#OPCODE_RANGE             = 27
OPCODE_REPEAT             = 28
OPCODE_REPEAT_ONE         = 29
#OPCODE_SUBPATTERN        = 30
OPCODE_MIN_REPEAT_ONE     = 31

# ____________________________________________________________

_seen_specname = {}

def specializectx(func):
    """A decorator that specializes 'func(ctx,...)' for each concrete subclass
    of AbstractMatchContext.  During annotation, if 'ctx' is known to be a
    specific subclass, calling 'func' is a direct call; if 'ctx' is only known
    to be of class AbstractMatchContext, calling 'func' is an indirect call.
    """
    assert func.func_code.co_varnames[0] == 'ctx'
    specname = '_spec_' + func.func_name
    while specname in _seen_specname:
        specname += '_'
    _seen_specname[specname] = True
    # Install a copy of the function under the name '_spec_funcname' in each
    # concrete subclass
    specialized_methods = []
    for prefix, concreteclass in [('str', StrMatchContext),
                                  ('uni', UnicodeMatchContext)]:
        newfunc = func_with_new_name(func, prefix + specname)
        assert not hasattr(concreteclass, specname)
        setattr(concreteclass, specname, newfunc)
        specialized_methods.append(newfunc)
    # Return a dispatcher function, specialized on the exact type of 'ctx'
    def dispatch(ctx, *args):
        return getattr(ctx, specname)(*args)
    dispatch._annspecialcase_ = 'specialize:argtype(0)'
    dispatch._specialized_methods_ = specialized_methods
    return func_with_new_name(dispatch, specname)

# ____________________________________________________________

class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

class AbstractMatchContext(object):
    """Abstract base class"""
    _immutable_fields_ = ['pattern[*]', 'flags', 'end']
    match_start = 0
    match_end = 0
    match_marks = None
    match_marks_flat = None

    def __init__(self, pattern, match_start, end, flags):
        # 'match_start' and 'end' must be known to be non-negative
        # and they must not be more than len(string).
        check_nonneg(match_start)
        check_nonneg(end)
        self.pattern = pattern
        self.match_start = match_start
        self.end = end
        self.flags = flags

    def reset(self, start):
        self.match_start = start
        self.match_marks = None
        self.match_marks_flat = None

    def pat(self, index):
        check_nonneg(index)
        result = self.pattern[index]
        # Check that we only return non-negative integers from this helper.
        # It is possible that self.pattern contains negative integers
        # (see set_charset() and set_bigcharset() in rsre_char.py)
        # but they should not be fetched via this helper here.
        assert result >= 0
        return result

    def str(self, index):
        """NOT_RPYTHON: Must be overridden in a concrete subclass.
        The tag ^^^ here is used to generate a translation-time crash
        if there is a call to str() that is indirect.  All calls must
        be direct for performance reasons; you need to specialize the
        caller with @specializectx."""
        raise NotImplementedError

    def lowstr(self, index):
        """NOT_RPYTHON: Similar to str()."""
        raise NotImplementedError

    def get_mark(self, gid):
        return find_mark(self.match_marks, gid)

    def flatten_marks(self):
        # for testing
        if self.match_marks_flat is None:
            self.match_marks_flat = [self.match_start, self.match_end]
            mark = self.match_marks
            if mark is not None:
                self.match_lastindex = mark.gid
            else:
                self.match_lastindex = -1
            while mark is not None:
                index = mark.gid + 2
                while index >= len(self.match_marks_flat):
                    self.match_marks_flat.append(-1)
                if self.match_marks_flat[index] == -1:
                    self.match_marks_flat[index] = mark.position
                mark = mark.prev
            self.match_marks = None    # clear
        return self.match_marks_flat

    def span(self, groupnum=0):
        # compatibility
        fmarks = self.flatten_marks()
        groupnum *= 2
        if groupnum >= len(fmarks):
            return (-1, -1)
        return (fmarks[groupnum], fmarks[groupnum+1])

    def group(self, groupnum=0):
        frm, to = self.span(groupnum)
        if 0 <= frm <= to:
            return self._string[frm:to]
        else:
            return None

    def fresh_copy(self, start):
        raise NotImplementedError

class StrMatchContext(AbstractMatchContext):
    """Concrete subclass for matching in a plain string."""

    def __init__(self, pattern, string, match_start, end, flags):
        AbstractMatchContext.__init__(self, pattern, match_start, end, flags)
        self._string = string
        if not we_are_translated() and isinstance(string, unicode):
            self.flags |= rsre_char.SRE_FLAG_UNICODE   # for rsre_re.py

    def str(self, index):
        check_nonneg(index)
        return ord(self._string[index])

    def lowstr(self, index):
        c = self.str(index)
        return rsre_char.getlower(c, self.flags)

    def fresh_copy(self, start):
        return StrMatchContext(self.pattern, self._string, start,
                               self.end, self.flags)

class UnicodeMatchContext(AbstractMatchContext):
    """Concrete subclass for matching in a unicode string."""

    def __init__(self, pattern, unicodestr, match_start, end, flags):
        AbstractMatchContext.__init__(self, pattern, match_start, end, flags)
        self._unicodestr = unicodestr

    def str(self, index):
        check_nonneg(index)
        return ord(self._unicodestr[index])

    def lowstr(self, index):
        c = self.str(index)
        return rsre_char.getlower(c, self.flags)

    def fresh_copy(self, start):
        return UnicodeMatchContext(self.pattern, self._unicodestr, start,
                                   self.end, self.flags)

# ____________________________________________________________

class Mark(object):
    _immutable_ = True

    def __init__(self, gid, position, prev):
        self.gid = gid
        self.position = position
        self.prev = prev      # chained list

def find_mark(mark, gid):
    while mark is not None:
        if mark.gid == gid:
            return mark.position
        mark = mark.prev
    return -1

# ____________________________________________________________

class MatchResult(object):
    subresult = None

    def move_to_next_result(self, ctx):
        # returns either 'self' or None
        result = self.subresult
        if result is None:
            return
        if result.move_to_next_result(ctx):
            return self
        return self.find_next_result(ctx)

    def find_next_result(self, ctx):
        raise NotImplementedError

MATCHED_OK = MatchResult()

class BranchMatchResult(MatchResult):

    def __init__(self, ppos, ptr, marks):
        self.ppos = ppos
        self.start_ptr = ptr
        self.start_marks = marks

    @jit.unroll_safe
    def find_first_result(self, ctx):
        ppos = jit.hint(self.ppos, promote=True)
        while ctx.pat(ppos):
            result = sre_match(ctx, ppos + 1, self.start_ptr, self.start_marks)
            ppos += ctx.pat(ppos)
            if result is not None:
                self.subresult = result
                self.ppos = ppos
                return self
    find_next_result = find_first_result

class RepeatOneMatchResult(MatchResult):
    install_jitdriver('RepeatOne',
                      greens=['nextppos', 'ctx.pattern'],
                      reds=['ptr', 'self', 'ctx'],
                      debugprint=(1, 0))   # indices in 'greens'

    def __init__(self, nextppos, minptr, ptr, marks):
        self.nextppos = nextppos
        self.minptr = minptr
        self.start_ptr = ptr
        self.start_marks = marks

    def find_first_result(self, ctx):
        ptr = self.start_ptr
        nextppos = self.nextppos
        while ptr >= self.minptr:
            ctx.jitdriver_RepeatOne.jit_merge_point(
                self=self, ptr=ptr, ctx=ctx, nextppos=nextppos)
            result = sre_match(ctx, nextppos, ptr, self.start_marks)
            ptr -= 1
            if result is not None:
                self.subresult = result
                self.start_ptr = ptr
                return self
    find_next_result = find_first_result


class MinRepeatOneMatchResult(MatchResult):
    install_jitdriver('MinRepeatOne',
                      greens=['nextppos', 'ppos3', 'ctx.pattern'],
                      reds=['ptr', 'self', 'ctx'],
                      debugprint=(2, 0))   # indices in 'greens'

    def __init__(self, nextppos, ppos3, maxptr, ptr, marks):
        self.nextppos = nextppos
        self.ppos3 = ppos3
        self.maxptr = maxptr
        self.start_ptr = ptr
        self.start_marks = marks

    def find_first_result(self, ctx):
        ptr = self.start_ptr
        nextppos = self.nextppos
        ppos3 = self.ppos3
        while ptr <= self.maxptr:
            ctx.jitdriver_MinRepeatOne.jit_merge_point(
                self=self, ptr=ptr, ctx=ctx, nextppos=nextppos, ppos3=ppos3)
            result = sre_match(ctx, nextppos, ptr, self.start_marks)
            if result is not None:
                self.subresult = result
                self.start_ptr = ptr
                return self
            if not self.next_char_ok(ctx, ptr, ppos3):
                break
            ptr += 1

    def find_next_result(self, ctx):
        ptr = self.start_ptr
        if not self.next_char_ok(ctx, ptr, self.ppos3):
            return
        self.start_ptr = ptr + 1
        return self.find_first_result(ctx)

    def next_char_ok(self, ctx, ptr, ppos):
        if ptr == ctx.end:
            return False
        op = ctx.pat(ppos)
        for op1, checkerfn in unroll_char_checker:
            if op1 == op:
                return checkerfn(ctx, ptr, ppos)
        raise Error("next_char_ok[%d]" % op)

class AbstractUntilMatchResult(MatchResult):

    def __init__(self, ppos, tailppos, ptr, marks):
        self.ppos = ppos
        self.tailppos = tailppos
        self.cur_ptr = ptr
        self.cur_marks = marks
        self.pending = None
        self.num_pending = 0

class Pending(object):
    def __init__(self, ptr, marks, enum, next):
        self.ptr = ptr
        self.marks = marks
        self.enum = enum
        self.next = next     # chained list

class MaxUntilMatchResult(AbstractUntilMatchResult):
    install_jitdriver('MaxUntil',
                      greens=['ppos', 'tailppos', 'match_more', 'ctx.pattern'],
                      reds=['ptr', 'marks', 'self', 'ctx'],
                      debugprint=(3, 0, 2))

    def find_first_result(self, ctx):
        return self.search_next(ctx, match_more=True)

    def find_next_result(self, ctx):
        return self.search_next(ctx, match_more=False)

    def search_next(self, ctx, match_more):
        ppos = self.ppos
        tailppos = self.tailppos
        ptr = self.cur_ptr
        marks = self.cur_marks
        while True:
            ctx.jitdriver_MaxUntil.jit_merge_point(
                ppos=ppos, tailppos=tailppos, match_more=match_more,
                ptr=ptr, marks=marks, self=self, ctx=ctx)
            if match_more:
                max = ctx.pat(ppos+2)
                if max == 65535 or self.num_pending < max:
                    # try to match one more 'item'
                    enum = sre_match(ctx, ppos + 3, ptr, marks)
                else:
                    enum = None    # 'max' reached, no more matches
            else:
                p = self.pending
                if p is None:
                    return
                self.pending = p.next
                self.num_pending -= 1
                ptr = p.ptr
                marks = p.marks
                enum = p.enum.move_to_next_result(ctx)
            #
            # zero-width match protection
            min = ctx.pat(ppos+1)
            if self.num_pending >= min:
                while enum is not None and ptr == ctx.match_end:
                    enum = enum.move_to_next_result(ctx)
                    # matched marks for zero-width assertions
                    marks = ctx.match_marks
            #
            if enum is not None:
                # matched one more 'item'.  record it and continue.
                self.pending = Pending(ptr, marks, enum, self.pending)
                self.num_pending += 1
                ptr = ctx.match_end
                marks = ctx.match_marks
                match_more = True
            else:
                # 'item' no longer matches.
                if self.num_pending >= min:
                    # try to match 'tail' if we have enough 'item'
                    result = sre_match(ctx, tailppos, ptr, marks)
                    if result is not None:
                        self.subresult = result
                        self.cur_ptr = ptr
                        self.cur_marks = marks
                        return self
                match_more = False

class MinUntilMatchResult(AbstractUntilMatchResult):

    def find_first_result(self, ctx):
        return self.search_next(ctx, resume=False)

    def find_next_result(self, ctx):
        return self.search_next(ctx, resume=True)

    def search_next(self, ctx, resume):
        # XXX missing jit support here
        ppos = self.ppos
        min = ctx.pat(ppos+1)
        max = ctx.pat(ppos+2)
        ptr = self.cur_ptr
        marks = self.cur_marks
        while True:
            # try to match 'tail' if we have enough 'item'
            if not resume and self.num_pending >= min:
                result = sre_match(ctx, self.tailppos, ptr, marks)
                if result is not None:
                    self.subresult = result
                    self.cur_ptr = ptr
                    self.cur_marks = marks
                    return self
            resume = False

            if max == 65535 or self.num_pending < max:
                # try to match one more 'item'
                enum = sre_match(ctx, ppos + 3, ptr, marks)
                #
                # zero-width match protection
                if self.num_pending >= min:
                    while enum is not None and ptr == ctx.match_end:
                        enum = enum.move_to_next_result(ctx)
            else:
                enum = None    # 'max' reached, no more matches

            while enum is None:
                # 'item' does not match; try to get further results from
                # the 'pending' list.
                p = self.pending
                if p is None:
                    return
                self.pending = p.next
                self.num_pending -= 1
                ptr = p.ptr
                marks = p.marks
                enum = p.enum.move_to_next_result(ctx)

            # matched one more 'item'.  record it and continue
            self.pending = Pending(ptr, marks, enum, self.pending)
            self.num_pending += 1
            ptr = ctx.match_end
            marks = ctx.match_marks

# ____________________________________________________________

@specializectx
@jit.unroll_safe
def sre_match(ctx, ppos, ptr, marks):
    """Returns either None or a MatchResult object.  Usually we only need
    the first result, but there is the case of REPEAT...UNTIL where we
    need all results; in that case we use the method move_to_next_result()
    of the MatchResult."""
    while True:
        op = ctx.pat(ppos)
        ppos += 1

        #jit.jit_debug("sre_match", op, ppos, ptr)
        #
        # When using the JIT, calls to sre_match() must always have a constant
        # (green) argument for 'ppos'.  If not, the following assert fails.
        jit.assert_green(op)

        if op == OPCODE_FAILURE:
            return

        if (op == OPCODE_SUCCESS or
            op == OPCODE_MAX_UNTIL or
            op == OPCODE_MIN_UNTIL):
            ctx.match_end = ptr
            ctx.match_marks = marks
            return MATCHED_OK

        elif op == OPCODE_ANY:
            # match anything (except a newline)
            # <ANY>
            if ptr >= ctx.end or rsre_char.is_linebreak(ctx.str(ptr)):
                return
            ptr += 1

        elif op == OPCODE_ANY_ALL:
            # match anything
            # <ANY_ALL>
            if ptr >= ctx.end:
                return
            ptr += 1

        elif op == OPCODE_ASSERT:
            # assert subpattern
            # <ASSERT> <0=skip> <1=back> <pattern>
            ptr1 = ptr - ctx.pat(ppos+1)
            if ptr1 < 0 or sre_match(ctx, ppos + 2, ptr1, marks) is None:
                return
            marks = ctx.match_marks
            ppos += ctx.pat(ppos)

        elif op == OPCODE_ASSERT_NOT:
            # assert not subpattern
            # <ASSERT_NOT> <0=skip> <1=back> <pattern>
            ptr1 = ptr - ctx.pat(ppos+1)
            if ptr1 >= 0 and sre_match(ctx, ppos + 2, ptr1, marks) is not None:
                return
            ppos += ctx.pat(ppos)

        elif op == OPCODE_AT:
            # match at given position (e.g. at beginning, at boundary, etc.)
            # <AT> <code>
            if not sre_at(ctx, ctx.pat(ppos), ptr):
                return
            ppos += 1

        elif op == OPCODE_BRANCH:
            # alternation
            # <BRANCH> <0=skip> code <JUMP> ... <NULL>
            result = BranchMatchResult(ppos, ptr, marks)
            return result.find_first_result(ctx)

        elif op == OPCODE_CATEGORY:
            # seems to be never produced, but used by some tests from
            # pypy/module/_sre/test
            # <CATEGORY> <category>
            if (ptr == ctx.end or
                not rsre_char.category_dispatch(ctx.pat(ppos), ctx.str(ptr))):
                return
            ptr += 1
            ppos += 1

        elif op == OPCODE_GROUPREF:
            # match backreference
            # <GROUPREF> <groupnum>
            startptr, length = get_group_ref(marks, ctx.pat(ppos))
            if length < 0:
                return     # group was not previously defined
            if not match_repeated(ctx, ptr, startptr, length):
                return     # no match
            ptr += length
            ppos += 1

        elif op == OPCODE_GROUPREF_IGNORE:
            # match backreference
            # <GROUPREF> <groupnum>
            startptr, length = get_group_ref(marks, ctx.pat(ppos))
            if length < 0:
                return     # group was not previously defined
            if not match_repeated_ignore(ctx, ptr, startptr, length):
                return     # no match
            ptr += length
            ppos += 1

        elif op == OPCODE_GROUPREF_EXISTS:
            # conditional match depending on the existence of a group
            # <GROUPREF_EXISTS> <group> <skip> codeyes <JUMP> codeno ...
            _, length = get_group_ref(marks, ctx.pat(ppos))
            if length >= 0:
                ppos += 2                  # jump to 'codeyes'
            else:
                ppos += ctx.pat(ppos+1)    # jump to 'codeno'

        elif op == OPCODE_IN:
            # match set member (or non_member)
            # <IN> <skip> <set>
            if ptr >= ctx.end or not rsre_char.check_charset(ctx.pattern,
                                                             ppos+1,
                                                             ctx.str(ptr)):
                return
            ppos += ctx.pat(ppos)
            ptr += 1

        elif op == OPCODE_IN_IGNORE:
            # match set member (or non_member), ignoring case
            # <IN> <skip> <set>
            if ptr >= ctx.end or not rsre_char.check_charset(ctx.pattern,
                                                             ppos+1,
                                                             ctx.lowstr(ptr)):
                return
            ppos += ctx.pat(ppos)
            ptr += 1

        elif op == OPCODE_INFO:
            # optimization info block
            # <INFO> <0=skip> <1=flags> <2=min> ...
            if (ctx.end - ptr) < ctx.pat(ppos+2):
                return
            ppos += ctx.pat(ppos)

        elif op == OPCODE_JUMP:
            ppos += ctx.pat(ppos)

        elif op == OPCODE_LITERAL:
            # match literal string
            # <LITERAL> <code>
            if ptr >= ctx.end or ctx.str(ptr) != ctx.pat(ppos):
                return
            ppos += 1
            ptr += 1

        elif op == OPCODE_LITERAL_IGNORE:
            # match literal string, ignoring case
            # <LITERAL_IGNORE> <code>
            if ptr >= ctx.end or ctx.lowstr(ptr) != ctx.pat(ppos):
                return
            ppos += 1
            ptr += 1

        elif op == OPCODE_MARK:
            # set mark
            # <MARK> <gid>
            gid = ctx.pat(ppos)
            marks = Mark(gid, ptr, marks)
            ppos += 1

        elif op == OPCODE_NOT_LITERAL:
            # match if it's not a literal string
            # <NOT_LITERAL> <code>
            if ptr >= ctx.end or ctx.str(ptr) == ctx.pat(ppos):
                return
            ppos += 1
            ptr += 1

        elif op == OPCODE_NOT_LITERAL_IGNORE:
            # match if it's not a literal string, ignoring case
            # <NOT_LITERAL> <code>
            if ptr >= ctx.end or ctx.lowstr(ptr) == ctx.pat(ppos):
                return
            ppos += 1
            ptr += 1

        elif op == OPCODE_REPEAT:
            # general repeat.  in this version of the re module, all the work
            # is done here, and not on the later UNTIL operator.
            # <REPEAT> <skip> <1=min> <2=max> item <UNTIL> tail
            # FIXME: we probably need to deal with zero-width matches in here..

            # decode the later UNTIL operator to see if it is actually
            # a MAX_UNTIL or MIN_UNTIL
            untilppos = ppos + ctx.pat(ppos)
            tailppos = untilppos + 1
            op = ctx.pat(untilppos)
            if op == OPCODE_MAX_UNTIL:
                # the hard case: we have to match as many repetitions as
                # possible, followed by the 'tail'.  we do this by
                # remembering each state for each possible number of
                # 'item' matching.
                result = MaxUntilMatchResult(ppos, tailppos, ptr, marks)
                return result.find_first_result(ctx)

            elif op == OPCODE_MIN_UNTIL:
                # first try to match the 'tail', and if it fails, try
                # to match one more 'item' and try again
                result = MinUntilMatchResult(ppos, tailppos, ptr, marks)
                return result.find_first_result(ctx)

            else:
                raise Error("missing UNTIL after REPEAT")

        elif op == OPCODE_REPEAT_ONE:
            # match repeated sequence (maximizing regexp).
            # this operator only works if the repeated item is
            # exactly one character wide, and we're not already
            # collecting backtracking points.  for other cases,
            # use the MAX_REPEAT operator.
            # <REPEAT_ONE> <skip> <1=min> <2=max> item <SUCCESS> tail
            start = ptr
            minptr = start + ctx.pat(ppos+1)
            if minptr > ctx.end:
                return    # cannot match
            ptr = find_repetition_end(ctx, ppos+3, start, ctx.pat(ppos+2))
            # when we arrive here, ptr points to the tail of the target
            # string.  check if the rest of the pattern matches,
            # and backtrack if not.
            nextppos = ppos + ctx.pat(ppos)
            result = RepeatOneMatchResult(nextppos, minptr, ptr, marks)
            return result.find_first_result(ctx)

        elif op == OPCODE_MIN_REPEAT_ONE:
            # match repeated sequence (minimizing regexp).
            # this operator only works if the repeated item is
            # exactly one character wide, and we're not already
            # collecting backtracking points.  for other cases,
            # use the MIN_REPEAT operator.
            # <MIN_REPEAT_ONE> <skip> <1=min> <2=max> item <SUCCESS> tail
            start = ptr
            min = ctx.pat(ppos+1)
            if min > 0:
                minptr = ptr + min
                if minptr > ctx.end:
                    return   # cannot match
                # count using pattern min as the maximum
                ptr = find_repetition_end(ctx, ppos+3, ptr, min)
                if ptr < minptr:
                    return   # did not match minimum number of times

            maxptr = ctx.end
            max = ctx.pat(ppos+2)
            if max != 65535:
                maxptr1 = start + max
                if maxptr1 <= maxptr:
                    maxptr = maxptr1
            nextppos = ppos + ctx.pat(ppos)
            result = MinRepeatOneMatchResult(nextppos, ppos+3, maxptr,
                                             ptr, marks)
            return result.find_first_result(ctx)

        else:
            raise Error("bad pattern code %d" % op)


def get_group_ref(marks, groupnum):
    gid = groupnum * 2
    startptr = find_mark(marks, gid)
    if startptr < 0:
        return 0, -1
    endptr = find_mark(marks, gid + 1)
    length = endptr - startptr     # < 0 if endptr < startptr (or if endptr=-1)
    return startptr, length

@specializectx
def match_repeated(ctx, ptr, oldptr, length):
    if ptr + length > ctx.end:
        return False
    for i in range(length):
        if ctx.str(ptr + i) != ctx.str(oldptr + i):
            return False
    return True

@specializectx
def match_repeated_ignore(ctx, ptr, oldptr, length):
    if ptr + length > ctx.end:
        return False
    for i in range(length):
        if ctx.lowstr(ptr + i) != ctx.lowstr(oldptr + i):
            return False
    return True

@specializectx
def find_repetition_end(ctx, ppos, ptr, maxcount):
    end = ctx.end
    ptrp1 = ptr + 1
    # First get rid of the cases where we don't have room for any match.
    if maxcount <= 0 or ptrp1 > end:
        return ptr
    # Check the first character directly.  If it doesn't match, we are done.
    # The idea is to be fast for cases like re.search("b+"), where we expect
    # the common case to be a non-match.  It's much faster with the JIT to
    # have the non-match inlined here rather than detect it in the fre() call.
    op = ctx.pat(ppos)
    for op1, checkerfn in unroll_char_checker:
        if op1 == op:
            if checkerfn(ctx, ptr, ppos):
                break
    else:
        return ptr
    # It matches at least once.  If maxcount == 1 (relatively common),
    # then we are done.
    if maxcount == 1:
        return ptrp1
    # Else we really need to count how many times it matches.
    if maxcount != 65535:
        # adjust end
        end1 = ptr + maxcount
        if end1 <= end:
            end = end1
    op = ctx.pat(ppos)
    for op1, fre in unroll_fre_checker:
        if op1 == op:
            return fre(ctx, ptrp1, end, ppos)
    raise Error("rsre.find_repetition_end[%d]" % op)

@specializectx
def match_ANY(ctx, ptr, ppos):   # dot wildcard.
    return not rsre_char.is_linebreak(ctx.str(ptr))
def match_ANY_ALL(ctx, ptr, ppos):
    return True    # match anything (including a newline)
@specializectx
def match_IN(ctx, ptr, ppos):
    return rsre_char.check_charset(ctx.pattern, ppos+2, ctx.str(ptr))
@specializectx
def match_IN_IGNORE(ctx, ptr, ppos):
    return rsre_char.check_charset(ctx.pattern, ppos+2, ctx.lowstr(ptr))
@specializectx
def match_LITERAL(ctx, ptr, ppos):
    return ctx.str(ptr) == ctx.pat(ppos+1)
@specializectx
def match_LITERAL_IGNORE(ctx, ptr, ppos):
    return ctx.lowstr(ptr) == ctx.pat(ppos+1)
@specializectx
def match_NOT_LITERAL(ctx, ptr, ppos):
    return ctx.str(ptr) != ctx.pat(ppos+1)
@specializectx
def match_NOT_LITERAL_IGNORE(ctx, ptr, ppos):
    return ctx.lowstr(ptr) != ctx.pat(ppos+1)

def _make_fre(checkerfn):
    if checkerfn == match_ANY_ALL:
        def fre(ctx, ptr, end, ppos):
            return end
    elif checkerfn == match_IN:
        install_jitdriver_spec('MatchIn',
                               greens=['ppos', 'ctx.pattern'],
                               reds=['ptr', 'end', 'ctx'],
                               debugprint=(1, 0))
        @specializectx
        def fre(ctx, ptr, end, ppos):
            while True:
                ctx.jitdriver_MatchIn.jit_merge_point(ctx=ctx, ptr=ptr,
                                                      end=end, ppos=ppos)
                if ptr < end and checkerfn(ctx, ptr, ppos):
                    ptr += 1
                else:
                    return ptr
    elif checkerfn == match_IN_IGNORE:
        install_jitdriver_spec('MatchInIgnore',
                               greens=['ppos', 'ctx.pattern'],
                               reds=['ptr', 'end', 'ctx'],
                               debugprint=(1, 0))
        @specializectx
        def fre(ctx, ptr, end, ppos):
            while True:
                ctx.jitdriver_MatchInIgnore.jit_merge_point(ctx=ctx, ptr=ptr,
                                                            end=end, ppos=ppos)
                if ptr < end and checkerfn(ctx, ptr, ppos):
                    ptr += 1
                else:
                    return ptr
    else:
        # in the other cases, the fre() function is not JITted at all
        # and is present as a residual call.
        @specializectx
        def fre(ctx, ptr, end, ppos):
            while ptr < end and checkerfn(ctx, ptr, ppos):
                ptr += 1
            return ptr
    fre = func_with_new_name(fre, 'fre_' + checkerfn.__name__)
    return fre

unroll_char_checker = [
    (OPCODE_ANY,                match_ANY),
    (OPCODE_ANY_ALL,            match_ANY_ALL),
    (OPCODE_IN,                 match_IN),
    (OPCODE_IN_IGNORE,          match_IN_IGNORE),
    (OPCODE_LITERAL,            match_LITERAL),
    (OPCODE_LITERAL_IGNORE,     match_LITERAL_IGNORE),
    (OPCODE_NOT_LITERAL,        match_NOT_LITERAL),
    (OPCODE_NOT_LITERAL_IGNORE, match_NOT_LITERAL_IGNORE),
    ]
unroll_fre_checker = [(_op, _make_fre(_fn))
                      for (_op, _fn) in unroll_char_checker]

unroll_char_checker = unrolling_iterable(unroll_char_checker)
unroll_fre_checker  = unrolling_iterable(unroll_fre_checker)

##### At dispatch

AT_BEGINNING = 0
AT_BEGINNING_LINE = 1
AT_BEGINNING_STRING = 2
AT_BOUNDARY = 3
AT_NON_BOUNDARY = 4
AT_END = 5
AT_END_LINE = 6
AT_END_STRING = 7
AT_LOC_BOUNDARY = 8
AT_LOC_NON_BOUNDARY = 9
AT_UNI_BOUNDARY = 10
AT_UNI_NON_BOUNDARY = 11

@specializectx
def sre_at(ctx, atcode, ptr):
    if (atcode == AT_BEGINNING or
        atcode == AT_BEGINNING_STRING):
        return ptr == 0

    elif atcode == AT_BEGINNING_LINE:
        prevptr = ptr - 1
        return prevptr < 0 or rsre_char.is_linebreak(ctx.str(prevptr))

    elif atcode == AT_BOUNDARY:
        return at_boundary(ctx, ptr)

    elif atcode == AT_NON_BOUNDARY:
        return at_non_boundary(ctx, ptr)

    elif atcode == AT_END:
        remaining_chars = ctx.end - ptr
        return remaining_chars <= 0 or (
            remaining_chars == 1 and rsre_char.is_linebreak(ctx.str(ptr)))

    elif atcode == AT_END_LINE:
        return ptr == ctx.end or rsre_char.is_linebreak(ctx.str(ptr))

    elif atcode == AT_END_STRING:
        return ptr == ctx.end

    elif atcode == AT_LOC_BOUNDARY:
        return at_loc_boundary(ctx, ptr)

    elif atcode == AT_LOC_NON_BOUNDARY:
        return at_loc_non_boundary(ctx, ptr)

    elif atcode == AT_UNI_BOUNDARY:
        return at_uni_boundary(ctx, ptr)

    elif atcode == AT_UNI_NON_BOUNDARY:
        return at_uni_non_boundary(ctx, ptr)

    return False

def _make_boundary(word_checker):
    @specializectx
    def at_boundary(ctx, ptr):
        if ctx.end == 0:
            return False
        prevptr = ptr - 1
        that = prevptr >= 0 and word_checker(ctx.str(prevptr))
        this = ptr < ctx.end and word_checker(ctx.str(ptr))
        return this != that
    @specializectx
    def at_non_boundary(ctx, ptr):
        if ctx.end == 0:
            return False
        prevptr = ptr - 1
        that = prevptr >= 0 and word_checker(ctx.str(prevptr))
        this = ptr < ctx.end and word_checker(ctx.str(ptr))
        return this == that
    return at_boundary, at_non_boundary

at_boundary, at_non_boundary = _make_boundary(rsre_char.is_word)
at_loc_boundary, at_loc_non_boundary = _make_boundary(rsre_char.is_loc_word)
at_uni_boundary, at_uni_non_boundary = _make_boundary(rsre_char.is_uni_word)

# ____________________________________________________________

def _adjust(start, end, length):
    if start < 0: start = 0
    elif start > length: start = length
    if end < 0: end = 0
    elif end > length: end = length
    return start, end

def match(pattern, string, start=0, end=sys.maxint, flags=0):
    start, end = _adjust(start, end, len(string))
    ctx = StrMatchContext(pattern, string, start, end, flags)
    if match_context(ctx):
        return ctx
    else:
        return None

def search(pattern, string, start=0, end=sys.maxint, flags=0):
    start, end = _adjust(start, end, len(string))
    ctx = StrMatchContext(pattern, string, start, end, flags)
    if search_context(ctx):
        return ctx
    else:
        return None

install_jitdriver('Match',
                  greens=['ctx.pattern'], reds=['ctx'],
                  debugprint=(0,))

def match_context(ctx):
    ctx.original_pos = ctx.match_start
    if ctx.end < ctx.match_start:
        return False
    ctx.jitdriver_Match.jit_merge_point(ctx=ctx)
    return sre_match(ctx, 0, ctx.match_start, None) is not None

def search_context(ctx):
    ctx.original_pos = ctx.match_start
    if ctx.end < ctx.match_start:
        return False
    base = 0
    charset = False
    if ctx.pat(base) == OPCODE_INFO:
        flags = ctx.pat(2)
        if flags & rsre_char.SRE_INFO_PREFIX:
            if ctx.pat(5) > 1:
                return fast_search(ctx)
        else:
            charset = (flags & rsre_char.SRE_INFO_CHARSET)
        base += 1 + ctx.pat(1)
    if ctx.pat(base) == OPCODE_LITERAL:
        return literal_search(ctx, base)
    if charset:
        return charset_search(ctx, base)
    return regular_search(ctx, base)

install_jitdriver('RegularSearch',
                  greens=['base', 'ctx.pattern'],
                  reds=['start', 'ctx'],
                  debugprint=(1, 0))

def regular_search(ctx, base):
    start = ctx.match_start
    while start <= ctx.end:
        ctx.jitdriver_RegularSearch.jit_merge_point(ctx=ctx, start=start,
                                                    base=base)
        if sre_match(ctx, base, start, None) is not None:
            ctx.match_start = start
            return True
        start += 1
    return False

install_jitdriver_spec("LiteralSearch",
                       greens=['base', 'character', 'ctx.pattern'],
                       reds=['start', 'ctx'],
                       debugprint=(2, 0, 1))
@specializectx
def literal_search(ctx, base):
    # pattern starts with a literal character.  this is used
    # for short prefixes, and if fast search is disabled
    character = ctx.pat(base + 1)
    base += 2
    start = ctx.match_start
    while start < ctx.end:
        ctx.jitdriver_LiteralSearch.jit_merge_point(ctx=ctx, start=start,
                                          base=base, character=character)
        if ctx.str(start) == character:
            if sre_match(ctx, base, start + 1, None) is not None:
                ctx.match_start = start
                return True
        start += 1
    return False

install_jitdriver_spec("CharsetSearch",
                       greens=['base', 'ctx.pattern'],
                       reds=['start', 'ctx'],
                       debugprint=(1, 0))
@specializectx
def charset_search(ctx, base):
    # pattern starts with a character from a known set
    start = ctx.match_start
    while start < ctx.end:
        ctx.jitdriver_CharsetSearch.jit_merge_point(ctx=ctx, start=start,
                                                    base=base)
        if rsre_char.check_charset(ctx.pattern, 5, ctx.str(start)):
            if sre_match(ctx, base, start, None) is not None:
                ctx.match_start = start
                return True
        start += 1
    return False

install_jitdriver_spec('FastSearch',
                       greens=['i', 'prefix_len', 'ctx.pattern'],
                       reds=['string_position', 'ctx'],
                       debugprint=(2, 0))
@specializectx
def fast_search(ctx):
    # skips forward in a string as fast as possible using information from
    # an optimization info block
    # <INFO> <1=skip> <2=flags> <3=min> <4=...>
    #        <5=length> <6=skip> <7=prefix data> <overlap data>
    string_position = ctx.match_start
    if string_position >= ctx.end:
        return False
    prefix_len = ctx.pat(5)
    assert prefix_len >= 0
    i = 0
    while True:
        ctx.jitdriver_FastSearch.jit_merge_point(ctx=ctx,
                string_position=string_position, i=i, prefix_len=prefix_len)
        char_ord = ctx.str(string_position)
        if char_ord != ctx.pat(7 + i):
            if i > 0:
                overlap_offset = prefix_len + (7 - 1)
                i = ctx.pat(overlap_offset + i)
                continue
        else:
            i += 1
            if i == prefix_len:
                # found a potential match
                start = string_position + 1 - prefix_len
                assert start >= 0
                prefix_skip = ctx.pat(6)
                ptr = start + prefix_skip
                #flags = ctx.pat(2)
                #if flags & rsre_char.SRE_INFO_LITERAL:
                #    # matched all of pure literal pattern
                #    ctx.match_start = start
                #    ctx.match_end = ptr
                #    ctx.match_marks = None
                #    return True
                pattern_offset = ctx.pat(1) + 1
                ppos_start = pattern_offset + 2 * prefix_skip
                if sre_match(ctx, ppos_start, ptr, None) is not None:
                    ctx.match_start = start
                    return True
                overlap_offset = prefix_len + (7 - 1)
                i = ctx.pat(overlap_offset + i)
        string_position += 1
        if string_position >= ctx.end:
            return False
