from __future__ import print_function
import sys
from rpython.rlib.debug import check_nonneg
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.rsre import rsre_char, rsre_constants as consts
from rpython.tool.sourcetools import func_with_new_name
from rpython.rlib.objectmodel import we_are_translated, not_rpython
from rpython.rlib.nonconst import NonConstant
from rpython.rlib import jit
from rpython.rlib.rsre.rsre_jit import install_jitdriver, install_jitdriver_spec, opname

_seen_specname = {}

def specializectx(func, **kwargs):
    """A decorator that specializes 'func(ctx,...)' for each concrete subclass
    of AbstractMatchContext.  During annotation, if 'ctx' is known to be a
    specific subclass, calling 'func' is a direct call; if 'ctx' is only known
    to be of class AbstractMatchContext, calling 'func' is an indirect call.
    """
    from rpython.rlib.rsre.rsre_utf8 import Utf8MatchContext

    assert func.func_code.co_varnames[0] == 'ctx'
    specname = '_spec_' + func.func_name
    while specname in _seen_specname:
        specname += '_'
    _seen_specname[specname] = True
    # Install a copy of the function under the name '_spec_funcname' in each
    # concrete subclass
    specialized_methods = []
    for prefix, concreteclass in [('buf', BufMatchContext),
                                  ('str', StrMatchContext),
                                  ('uni', UnicodeMatchContext),
                                  ('utf8', Utf8MatchContext),
                                  ]:
        override = "override_" + prefix
        newfunc = kwargs.get(override)
        if newfunc is None:
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

def specializectx_override(**kwargs):
    def decorate(func):
        return specializectx(func, **kwargs)
    return decorate

# ____________________________________________________________

class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

class EndOfString(Exception):
    pass

class CompiledPattern(object):
    _immutable_fields_ = ['pattern[*]', 'flags']

    def __init__(self, pattern, flags, repr=None):
        self.pattern = pattern
        self.flags = flags
        self.repr = repr
    
    def pat(self, index):
        jit.promote(self)
        check_nonneg(index)
        result = self.pattern[index]
        # Check that we only return non-negative integers from this helper.
        # It is possible that self.pattern contains negative integers
        # (see set_charset() and set_bigcharset() in rsre_char.py)
        # but they should not be fetched via this helper here.
        assert result >= 0
        return result

    def dis(self):
        # stolen from CPython
        code = self.pattern

        def _hex_code(code):
            return '[%s]' % ', '.join('%#0*x' % (consts.CODESIZE*2+2, x) for x in code)

        labels = set()
        offset_width = len(str(len(code) - 1))

        def dis_(start, end, level=0):
            def print_(*args, **kwargs):
                to = kwargs.pop('to', None)
                assert not kwargs
                if to is not None:
                    labels.add(to)
                    args += ('(to %d)' % (to,),)
                print('%*d%s ' % (offset_width, start, ':' if start in labels else '.'),
                      end='  '*(level-1))
                print(*args)

            def print_2(*args):
                print(end=' '*(offset_width + 2*level))
                print(*args)

            level += 1
            i = start
            while i < end:
                start = i
                op = code[i]
                opname = consts.opnames[op]
                i += 1
                if op in (consts.OPCODE_SUCCESS, consts.OPCODE_FAILURE, consts.OPCODE_ANY, consts.OPCODE_ANY_ALL,
                          consts.OPCODE_MAX_UNTIL, consts.OPCODE_MIN_UNTIL, consts.OPCODE_NEGATE):
                    print_(opname)
                elif op in (consts.OPCODE_LITERAL, consts.OPCODE_NOT_LITERAL,
                        consts.OPCODE_LITERAL_IGNORE, consts.OPCODE_NOT_LITERAL_IGNORE):
                    arg = code[i]
                    i += 1
                    print_(opname, u'%#02x (%r)' % (arg, unichr(arg)))
                elif op is consts.OPCODE_AT:
                    arg = code[i]
                    i += 1
                    arg = str(consts.ATCODES[arg])
                    assert arg[:3] == 'AT_'
                    print_(opname, arg[3:])
                elif op is consts.OPCODE_CATEGORY:
                    arg = code[i]
                    i += 1
                    arg = str(consts.CHCODES[arg])
                    assert arg[:9] == 'CATEGORY_'
                    print_(opname, arg[9:])
                elif op in (consts.OPCODE_IN, consts.OPCODE_IN_IGNORE):
                    skip = code[i]
                    print_(opname, skip, to=i+skip)
                    dis_(i+1, i+skip)
                    i += skip
                elif op == consts.OPCODE_RANGE:
                    lo, hi = code[i: i+2]
                    i += 2
                    print_(opname, u'%#02x %#02x (%r-%r)' % (lo, hi, unichr(lo), unichr(hi)))
                elif op is consts.OPCODE_CHARSET:
                    print_(opname, _hex_code(code[i: i + 256//consts._CODEBITS]))
                    i += 256//consts._CODEBITS
                elif op is consts.OPCODE_BIGCHARSET:
                    arg = code[i]
                    i += 1
                    print_(opname, arg, code[i: i + 256//consts.CODESIZE])
                    i += 256//consts.CODESIZE
                    level += 1
                    for j in range(arg):
                        print_2(_hex_code(code[i: i + 256//consts._CODEBITS]))
                        i += 256//consts._CODEBITS
                    level -= 1
                elif op in (consts.OPCODE_MARK, consts.OPCODE_GROUPREF, consts.OPCODE_GROUPREF_IGNORE):
                    arg = code[i]
                    i += 1
                    print_(opname, arg)
                elif op is consts.OPCODE_JUMP:
                    skip = code[i]
                    print_(opname, skip, to=i+skip)
                    i += 1
                elif op is consts.OPCODE_BRANCH:
                    skip = code[i]
                    print_(opname, skip, to=i+skip)
                    while skip:
                        dis_(i+1, i+skip)
                        i += skip
                        start = i
                        skip = code[i]
                        if skip:
                            print_('branch', skip, to=i+skip)
                        else:
                            print_(consts.OPCODE_FAILURE)
                    i += 1
                elif op in (consts.OPCODE_REPEAT, consts.OPCODE_REPEAT_ONE, consts.OPCODE_MIN_REPEAT_ONE):
                    skip, min, max = code[i: i+3]
                    if max == consts.MAXREPEAT:
                        max = 'MAXREPEAT'
                    print_(opname, skip, min, max, to=i+skip)
                    dis_(i+3, i+skip)
                    i += skip
                elif op is consts.OPCODE_GROUPREF_EXISTS:
                    arg, skip = code[i: i+2]
                    print_(opname, arg, skip, to=i+skip)
                    i += 2
                elif op in (consts.OPCODE_ASSERT, consts.OPCODE_ASSERT_NOT):
                    skip, arg = code[i: i+2]
                    print_(opname, skip, arg, to=i+skip)
                    dis_(i+2, i+skip)
                    i += skip
                elif op is consts.OPCODE_INFO:
                    skip, flags, min, max = code[i: i+4]
                    if max == consts.MAXREPEAT:
                        max = 'MAXREPEAT'
                    print_(opname, skip, bin(flags), min, max, to=i+skip)
                    start = i+4
                    if flags & consts.SRE_INFO_PREFIX:
                        prefix_len, prefix_skip = code[i+4: i+6]
                        print_2('  prefix_skip', prefix_skip)
                        start = i + 6
                        prefix = code[start: start+prefix_len]
                        print_2('  prefix',
                                '[%s]' % ', '.join('%#02x' % x for x in prefix),
                                u'(%r)' % u''.join(map(unichr, prefix)))
                        start += prefix_len
                        print_2('  overlap', code[start: start+prefix_len])
                        start += prefix_len
                    if flags & consts.SRE_INFO_CHARSET:
                        level += 1
                        print_2('in')
                        dis_(start, i+skip, level=level)
                        level -= 1
                    i += skip
                else:
                    raise ValueError(opname)

            level -= 1

        dis_(0, len(code))



class AbstractMatchContext(object):
    """Abstract base class"""
    _immutable_fields_ = ['end']
    match_start = 0
    match_end = 0
    match_marks = None
    match_marks_flat = None
    fullmatch_only = False

    def __init__(self, match_start, end):
        # 'match_start' and 'end' must be known to be non-negative
        # and they must not be more than len(string).
        check_nonneg(match_start)
        check_nonneg(end)
        self.match_start = match_start
        self.end = end

    def reset(self, start):
        self.match_start = start
        self.match_marks = None
        self.match_marks_flat = None

    @not_rpython
    def str(self, index):
        """Must be overridden in a concrete subclass.
        The tag ^^^ here is used to generate a translation-time crash
        if there is a call to str() that is indirect.  All calls must
        be direct for performance reasons; you need to specialize the
        caller with @specializectx."""
        raise NotImplementedError

    @not_rpython
    def lowstr(self, index, flags):
        """Similar to str()."""
        raise NotImplementedError

    # The following methods are provided to be overriden in
    # Utf8MatchContext.  The non-utf8 implementation is provided
    # by the FixedMatchContext abstract subclass, in order to use
    # the same @not_rpython safety trick as above.  If you get a
    # "not_rpython" error during translation, either consider
    # calling the methods xxx_indirect() instead of xxx(), or if
    # applicable add the @specializectx decorator.
    ZERO = 0
    @not_rpython
    def next(self, position):
        raise NotImplementedError
    @not_rpython
    def prev(self, position):
        raise NotImplementedError
    @not_rpython
    def next_n(self, position, n, end_position):
        raise NotImplementedError
    @not_rpython
    def prev_n(self, position, n, start_position):
        raise NotImplementedError
    @not_rpython
    def debug_check_pos(self, position):
        raise NotImplementedError
    @not_rpython
    def maximum_distance(self, position_low, position_high):
        raise NotImplementedError
    @not_rpython
    def get_single_byte(self, base_position, index):
        raise NotImplementedError
    def matches_literal(self, position, ordch):
        """ Check whether the string matches ordch at position. ordch is
        usually green. """
        raise NotImplementedError
    @not_rpython
    def matches_many_literals(self, ptr, pattern, ppos, n):
        """ match n literal bytecodes in pattern at position ppos against the
        string in ctx, at position ptr. Return -1 on non-match, and the new ptr
        on match. """
        raise NotImplementedError

    def bytes_difference(self, position1, position2):
        return position1 - position2
    def go_forward_by_bytes(self, base_position, index):
        return base_position + index
    def next_indirect(self, position):
        assert position < self.end
        return position + 1     # like next(), but can be called indirectly
    def prev_indirect(self, position):
        position -= 1           # like prev(), but can be called indirectly
        if position < 0:
            raise EndOfString
        return position

    def get_mark(self, gid):
        return find_mark(self.match_marks, gid)

    def flatten_marks(self):
        # for testing
        if self.match_marks_flat is None:
            self._compute_flattened_marks()
        return self.match_marks_flat

    def _compute_flattened_marks(self):
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

class FixedMatchContext(AbstractMatchContext):
    """Abstract subclass to introduce the default implementation for
    these position methods.  The Utf8MatchContext subclass doesn't
    inherit from here."""

    next = AbstractMatchContext.next_indirect
    prev = AbstractMatchContext.prev_indirect

    def next_n(self, position, n, end_position):
        position += n
        if position > end_position:
            raise EndOfString
        return position

    def prev_n(self, position, n, start_position):
        position -= n
        if position < start_position:
            raise EndOfString
        return position

    def debug_check_pos(self, position):
        pass

    def maximum_distance(self, position_low, position_high):
        return position_high - position_low

    @jit.unroll_safe
    def matches_many_literals(self, ptr, pattern, ppos, n):
        assert ppos >= 0
        # do a single range check
        try:
            endpos = self.next_n(ptr, n, self.end)
        except EndOfString:
            return -1
        for i in range(n):
            ordch = pattern.pat(ppos + 2 * i + 1)
            if not self.matches_literal(ptr, ordch):
                return -1
            ptr = self.next(ptr)
        return endpos


class BufMatchContext(FixedMatchContext):
    """Concrete subclass for matching in a buffer."""

    _immutable_fields_ = ["_buffer"]

    def __init__(self, buf, match_start, end):
        FixedMatchContext.__init__(self, match_start, end)
        self._buffer = buf

    def str(self, index):
        check_nonneg(index)
        return ord(self._buffer.getitem(index))

    def lowstr(self, index, flags):
        c = self.str(index)
        return rsre_char.getlower(c, flags)

    def fresh_copy(self, start):
        return BufMatchContext(self._buffer, start,
                               self.end)

    def get_single_byte(self, base_position, index):
        return self.str(base_position + index)

    def matches_literal(self, position, ordch):
        return self.str(position) == ordch


class StrMatchContext(FixedMatchContext):
    """Concrete subclass for matching in a plain string."""

    _immutable_fields_ = ["_string"]

    def __init__(self, string, match_start, end):
        FixedMatchContext.__init__(self, match_start, end)
        self._string = string

    def str(self, index):
        check_nonneg(index)
        return ord(self._string[index])

    def lowstr(self, index, flags):
        c = self.str(index)
        return rsre_char.getlower(c, flags)

    def fresh_copy(self, start):
        return StrMatchContext(self._string, start,
                               self.end)

    def get_single_byte(self, base_position, index):
        return self.str(base_position + index)

    def _real_pos(self, index):
        return index     # overridden by tests

    def matches_literal(self, position, ordch):
        return self.str(position) == ordch

class UnicodeMatchContext(FixedMatchContext):
    """Concrete subclass for matching in a unicode string."""

    _immutable_fields_ = ["_unicodestr"]

    def __init__(self, unicodestr, match_start, end):
        FixedMatchContext.__init__(self, match_start, end)
        self._unicodestr = unicodestr

    def str(self, index):
        check_nonneg(index)
        return ord(self._unicodestr[index])

    def lowstr(self, index, flags):
        c = self.str(index)
        return rsre_char.getlower(c, flags)

    def fresh_copy(self, start):
        return UnicodeMatchContext(self._unicodestr, start,
                                   self.end)

    def get_single_byte(self, base_position, index):
        return self.str(base_position + index)

    def matches_literal(self, position, ordch):
        return self.str(position) == ordch
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

    def move_to_next_result(self, ctx, pattern):
        # returns either 'self' or None
        result = self.subresult
        if result is None:
            return
        if result.move_to_next_result(ctx, pattern):
            return self
        return self.find_next_result(ctx, pattern)

    def find_next_result(self, ctx, pattern):
        raise NotImplementedError

MATCHED_OK = MatchResult()

class BranchMatchResult(MatchResult):

    def __init__(self, ppos, ptr, marks):
        check_nonneg(ppos)
        self.ppos = ppos
        self.start_ptr = ptr
        self.start_marks = marks

    @jit.unroll_safe
    def find_first_result(self, ctx, pattern):
        ppos = jit.promote(self.ppos)
        assert ppos >= 0
        while True:
            result = sre_match(ctx, pattern, ppos + 1, self.start_ptr, self.start_marks)
            offset = pattern.pat(ppos)
            if pattern.pat(ppos + offset) == 0:
                # we're in the last branch. backtracking to self won't produce
                # more. just return result
                return result
            ppos += offset
            if result is not None:
                self.subresult = result
                self.ppos = ppos
                return self
    find_next_result = find_first_result

class RepeatOneMatchResult(MatchResult):
    install_jitdriver('RepeatOne',
                      greens=['nextppos', 'pattern'],
                      reds=['ptr', 'self', 'ctx'],
                      debugprint=(1, 0))   # indices in 'greens'

    def __init__(self, nextppos, minptr, ptr, marks):
        self.nextppos = nextppos
        self.minptr = minptr
        self.start_ptr = ptr
        self.start_marks = marks

    def find_first_result(self, ctx, pattern):
        ptr = self.start_ptr
        nextppos = self.nextppos
        while ptr >= self.minptr:
            ctx.jitdriver_RepeatOne.jit_merge_point(
                self=self, ptr=ptr, ctx=ctx, nextppos=nextppos,
                pattern=pattern)
            result = sre_match(ctx, pattern, nextppos, ptr, self.start_marks)
            try:
                ptr = ctx.prev_indirect(ptr)
            except EndOfString:
                ptr = -1
            if result is not None:
                self.subresult = result
                self.start_ptr = ptr
                return self
    find_next_result = find_first_result


class MinRepeatOneMatchResult(MatchResult):
    install_jitdriver('MinRepeatOne',
                      greens=['nextppos', 'ppos3', 'pattern'],
                      reds=['max_count', 'ptr', 'self', 'ctx'],
                      debugprint=(2, 0))   # indices in 'greens'

    def __init__(self, nextppos, ppos3, max_count, ptr, marks):
        self.nextppos = nextppos
        self.ppos3 = ppos3
        self.max_count = max_count
        self.start_ptr = ptr
        self.start_marks = marks

    def find_first_result(self, ctx, pattern):
        ptr = self.start_ptr
        nextppos = self.nextppos
        max_count = self.max_count
        ppos3 = self.ppos3
        while max_count >= 0:
            ctx.jitdriver_MinRepeatOne.jit_merge_point(
                self=self, ptr=ptr, ctx=ctx, nextppos=nextppos, ppos3=ppos3,
                max_count=max_count, pattern=pattern)
            result = sre_match(ctx, pattern, nextppos, ptr, self.start_marks)
            if result is not None:
                self.subresult = result
                self.start_ptr = ptr
                self.max_count = max_count
                return self
            if not self.next_char_ok(ctx, pattern, ptr, ppos3):
                break
            ptr = ctx.next_indirect(ptr)
            max_count -= 1

    def find_next_result(self, ctx, pattern):
        ptr = self.start_ptr
        if not self.next_char_ok(ctx, pattern, ptr, self.ppos3):
            return
        self.start_ptr = ctx.next_indirect(ptr)
        return self.find_first_result(ctx, pattern)

    def next_char_ok(self, ctx, pattern, ptr, ppos):
        if ptr == ctx.end:
            return False
        op = pattern.pat(ppos)
        for op1, checkerfn in unroll_char_checker:
            if op1 == op:
                return checkerfn(ctx, pattern, ptr, ppos)
        # obscure case: it should be a single char pattern, but isn't
        # one of the opcodes in unroll_char_checker (see test_ext_opcode)
        return sre_match(ctx, pattern, ppos, ptr, self.start_marks) is not None

class AbstractUntilMatchResult(MatchResult):

    def __init__(self, ppos, tailppos, ptr, marks):
        check_nonneg(ppos)
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
                      greens=['ppos', 'tailppos', 'match_more', 'pattern'],
                      reds=['ptr', 'marks', 'self', 'ctx'],
                      debugprint=(3, 0, 2))
    def find_first_result(self, ctx, pattern):
        return self.search_next(ctx, pattern, match_more=True)

    def find_next_result(self, ctx, pattern):
        return self.search_next(ctx, pattern, match_more=False)

    def search_next(self, ctx, pattern, match_more):
        ppos = self.ppos
        tailppos = self.tailppos
        ptr = self.cur_ptr
        marks = self.cur_marks
        while True:
            ctx.jitdriver_MaxUntil.jit_merge_point(
                ppos=ppos, tailppos=tailppos, match_more=match_more,
                ptr=ptr, marks=marks, self=self, ctx=ctx,
                pattern=pattern)
            if match_more:
                max = pattern.pat(ppos+2)
                if max == consts.MAXREPEAT or self.num_pending < max:
                    # try to match one more 'item'
                    enum = sre_match(ctx, pattern, ppos + 3, ptr, marks)
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
                enum = p.enum.move_to_next_result(ctx, pattern)
            #
            min = pattern.pat(ppos+1)
            if enum is not None:
                # matched one more 'item'.
                last_match_zero_length = (ctx.match_end == ptr)
                # note that num_pending is confusingly named and counts the
                # number of matches of the subpattern, not how many Pending
                # instances there are
                self.num_pending += 1
                # we record a Pending (a backtracking point) in one of two cases:
                # 1) if enum is itself complicated, ie potentially contains
                # backtracking points
                # 2) if enum is MatchResult we record only if the tail can
                # match and we already have enough matches
                if (type(enum) is not MatchResult or
                        (is_match_possible(ctx, ptr, pattern, tailppos) and
                            self.num_pending >= min)):
                    self.pending = Pending(ptr, marks, enum, self.pending)
                ptr = ctx.match_end
                marks = ctx.match_marks
                if last_match_zero_length and self.num_pending >= min:
                    # zero-width protection: after an empty match, if there
                    # are enough matches, don't try to match more.  Instead,
                    # fall through to trying to match 'tail'.
                    pass
                else:
                    match_more = True
                    continue

            # 'item' no longer matches.
            if self.num_pending >= min:
                # try to match 'tail' if we have enough 'item'
                result = sre_match(ctx, pattern, tailppos, ptr, marks)
                if result is not None:
                    self.subresult = result
                    self.cur_ptr = ptr
                    self.cur_marks = marks
                    return self
            match_more = False

class MinUntilMatchResult(AbstractUntilMatchResult):
    install_jitdriver('MinUntil',
                      greens=['ppos', 'tailppos', 'resume', 'min', 'max', 'pattern'],
                      reds=['ptr', 'marks', 'self', 'ctx'],
                      debugprint=(5, 0))


    def find_first_result(self, ctx, pattern):
        return self.search_next(ctx, pattern, resume=False)

    def find_next_result(self, ctx, pattern):
        return self.search_next(ctx, pattern, resume=True)

    def search_next(self, ctx, pattern, resume):
        ppos = self.ppos
        min = pattern.pat(ppos+1)
        max = pattern.pat(ppos+2)
        tailppos = self.tailppos
        ptr = self.cur_ptr
        marks = self.cur_marks
        while True:
            # try to match 'tail' if we have enough 'item'
            ctx.jitdriver_MinUntil.jit_merge_point(
                ppos=ppos, tailppos=tailppos, ptr=ptr, marks=marks, self=self,
                ctx=ctx, min=min, max=max, resume=resume, pattern=pattern)
            if not resume and self.num_pending >= min:
                result = sre_match(ctx, pattern, tailppos, ptr, marks)
                if result is not None:
                    self.subresult = result
                    self.cur_ptr = ptr
                    self.cur_marks = marks
                    return self
            resume = False

            if max == consts.MAXREPEAT or self.num_pending < max:
                # try to match one more 'item'
                enum = sre_match(ctx, pattern, ppos + 3, ptr, marks)
                #
                # zero-width match protection
                if self.num_pending >= min:
                    while enum is not None and ptr == ctx.match_end:
                        enum = enum.move_to_next_result(ctx, pattern)
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
                enum = p.enum.move_to_next_result(ctx, pattern)

            # matched one more 'item'.  record it and continue
            self.pending = Pending(ptr, marks, enum, self.pending)
            self.num_pending += 1
            ptr = ctx.match_end
            marks = ctx.match_marks

# ____________________________________________________________

@specializectx
@jit.unroll_safe
def sre_match(ctx, pattern, ppos, ptr, marks):
    """Returns either None or a MatchResult object.  Usually we only need
    the first result, but there is the case of REPEAT...UNTIL where we
    need all results; in that case we use the method move_to_next_result()
    of the MatchResult."""
    check_nonneg(ppos)
    while True:
        op = pattern.pat(ppos)
        ppos += 1

        jit.jit_debug(opname(op), op, ppos)
        #
        # When using the JIT, calls to sre_match() must always have a constant
        # (green) argument for 'ppos'.  If not, the following assert fails.
        jit.assert_green(op)

        if op == consts.OPCODE_FAILURE:
            return

        elif op == consts.OPCODE_SUCCESS:
            if ctx.fullmatch_only:
                if ptr != ctx.end:
                    return     # not a full match
            ctx.match_end = ptr
            ctx.match_marks = marks
            return MATCHED_OK

        elif (op == consts.OPCODE_MAX_UNTIL or
              op == consts.OPCODE_MIN_UNTIL):
            ctx.match_end = ptr
            ctx.match_marks = marks
            return MATCHED_OK

        elif op == consts.OPCODE_ANY:
            # match anything (except a newline)
            # <ANY>
            if ptr >= ctx.end or rsre_char.is_linebreak(ctx.str(ptr)):
                return
            ptr = ctx.next(ptr)

        elif op == consts.OPCODE_ANY_ALL:
            # match anything
            # <ANY_ALL>
            if ptr >= ctx.end:
                return
            ptr = ctx.next(ptr)

        elif op == consts.OPCODE_ASSERT:
            # assert subpattern
            # <ASSERT> <0=skip> <1=back> <pattern>
            try:
                ptr1 = ctx.prev_n(ptr, pattern.pat(ppos+1), ctx.ZERO)
            except EndOfString:
                return
            saved = ctx.fullmatch_only
            ctx.fullmatch_only = False
            stop = sre_match(ctx, pattern, ppos + 2, ptr1, marks) is None
            ctx.fullmatch_only = saved
            if stop:
                return
            marks = ctx.match_marks
            ppos += pattern.pat(ppos)

        elif op == consts.OPCODE_ASSERT_NOT:
            # assert not subpattern
            # <ASSERT_NOT> <0=skip> <1=back> <pattern>

            try:
                ptr1 = ctx.prev_n(ptr, pattern.pat(ppos+1), ctx.ZERO)
            except EndOfString:
                pass
            else:
                saved = ctx.fullmatch_only
                ctx.fullmatch_only = False
                stop = sre_match(ctx, pattern, ppos + 2, ptr1, marks) is not None
                ctx.fullmatch_only = saved
                if stop:
                    return
            ppos += pattern.pat(ppos)

        elif op == consts.OPCODE_AT:
            # match at given position (e.g. at beginning, at boundary, etc.)
            # <AT> <code>
            if not sre_at(ctx, pattern.pat(ppos), ptr):
                return
            ppos += 1

        elif op == consts.OPCODE_BRANCH:
            # alternation
            # <BRANCH> <0=skip> code <JUMP> ... <NULL>
            result = BranchMatchResult(ppos, ptr, marks)
            return result.find_first_result(ctx, pattern)

        elif op == consts.OPCODE_CATEGORY:
            # seems to be never produced, but used by some tests from
            # pypy/module/_sre/test
            # <CATEGORY> <category>
            if (ptr == ctx.end or
                not rsre_char.category_dispatch(pattern.pat(ppos), ctx.str(ptr))):
                return
            ptr = ctx.next(ptr)
            ppos += 1

        elif op == consts.OPCODE_GROUPREF:
            # match backreference
            # <GROUPREF> <groupnum>
            startptr, length_bytes = get_group_ref(ctx, marks, pattern.pat(ppos))
            if length_bytes < 0:
                return     # group was not previously defined
            if not match_repeated(ctx, ptr, startptr, length_bytes):
                return     # no match
            ptr = ctx.go_forward_by_bytes(ptr, length_bytes)
            ppos += 1

        elif op == consts.OPCODE_GROUPREF_IGNORE:
            # match backreference
            # <GROUPREF> <groupnum>
            startptr, length_bytes = get_group_ref(ctx, marks, pattern.pat(ppos))
            if length_bytes < 0:
                return     # group was not previously defined
            ptr = match_repeated_ignore(ctx, ptr, startptr, length_bytes, pattern.flags)
            if ptr < ctx.ZERO:
                return     # no match
            ppos += 1

        elif op == consts.OPCODE_GROUPREF_EXISTS:
            # conditional match depending on the existence of a group
            # <GROUPREF_EXISTS> <group> <skip> codeyes <JUMP> codeno ...
            _, length_bytes = get_group_ref(ctx, marks, pattern.pat(ppos))
            if length_bytes >= 0:
                ppos += 2                  # jump to 'codeyes'
            else:
                ppos += pattern.pat(ppos+1)    # jump to 'codeno'

        elif op == consts.OPCODE_IN:
            # match set member (or non_member)
            # <IN> <skip> <set>
            if ptr >= ctx.end or not rsre_char.check_charset(ctx, pattern, ppos+1,
                                                             ctx.str(ptr)):
                return
            ppos += pattern.pat(ppos)
            ptr = ctx.next(ptr)

        elif op == consts.OPCODE_IN_IGNORE:
            # match set member (or non_member), ignoring case
            # <IN> <skip> <set>
            if ptr >= ctx.end or not rsre_char.check_charset(ctx, pattern, ppos+1,
                                                             ctx.lowstr(ptr, pattern.flags)):
                return
            ppos += pattern.pat(ppos)
            ptr = ctx.next(ptr)

        elif op == consts.OPCODE_INFO:
            # optimization info block
            # <INFO> <0=skip> <1=flags> <2=min> ...
            if ctx.maximum_distance(ptr, ctx.end) < pattern.pat(ppos+2):
                return
            ppos += pattern.pat(ppos)

        elif op == consts.OPCODE_JUMP:
            ppos += pattern.pat(ppos)

        elif op == consts.OPCODE_LITERAL:
            # match literal string
            # <LITERAL> <code>

            # execute several LITERAL bytecodes in one go
            ppos_min_one = ppos - 1
            assert ppos_min_one >= 0
            n = number_literals(pattern, ppos_min_one)
            ptr = ctx.matches_many_literals(ptr, pattern, ppos_min_one, n)
            if ptr == -1: # no match
                return
            assert ptr >= 0
            ppos += 2 * n - 1
            assert ppos >= 0

        elif op == consts.OPCODE_LITERAL_IGNORE:
            # match literal string, ignoring case
            # <LITERAL_IGNORE> <code>
            if ptr >= ctx.end or ctx.lowstr(ptr, pattern.flags) != pattern.pat(ppos):
                return
            ppos += 1
            ptr = ctx.next(ptr)

        elif op == consts.OPCODE_MARK:
            # set mark
            # <MARK> <gid>
            gid = pattern.pat(ppos)
            marks = Mark(gid, ptr, marks)
            ppos += 1

        elif op == consts.OPCODE_NOT_LITERAL:
            # match if it's not a literal string
            # <NOT_LITERAL> <code>
            if ptr >= ctx.end or ctx.matches_literal(ptr, pattern.pat(ppos)):
                return
            ppos += 1
            ptr = ctx.next(ptr)

        elif op == consts.OPCODE_NOT_LITERAL_IGNORE:
            # match if it's not a literal string, ignoring case
            # <NOT_LITERAL> <code>
            if ptr >= ctx.end or ctx.lowstr(ptr, pattern.flags) == pattern.pat(ppos):
                return
            ppos += 1
            ptr = ctx.next(ptr)

        elif op == consts.OPCODE_REPEAT:
            # general repeat.  in this version of the re module, all the work
            # is done here, and not on the later UNTIL operator.
            # <REPEAT> <skip> <1=min> <2=max> item <UNTIL> tail
            # FIXME: we probably need to deal with zero-width matches in here..

            # decode the later UNTIL operator to see if it is actually
            # a MAX_UNTIL or MIN_UNTIL
            untilppos = ppos + pattern.pat(ppos)
            tailppos = untilppos + 1
            op = pattern.pat(untilppos)
            if op == consts.OPCODE_MAX_UNTIL:
                # the hard case: we have to match as many repetitions as
                # possible, followed by the 'tail'.  we do this by
                # remembering each state for each possible number of
                # 'item' matching.
                result = MaxUntilMatchResult(ppos, tailppos, ptr, marks)
                return result.find_first_result(ctx, pattern)

            elif op == consts.OPCODE_MIN_UNTIL:
                # first try to match the 'tail', and if it fails, try
                # to match one more 'item' and try again
                result = MinUntilMatchResult(ppos, tailppos, ptr, marks)
                return result.find_first_result(ctx, pattern)

            else:
                raise Error("missing UNTIL after REPEAT")

        elif op == consts.OPCODE_REPEAT_ONE:
            # match repeated sequence (maximizing regexp).
            # this operator only works if the repeated item is
            # exactly one character wide, and we're not already
            # collecting backtracking points.  for other cases,
            # use the MAX_REPEAT operator.
            # <REPEAT_ONE> <skip> <1=min> <2=max> item <SUCCESS> tail
            start = ptr

            min = pattern.pat(ppos+1)
            if min:
                try:
                    minptr = ctx.next_n(start, min, ctx.end)
                except EndOfString:
                    return    # cannot match
            else:
                minptr = start
            nextppos = ppos + pattern.pat(ppos)
            ptr = find_repetition_end(ctx, pattern, ppos+3, start,
                                      pattern.pat(ppos+2),
                                      marks, nextppos)
            if ptr < 0:
                exactly_one_match = True
                ptr = ~ptr
            else:
                exactly_one_match = False
            assert ptr >= 0
            # when we arrive here, ptr points to the tail of the target
            # string.  check if the rest of the pattern matches,
            # and backtrack if not.
            if ptr == start:
                # matches at most 0 times
                if min == 0:
                    # we don't need to make a RepeatOneMatchResult, since
                    # backtracking won't produce anything new anyway.
                    # XXX generalize this approach to min > 0
                    ppos = nextppos
                    continue
                else:
                    # minimum not reached!
                    return
            if exactly_one_match:
                # backtracking not useful, only one possible match
                ppos = nextppos
                continue
            result = RepeatOneMatchResult(nextppos, minptr, ptr, marks)
            return result.find_first_result(ctx, pattern)

        elif op == consts.OPCODE_MIN_REPEAT_ONE:
            # match repeated sequence (minimizing regexp).
            # this operator only works if the repeated item is
            # exactly one character wide, and we're not already
            # collecting backtracking points.  for other cases,
            # use the MIN_REPEAT operator.
            # <MIN_REPEAT_ONE> <skip> <1=min> <2=max> item <SUCCESS> tail
            start = ptr
            min = pattern.pat(ppos+1)
            if min > 0:
                try:
                    minptr = ctx.next_n(ptr, min, ctx.end)
                except EndOfString:
                    return    # cannot match
                # count using pattern min as the maximum
                ptr = find_repetition_end(ctx, pattern, ppos+3, ptr, min, marks)
                if ptr < 0:
                    ptr = ~ptr
                assert ptr >= 0
                if ptr < minptr:
                    return   # did not match minimum number of times

            max_count = sys.maxint
            max = pattern.pat(ppos+2)
            if max != consts.MAXREPEAT:
                max_count = max - min
                assert max_count >= 0
            nextppos = ppos + pattern.pat(ppos)
            result = MinRepeatOneMatchResult(nextppos, ppos+3, max_count,
                                             ptr, marks)
            return result.find_first_result(ctx, pattern)

        else:
            raise Error("bad pattern code %d" % op)

@jit.elidable
def number_literals(pattern, ppos):
    assert ppos >= 0
    n = 0
    while pattern.pat(ppos) == consts.OPCODE_LITERAL:
        ppos += 2
        n += 1
    return n

@specializectx
def is_match_possible(ctx, ptr, pattern, ppos):
    # look at 1 char at most to see whether a match is possible. don't mutate
    # ctx. it's always safe to return True
    op = pattern.pat(ppos)
    ppos += 1
    if op == consts.OPCODE_LITERAL:
        return not ptr >= ctx.end and ctx.matches_literal(ptr, pattern.pat(ppos))
    # XXX add more cases
    return True

def get_group_ref(ctx, marks, groupnum):
    gid = groupnum * 2
    startptr = find_mark(marks, gid)
    if startptr < ctx.ZERO:
        return 0, -1
    endptr = find_mark(marks, gid + 1)
    length_bytes = ctx.bytes_difference(endptr, startptr)
    return startptr, length_bytes

@specializectx
def match_repeated(ctx, ptr, oldptr, length_bytes):
    if ctx.bytes_difference(ctx.end, ptr) < length_bytes:
        return False
    for i in range(length_bytes):
        if ctx.get_single_byte(ptr, i) != ctx.get_single_byte(oldptr, i):
            return False
    return True

@specializectx
def match_repeated_ignore(ctx, ptr, oldptr, length_bytes, flags):
    oldend = ctx.go_forward_by_bytes(oldptr, length_bytes)
    while oldptr < oldend:
        if ptr >= ctx.end:
            return -1
        if ctx.lowstr(ptr, flags) != ctx.lowstr(oldptr, flags):
            return -1
        ptr = ctx.next(ptr)
        oldptr = ctx.next(oldptr)
    return ptr

@specializectx
def find_repetition_end(ctx, pattern, ppos, ptr, maxcount, marks, postcond_ppos=-1):
    end = ctx.end
    # First get rid of the cases where we don't have room for any match.
    if maxcount <= 0 or ptr >= end:
        return ptr
    # It matches at least once.  If maxcount == 1 (relatively common),
    # then we are done.
    # XXX
    #if maxcount == 1:
    #    return ptrp1
    # Else we really need to count how many times it matches.
    if maxcount != consts.MAXREPEAT:
        # adjust end
        try:
            end = ctx.next_n(ptr, maxcount, end)
        except EndOfString:
            pass
    op = pattern.pat(ppos)
    if op == consts.OPCODE_ANY_ALL:
        return end
    return find_repetition_end_jitted(ctx, pattern, ptr, end, ppos, maxcount, marks, postcond_ppos)

@specializectx
def general_find_repetition_end(ctx, pattern, ppos, ptr, maxcount, marks, postcond_ppos):
    # moved into its own JIT-opaque function
    end = ctx.end
    if maxcount != consts.MAXREPEAT:
        # adjust end
        end1 = ptr + maxcount
        if end1 <= end:
            end = end1
    while ptr < end and sre_match(ctx, pattern, ppos, ptr, marks) is not None:
        ptr = ctx.next(ptr)
    return ptr

@specializectx
def match_ANY(ctx, pattern, ptr, ppos):   # dot wildcard.
    return not rsre_char.is_linebreak(ctx.str(ptr))
def match_ANY_ALL(ctx, pattern, ptr, ppos):
    return True    # match anything (including a newline)
@specializectx
def match_IN(ctx, pattern, ptr, ppos):
    return rsre_char.check_charset(ctx, pattern, ppos+2, ctx.str(ptr))
@specializectx
def match_IN_IGNORE(ctx, pattern, ptr, ppos):
    return rsre_char.check_charset(ctx, pattern, ppos+2, ctx.lowstr(ptr, pattern.flags))
@specializectx
def match_LITERAL(ctx, pattern, ptr, ppos):
    return ctx.matches_literal(ptr, pattern.pat(ppos+1))
@specializectx
def match_LITERAL_IGNORE(ctx, pattern, ptr, ppos):
    return ctx.lowstr(ptr, pattern.flags) == pattern.pat(ppos+1)
@specializectx
def match_NOT_LITERAL(ctx, pattern, ptr, ppos):
    return not ctx.matches_literal(ptr, pattern.pat(ppos+1))
@specializectx
def match_NOT_LITERAL_IGNORE(ctx, pattern, ptr, ppos):
    return ctx.lowstr(ptr, pattern.flags) != pattern.pat(ppos+1)

install_jitdriver_spec("find_repetition_end",
                       greens=['ppos', 'postcond_ppos', 'pattern'],
                       reds='auto',
                       # always unroll one iteration to check the first
                       # character directly.  If it doesn't match, we are done.
                       # The idea is to be fast for cases like re.search("b+"),
                       # where we expect the common case to be a non-match.
                       # It's much faster with the JIT to have the non-match
                       # inlined in the caller rather than detect it in a
                       # call_assembler.
                       should_unroll_one_iteration=lambda *args: True,
                       is_recursive=True,
                       debugprint=(2, 0))
@specializectx
def find_repetition_end_jitted(ctx, pattern, ptr, end, ppos, maxcount, marks, postcond_ppos):
    exactly_one_match = True
    last_possible_match = -1
    startptr = ptr
    while True:
        jitdriver = ctx.jitdriver_find_repetition_end
        jitdriver.jit_merge_point(ppos=ppos,
                                  postcond_ppos=postcond_ppos,
                                  pattern=pattern)
        pattern_matches = False
        op = pattern.pat(ppos)
        if ptr < end:
            for op1, checkerfn in unroll_char_checker:
                if op1 == op:
                    pattern_matches = checkerfn(ctx, pattern, ptr, ppos)
                    break
            else:
                # obscure case: it should be a single char pattern, but isn't
                # one of the opcodes in unroll_char_checker (see test_ext_opcode)
                return general_find_repetition_end(ctx, pattern, ppos, ptr, maxcount, marks, postcond_ppos)
        if pattern_matches:
            # boolean promote, make sure that we get a guard_true before the
            # is_match_possible
            pass
        if postcond_ppos < 0 or is_match_possible(ctx, ptr, pattern, postcond_ppos):
            if last_possible_match >= 0:
                exactly_one_match = False
            last_possible_match = ptr
        if not pattern_matches:
            if last_possible_match < 0:
                return startptr
            if exactly_one_match:
                return ~last_possible_match
            return last_possible_match
        ptr = ctx.next(ptr)

unroll_char_checker = [
    (consts.OPCODE_ANY,                match_ANY),
    (consts.OPCODE_ANY_ALL,            match_ANY_ALL),
    (consts.OPCODE_IN,                 match_IN),
    (consts.OPCODE_IN_IGNORE,          match_IN_IGNORE),
    (consts.OPCODE_LITERAL,            match_LITERAL),
    (consts.OPCODE_LITERAL_IGNORE,     match_LITERAL_IGNORE),
    (consts.OPCODE_NOT_LITERAL,        match_NOT_LITERAL),
    (consts.OPCODE_NOT_LITERAL_IGNORE, match_NOT_LITERAL_IGNORE),
    ]

unroll_char_checker = unrolling_iterable(unroll_char_checker)

##### At dispatch

@specializectx
def sre_at(ctx, atcode, ptr):
    if (atcode == consts.AT_BEGINNING or
        atcode == consts.AT_BEGINNING_STRING):
        return ptr == ctx.ZERO

    elif atcode == consts.AT_BEGINNING_LINE:
        try:
            prevptr = ctx.prev(ptr)
        except EndOfString:
            return True
        return rsre_char.is_linebreak(ctx.str(prevptr))

    elif atcode == consts.AT_BOUNDARY:
        return at_boundary(ctx, ptr)

    elif atcode == consts.AT_NON_BOUNDARY:
        return at_non_boundary(ctx, ptr)

    elif atcode == consts.AT_END:
        return (ptr == ctx.end or
            (ctx.next(ptr) == ctx.end and rsre_char.is_linebreak(ctx.str(ptr))))

    elif atcode == consts.AT_END_LINE:
        return ptr == ctx.end or rsre_char.is_linebreak(ctx.str(ptr))

    elif atcode == consts.AT_END_STRING:
        return ptr == ctx.end

    elif atcode == consts.AT_LOC_BOUNDARY:
        return at_loc_boundary(ctx, ptr)

    elif atcode == consts.AT_LOC_NON_BOUNDARY:
        return at_loc_non_boundary(ctx, ptr)

    elif atcode == consts.AT_UNI_BOUNDARY:
        return at_uni_boundary(ctx, ptr)

    elif atcode == consts.AT_UNI_NON_BOUNDARY:
        return at_uni_non_boundary(ctx, ptr)

    return False

def _make_boundary(word_checker):
    @specializectx
    def at_boundary(ctx, ptr):
        if ctx.end == ctx.ZERO:
            return False
        try:
            prevptr = ctx.prev(ptr)
        except EndOfString:
            that = False
        else:
            that = word_checker(ctx.str(prevptr))
        this = ptr < ctx.end and word_checker(ctx.str(ptr))
        return this != that
    @specializectx
    def at_non_boundary(ctx, ptr):
        if ctx.end == ctx.ZERO:
            return False
        try:
            prevptr = ctx.prev(ptr)
        except EndOfString:
            that = False
        else:
            that = word_checker(ctx.str(prevptr))
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

def match(pattern, string, start=0, end=sys.maxint, fullmatch=False):
    assert isinstance(pattern, CompiledPattern)
    start, end = _adjust(start, end, len(string))
    ctx = StrMatchContext(string, start, end)
    ctx.fullmatch_only = fullmatch
    if match_context(ctx, pattern):
        return ctx
    else:
        return None

def fullmatch(pattern, string, start=0, end=sys.maxint):
    return match(pattern, string, start, end, fullmatch=True)

def search(pattern, string, start=0, end=sys.maxint):
    assert isinstance(pattern, CompiledPattern)
    start, end = _adjust(start, end, len(string))
    ctx = StrMatchContext(string, start, end)
    if search_context(ctx, pattern):
        return ctx
    else:
        return None

install_jitdriver('Match',
                  greens=['pattern'], reds=['ctx'],
                  debugprint=(0,),
                  is_recursive=True)

def match_context(ctx, pattern):
    ctx.original_pos = ctx.match_start
    if ctx.end < ctx.match_start:
        return False
    ctx.jitdriver_Match.jit_merge_point(ctx=ctx, pattern=pattern)
    return sre_match(ctx, pattern, 0, ctx.match_start, None) is not None

def search_context(ctx, pattern):
    ctx.original_pos = ctx.match_start
    if ctx.end < ctx.match_start:
        return False
    base = 0
    charset = False
    if pattern.pat(base) == consts.OPCODE_INFO:
        flags = pattern.pat(2)
        if flags & consts.SRE_INFO_PREFIX:
            if pattern.pat(5) > 1:
                return fast_search(ctx, pattern)
        else:
            charset = (flags & consts.SRE_INFO_CHARSET)
        base += 1 + pattern.pat(1)
    if pattern.pat(base) == consts.OPCODE_LITERAL:
        return literal_search(ctx, pattern, base)
    if charset:
        return charset_search(ctx, pattern, base)
    return regular_search(ctx, pattern, base)

install_jitdriver('RegularSearch',
                  greens=['base', 'pattern'],
                  reds=['start', 'ctx'],
                  debugprint=(1, 0),
                  is_recursive=True)

def regular_search(ctx, pattern, base):
    start = ctx.match_start
    while True:
        ctx.jitdriver_RegularSearch.jit_merge_point(ctx=ctx, pattern=pattern,
                                                    start=start, base=base)
        if sre_match(ctx, pattern, base, start, None) is not None:
            ctx.match_start = start
            return True
        if start >= ctx.end:
            break
        start = ctx.next_indirect(start)
    return False

install_jitdriver_spec("LiteralSearch",
                       greens=['base', 'character', 'pattern'],
                       reds=['start', 'ctx'],
                       debugprint=(2, 0, 1))
@specializectx
def literal_search(ctx, pattern, base):
    # pattern starts with a literal character.  this is used
    # for short prefixes, and if fast search is disabled
    character = pattern.pat(base + 1)
    base += 2
    start = ctx.match_start
    while start < ctx.end:
        ctx.jitdriver_LiteralSearch.jit_merge_point(ctx=ctx, start=start,
                                          base=base, character=character, pattern=pattern)
        start1 = ctx.next(start)
        if ctx.matches_literal(start, character):
            if sre_match(ctx, pattern, base, start1, None) is not None:
                ctx.match_start = start
                return True
        start = start1
    return False

install_jitdriver_spec("CharsetSearch",
                       greens=['base', 'pattern'],
                       reds=['start', 'ctx'],
                       debugprint=(1, 0))
@specializectx
def charset_search(ctx, pattern, base):
    # pattern starts with a character from a known set
    start = ctx.match_start
    while start < ctx.end:
        ctx.jitdriver_CharsetSearch.jit_merge_point(ctx=ctx, start=start,
                                                    base=base, pattern=pattern)
        if rsre_char.check_charset(ctx, pattern, 5, ctx.str(start)):
            if sre_match(ctx, pattern, base, start, None) is not None:
                ctx.match_start = start
                return True
        start = ctx.next(start)
    return False

install_jitdriver_spec('FastSearch',
                       greens=['i', 'prefix_len', 'pattern'],
                       reds='auto',
                       debugprint=(2, 0))


def fast_search_utf8(ctx, pattern):
    from rpython.rlib.rsre.rsre_utf8 import compute_utf8_size_n_literals
    from rpython.rlib.rsre.rsre_utf8 import extract_literal_utf8
    # just use str.find
    string_position = ctx.match_start
    if string_position >= ctx.end:
        return False
    prefix_len = pattern.pat(5)
    assert prefix_len >= 0
    utf8_literal = extract_literal_utf8(pattern)
    i = NonConstant(0)
    while True:
        ctx.jitdriver_FastSearch.jit_merge_point(
                i=i, prefix_len=prefix_len,
                pattern=pattern)
        start = ctx._utf8.find(utf8_literal, string_position, ctx.end)
        if start < 0:
            return False
        string_position = start + len(utf8_literal)
        # start = string_position + 1 - prefix_len: computed later
        ptr = string_position
        prefix_skip = pattern.pat(6)
        if prefix_skip != prefix_len:
            assert prefix_skip < prefix_len
            ptr = start + compute_utf8_size_n_literals(pattern, 7, prefix_skip, 1)
        pattern_offset = pattern.pat(1) + 1
        ppos_start = pattern_offset + 2 * prefix_skip
        if sre_match(ctx, pattern, ppos_start, ptr, None) is not None:
            ctx.match_start = start
            return True
        if string_position >= ctx.end:
            return False

@specializectx_override(override_utf8=fast_search_utf8)
def fast_search(ctx, pattern):
    # skips forward in a string as fast as possible using information from
    # an optimization info block
    # <INFO> <1=skip> <2=flags> <3=min> <4=...>
    #        <5=length> <6=skip> <7=prefix data> <overlap data>
    string_position = ctx.match_start
    if string_position >= ctx.end:
        return False
    prefix_len = pattern.pat(5)
    assert prefix_len >= 0
    i = 0
    while True:
        ctx.jitdriver_FastSearch.jit_merge_point(i=i, prefix_len=prefix_len,
                pattern=pattern)
        if not ctx.matches_literal(string_position, pattern.pat(7 + i)):
            if i > 0:
                overlap_offset = prefix_len + (7 - 1)
                i = pattern.pat(overlap_offset + i)
                continue
        else:
            i += 1
            if i == prefix_len:
                # start = string_position + 1 - prefix_len: computed later
                ptr = string_position
                prefix_skip = pattern.pat(6)
                if prefix_skip == prefix_len:
                    ptr = ctx.next(ptr)
                else:
                    assert prefix_skip < prefix_len
                    ptr = ctx.prev_n(ptr, prefix_len-1 - prefix_skip, ctx.ZERO)
                #flags = pattern.pat(2)
                #if flags & rsre_char.SRE_INFO_LITERAL:
                #    # matched all of pure literal pattern
                #    ctx.match_start = start
                #    ctx.match_end = ptr
                #    ctx.match_marks = None
                #    return True
                pattern_offset = pattern.pat(1) + 1
                ppos_start = pattern_offset + 2 * prefix_skip
                if sre_match(ctx, pattern, ppos_start, ptr, None) is not None:
                    start = ctx.prev_n(ptr, prefix_skip, ctx.ZERO)
                    ctx.match_start = start
                    return True
                overlap_offset = prefix_len + (7 - 1)
                i = pattern.pat(overlap_offset + i)
        string_position = ctx.next(string_position)
        if string_position >= ctx.end:
            return False

