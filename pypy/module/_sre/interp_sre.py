import sys
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.typedef import make_weakref_descr
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.error import OperationError, oefmt
from rpython.rlib.rarithmetic import intmask
from rpython.rlib import jit, rutf8
from rpython.rlib.rstring import StringBuilder

# ____________________________________________________________
#
# Constants and exposed functions

from rpython.rlib.rsre import rsre_core, rsre_utf8
from rpython.rlib.rsre.rsre_char import CODESIZE, MAXREPEAT, getlower, set_unicode_db


@unwrap_spec(char_ord=int, flags=int)
def w_getlower(space, char_ord, flags):
    return space.newint(getlower(char_ord, flags))


def w_getcodesize(space):
    return space.newint(CODESIZE)

# use the same version of unicodedb as the standard objspace
import pypy.objspace.std.unicodeobject
set_unicode_db(pypy.objspace.std.unicodeobject.unicodedb)

# ____________________________________________________________
#

class UnicodeAsciiMatchContext(rsre_core.StrMatchContext):
    # we make a subclass just to mark that it originates from a W_UnicodeObject
    pass


def slice_w(space, ctx, start, end, w_default):
    # 'start' and 'end' are byte positions
    if ctx.ZERO <= start <= end:
        if isinstance(ctx, rsre_core.BufMatchContext):
            return space.newbytes(ctx._buffer.getslice(start, 1, end-start))
        elif isinstance(ctx, UnicodeAsciiMatchContext):
            s = ctx._string[start:end]
            return space.newutf8(s, len(s))
        elif isinstance(ctx, rsre_core.StrMatchContext):
            start = ctx._real_pos(start)
            end = ctx._real_pos(end)
            return space.newbytes(ctx._string[start:end])
        elif isinstance(ctx, rsre_utf8.Utf8MatchContext):
            s = ctx._utf8[start:end]
            lgt = rutf8.codepoints_in_utf8(s)
            return space.newutf8(s, lgt)
        else:
            # unreachable
            raise SystemError
    return w_default


@jit.look_inside_iff(lambda ctx, num_groups: jit.isconstant(num_groups))
def do_flatten_marks(ctx, num_groups):
    # Returns a list of RPython-level integers.
    # Unlike the app-level groups() method, groups are numbered from 0
    # and the returned list does not start with the whole match range.
    # The integers are byte positions, not character indexes (for utf8).
    if num_groups == 0:
        return None
    result = [-1] * (2 * num_groups)
    mark = ctx.match_marks
    while mark is not None:
        index = jit.promote(mark.gid)
        if result[index] == -1:
            result[index] = mark.position
        mark = mark.prev
    return result


@jit.look_inside_iff(lambda space, ctx, fmarks, num_groups, w_default: jit.isconstant(num_groups))
def allgroups_w(space, ctx, fmarks, num_groups, w_default):
    grps = [slice_w(space, ctx, fmarks[i * 2], fmarks[i * 2 + 1], w_default)
            for i in range(num_groups)]
    return space.newtuple(grps)


def import_re(space):
    w_builtin = space.getbuiltinmodule('__builtin__')
    w_import = space.getattr(w_builtin, space.newtext("__import__"))
    return space.call_function(w_import, space.newtext("re"))

def matchcontext(space, ctx, pattern):
    try:
        return rsre_core.match_context(ctx, pattern)
    except rsre_core.Error as e:
        raise OperationError(space.w_RuntimeError, space.newtext(e.msg))

def searchcontext(space, ctx, pattern):
    try:
        return rsre_core.search_context(ctx, pattern)
    except rsre_core.Error as e:
        raise OperationError(space.w_RuntimeError, space.newtext(e.msg))

# ____________________________________________________________
#
# SRE_Pattern class

class W_SRE_Pattern(W_Root):
    _immutable_fields_ = ["code", "flags", "num_groups", "w_groupindex"]

    def cannot_copy_w(self):
        space = self.space
        raise oefmt(space.w_TypeError, "cannot copy this pattern object")

    def make_ctx(self, w_string, pos=0, endpos=sys.maxint):
        """Make a StrMatchContext, BufMatchContext, UnicodeAsciiMatchContext or
        a Utf8MatchContext for searching in the given w_string object."""
        space = self.space
        if pos < 0:
            pos = 0
        if endpos < pos:
            endpos = pos
        if space.isinstance_w(w_string, space.w_unicode):
            w_unicode_obj = space.convert_arg_to_w_unicode(w_string)
            utf8str = w_unicode_obj._utf8
            length = w_unicode_obj._len()
            if pos <= 0:
                bytepos = 0
            elif pos >= length:
                bytepos = len(utf8str)
            else:
                bytepos = w_unicode_obj._index_to_byte(pos)
            if endpos >= length:
                endbytepos = len(utf8str)
            else:
                endbytepos = w_unicode_obj._index_to_byte(endpos)
            if w_unicode_obj.is_ascii():
                ctx = UnicodeAsciiMatchContext(
                        utf8str, bytepos, endbytepos)
            else:
                ctx = rsre_utf8.Utf8MatchContext(
                    utf8str, bytepos, endbytepos)
                # we store the w_string on the ctx too, for
                # W_SRE_Match.bytepos_to_charindex()
                ctx.w_unicode_obj = w_unicode_obj
            return ctx
        elif space.isinstance_w(w_string, space.w_bytes):
            str = space.bytes_w(w_string)
            if pos > len(str):
                pos = len(str)
            if endpos > len(str):
                endpos = len(str)
            return self._make_str_match_context(str, pos, endpos)
        else:
            buf = space.readbuf_w(w_string)
            size = buf.getlength()
            assert size >= 0
            if pos > size:
                pos = size
            if endpos > size:
                endpos = size
            return rsre_core.BufMatchContext(buf,
                                             pos, endpos)

    def fresh_copy(self, ctx):
        if isinstance(ctx, rsre_utf8.Utf8MatchContext):
            result = rsre_utf8.Utf8MatchContext(
                ctx._utf8, ctx.match_start, ctx.end)
            result.w_unicode_obj = ctx.w_unicode_obj
        elif isinstance(ctx, UnicodeAsciiMatchContext):
            result = UnicodeAsciiMatchContext(
                ctx._string, ctx.match_start, ctx.end)
        elif isinstance(ctx, rsre_core.StrMatchContext):
            result = self._make_str_match_context(
                ctx._string, ctx.match_start, ctx.end)
        elif isinstance(ctx, rsre_core.BufMatchContext):
            result = rsre_core.BufMatchContext(
                ctx._buffer, ctx.match_start, ctx.end)
        else:
            raise AssertionError("bad ctx type")
        result.match_end = ctx.match_end
        return result

    def _make_str_match_context(self, str, pos, endpos):
        # for tests to override
        return rsre_core.StrMatchContext(str,
                                         pos, endpos)

    def getmatch(self, ctx, found):
        if found:
            return W_SRE_Match(self, ctx)
        else:
            return self.space.w_None

    @unwrap_spec(pos=int, endpos=int)
    def match_w(self, w_string, pos=0, endpos=sys.maxint):
        ctx = self.make_ctx(w_string, pos, endpos)
        return self.getmatch(ctx, matchcontext(self.space, ctx, self.code))

    @unwrap_spec(pos=int, endpos=int)
    def search_w(self, w_string, pos=0, endpos=sys.maxint):
        ctx = self.make_ctx(w_string, pos, endpos)
        return self.getmatch(ctx, searchcontext(self.space, ctx, self.code))

    @unwrap_spec(pos=int, endpos=int)
    def findall_w(self, w_string, pos=0, endpos=sys.maxint):
        space = self.space
        matchlist_w = []
        ctx = self.make_ctx(w_string, pos, endpos)
        while True:
            if not searchcontext(space, ctx, self.code):
                break
            num_groups = self.num_groups
            w_emptystr = space.newtext("")
            if num_groups == 0:
                w_item = slice_w(space, ctx, ctx.match_start, ctx.match_end,
                                 w_emptystr)
            else:
                fmarks = do_flatten_marks(ctx, num_groups)
                if num_groups == 1:
                    w_item = slice_w(space, ctx, fmarks[0], fmarks[1],
                                     w_emptystr)
                else:
                    w_item = allgroups_w(space, ctx, fmarks, num_groups,
                                         w_emptystr)
            matchlist_w.append(w_item)
            reset_at = ctx.match_end
            if ctx.match_start == ctx.match_end:
                if reset_at == ctx.end:
                    break
                reset_at = ctx.next_indirect(reset_at)
            ctx.reset(reset_at)
        return space.newlist(matchlist_w)

    @unwrap_spec(pos=int, endpos=int)
    def finditer_w(self, w_string, pos=0, endpos=sys.maxint):
        # this also works as the implementation of the undocumented
        # scanner() method.
        ctx = self.make_ctx(w_string, pos, endpos)
        scanner = W_SRE_Scanner(self, ctx, self.code)
        return scanner

    @unwrap_spec(maxsplit=int)
    def split_w(self, w_string, maxsplit=0):
        space = self.space
        splitlist = []
        n = 0
        ctx = self.make_ctx(w_string)
        last = ctx.ZERO
        while not maxsplit or n < maxsplit:
            if not searchcontext(space, ctx, self.code):
                break
            if ctx.match_start == ctx.match_end:     # zero-width match
                if ctx.match_start == ctx.end:       # or end of string
                    break
                ctx.reset(ctx.next_indirect(ctx.match_end))
                continue
            splitlist.append(slice_w(space, ctx, last, ctx.match_start,
                                     space.w_None))
            # add groups (if any)
            fmarks = do_flatten_marks(ctx, self.num_groups)
            for groupnum in range(self.num_groups):
                groupstart, groupend = fmarks[groupnum*2], fmarks[groupnum*2+1]
                splitlist.append(slice_w(space, ctx, groupstart, groupend,
                                         space.w_None))
            n += 1
            last = ctx.match_end
            ctx.reset(last)
        splitlist.append(slice_w(space, ctx, last, ctx.end, space.w_None))
        return space.newlist(splitlist)

    @unwrap_spec(count=int)
    def sub_w(self, w_repl, w_string, count=0):
        w_item, n = self.subx(w_repl, w_string, count)
        return w_item

    @unwrap_spec(count=int)
    def subn_w(self, w_repl, w_string, count=0):
        w_item, n = self.subx(w_repl, w_string, count)
        space = self.space
        return space.newtuple([w_item, space.newint(n)])

    def subx(self, w_ptemplate, w_string, count):
        space = self.space
        # use a (much faster) string builder (possibly utf8) if w_ptemplate and
        # w_string are both string or both unicode objects, and if w_ptemplate
        # is a literal
        use_builder = '\x00'   # or 'S'tring or 'U'nicode/UTF8
        filter_as_string = None
        if space.is_true(space.callable(w_ptemplate)):
            w_filter = w_ptemplate
            filter_is_callable = True
        else:
            if space.isinstance_w(w_ptemplate, space.w_unicode):
                filter_as_string = space.utf8_w(w_ptemplate)
                literal = '\\' not in filter_as_string
                if space.isinstance_w(w_string, space.w_unicode) and literal:
                    use_builder = 'U'
            else:
                try:
                    filter_as_string = space.bytes_w(w_ptemplate)
                except OperationError as e:
                    if e.async(space):
                        raise
                    literal = False
                else:
                    literal = '\\' not in filter_as_string
                    if space.isinstance_w(w_string, space.w_bytes) and literal:
                        use_builder = 'S'
            if literal:
                w_filter = w_ptemplate
                filter_is_callable = False
            else:
                # not a literal; hand it over to the template compiler
                w_re = import_re(space)
                w_filter = space.call_method(w_re, '_subx',
                                             self, w_ptemplate)
                filter_is_callable = space.is_true(space.callable(w_filter))
        #
        # XXX this is a bit of a mess, but it improves performance a lot
        ctx = self.make_ctx(w_string)
        sublist_w = strbuilder = None
        if use_builder != '\x00':
            assert filter_as_string is not None
            strbuilder = StringBuilder(ctx.end)
        else:
            sublist_w = []
        n = 0
        last_pos = ctx.ZERO
        while not count or n < count:
            pattern = self.code
            sub_jitdriver.jit_merge_point(
                self=self,
                use_builder=use_builder,
                filter_is_callable=filter_is_callable,
                filter_type=type(w_filter),
                ctx=ctx, pattern=pattern,
                w_filter=w_filter,
                strbuilder=strbuilder,
                filter_as_string=filter_as_string,
                count=count,
                w_string=w_string,
                n=n, last_pos=last_pos, sublist_w=sublist_w
                )
            space = self.space
            if not searchcontext(space, ctx, pattern):
                break
            if last_pos < ctx.match_start:
                _sub_append_slice(
                    ctx, space, use_builder, sublist_w,
                    strbuilder, last_pos, ctx.match_start)
            if not (last_pos == ctx.match_start
                             == ctx.match_end and n > 0):
                # the above ignores empty matches on latest position
                last_pos = ctx.match_end
                if filter_is_callable:
                    w_match = self.getmatch(ctx, True)
                    # make a copy of 'ctx'; see test_sub_matches_stay_valid
                    ctx = self.fresh_copy(ctx)
                    w_piece = space.call_function(w_filter, w_match)
                    if not space.is_w(w_piece, space.w_None):
                        assert strbuilder is None
                        assert use_builder == '\x00'
                        sublist_w.append(w_piece)
                else:
                    if use_builder != '\x00':
                        assert filter_as_string is not None
                        assert strbuilder is not None
                        strbuilder.append(filter_as_string)
                    else:
                        sublist_w.append(w_filter)
                n += 1
            elif last_pos >= ctx.end:
                break    # empty match at the end: finished

            start = ctx.match_end
            if start == ctx.match_start:
                if start == ctx.end:
                    break
                start = ctx.next_indirect(start)
            ctx.reset(start)

        if last_pos < ctx.end:
            _sub_append_slice(ctx, space, use_builder, sublist_w,
                              strbuilder, last_pos, ctx.end)
        if use_builder != '\x00':
            assert strbuilder is not None
            result_bytes = strbuilder.build()
            if use_builder == 'S':
                assert not isinstance(ctx, rsre_utf8.Utf8MatchContext)
                return space.newbytes(result_bytes), n
            elif use_builder == 'U':
                assert (isinstance(ctx, UnicodeAsciiMatchContext) or
                        isinstance(ctx, rsre_utf8.Utf8MatchContext))
                return space.newutf8(result_bytes,
                                     rutf8.codepoints_in_utf8(result_bytes)), n
            else:
                raise AssertionError(use_builder)
        else:
            if space.isinstance_w(w_string, space.w_unicode):
                w_emptystr = space.newutf8('', 0)
            else:
                w_emptystr = space.newbytes('')
            w_item = space.call_method(w_emptystr, 'join',
                                       space.newlist(sublist_w))
            return w_item, n

sub_jitdriver = jit.JitDriver(
    reds="""count n last_pos
            ctx w_filter
            strbuilder
            filter_as_string
            w_string sublist_w
            self""".split(),
    greens=["filter_is_callable", "use_builder", "filter_type", "pattern"])


def _sub_append_slice(ctx, space, use_builder, sublist_w,
                      strbuilder, start, end):
    if use_builder != '\x00':
        assert strbuilder is not None
        if isinstance(ctx, rsre_core.BufMatchContext):
            assert use_builder == 'S'
            return strbuilder.append(ctx._buffer.getslice(start, 1, end-start))
        if isinstance(ctx, UnicodeAsciiMatchContext):
            assert use_builder == 'U'
            return strbuilder.append_slice(ctx._string, start, end)
        if isinstance(ctx, rsre_core.StrMatchContext):
            assert use_builder == 'S'
            start = ctx._real_pos(start)
            end = ctx._real_pos(end)
            return strbuilder.append_slice(ctx._string, start, end)
        if isinstance(ctx, rsre_utf8.Utf8MatchContext):
            assert use_builder == 'U'
            return strbuilder.append_slice(ctx._utf8, start, end)
        assert 0, "unreachable"
    else:
        sublist_w.append(slice_w(space, ctx, start, end, space.w_None))

@unwrap_spec(flags=int, groups=int, w_groupindex=WrappedDefault(None),
             w_indexgroup=WrappedDefault(None))
def SRE_Pattern__new__(space, w_subtype, w_pattern, flags, w_code,
              groups=0, w_groupindex=None, w_indexgroup=None):
    n = space.len_w(w_code)
    code = [intmask(space.uint_w(space.getitem(w_code, space.newint(i))))
            for i in range(n)]
    #
    w_srepat = space.allocate_instance(W_SRE_Pattern, w_subtype)
    srepat = space.interp_w(W_SRE_Pattern, w_srepat)
    srepat.space = space
    srepat.w_pattern = w_pattern      # the original uncompiled pattern
    srepat.flags = flags
    # note: we assume that the app-level is caching SRE_Pattern objects,
    # so that we don't need to do it here.  Creating new SRE_Pattern
    # objects all the time would be bad for the JIT, which relies on the
    # identity of the CompiledPattern() object.
    srepat.code = rsre_core.CompiledPattern(code, flags)
    srepat.num_groups = groups
    srepat.w_groupindex = w_groupindex
    srepat.w_indexgroup = w_indexgroup
    return w_srepat


W_SRE_Pattern.typedef = TypeDef(
    'SRE_Pattern',
    __new__      = interp2app(SRE_Pattern__new__),
    __copy__     = interp2app(W_SRE_Pattern.cannot_copy_w),
    __deepcopy__ = interp2app(W_SRE_Pattern.cannot_copy_w),
    __weakref__  = make_weakref_descr(W_SRE_Pattern),
    findall      = interp2app(W_SRE_Pattern.findall_w),
    finditer     = interp2app(W_SRE_Pattern.finditer_w),
    match        = interp2app(W_SRE_Pattern.match_w),
    scanner      = interp2app(W_SRE_Pattern.finditer_w),    # reuse finditer()
    search       = interp2app(W_SRE_Pattern.search_w),
    split        = interp2app(W_SRE_Pattern.split_w),
    sub          = interp2app(W_SRE_Pattern.sub_w),
    subn         = interp2app(W_SRE_Pattern.subn_w),
    flags        = interp_attrproperty('flags', W_SRE_Pattern,
        wrapfn="newint"),
    groupindex   = interp_attrproperty_w('w_groupindex', W_SRE_Pattern),
    groups       = interp_attrproperty('num_groups', W_SRE_Pattern,
        wrapfn="newint"),
    pattern      = interp_attrproperty_w('w_pattern', W_SRE_Pattern),
)
W_SRE_Pattern.typedef.acceptable_as_base_class = False

# ____________________________________________________________
#
# SRE_Match class

class W_SRE_Match(W_Root):
    flatten_cache = None

    def __init__(self, srepat, ctx):
        self.space = srepat.space
        self.srepat = srepat
        self.ctx = ctx

    def cannot_copy_w(self):
        space = self.space
        raise oefmt(space.w_TypeError, "cannot copy this match object")

    @jit.look_inside_iff(lambda self, args_w: jit.isconstant(len(args_w)))
    def group_w(self, args_w):
        space = self.space
        ctx = self.ctx
        if len(args_w) <= 1:
            if len(args_w) == 0:
                start, end = ctx.match_start, ctx.match_end
            else:
                start, end = self.do_span(args_w[0])
            return slice_w(space, ctx, start, end, space.w_None)
        else:
            results = [None] * len(args_w)
            for i in range(len(args_w)):
                start, end = self.do_span(args_w[i])
                results[i] = slice_w(space, ctx, start, end, space.w_None)
            return space.newtuple(results)

    @unwrap_spec(w_default=WrappedDefault(None))
    def groups_w(self, w_default=None):
        fmarks = self.flatten_marks()
        num_groups = self.srepat.num_groups
        return allgroups_w(self.space, self.ctx, fmarks, num_groups, w_default)

    @unwrap_spec(w_default=WrappedDefault(None))
    def groupdict_w(self, w_default=None):
        space = self.space
        w_dict = space.newdict()
        w_groupindex = self.srepat.w_groupindex
        w_iterator = space.iter(w_groupindex)
        while True:
            try:
                w_key = space.next(w_iterator)
            except OperationError as e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break  # done
            w_value = space.getitem(w_groupindex, w_key)
            start, end = self.do_span(w_value)
            w_grp = slice_w(space, self.ctx, start, end, w_default)
            space.setitem(w_dict, w_key, w_grp)
        return w_dict

    def expand_w(self, w_template):
        space = self.space
        w_re = import_re(space)
        return space.call_method(w_re, '_expand', self.srepat,
                                 self, w_template)

    @unwrap_spec(w_groupnum=WrappedDefault(0))
    def start_w(self, w_groupnum):
        start, end = self.do_span(w_groupnum)
        start = self.bytepos_to_charindex(start)
        return self.space.newint(start)

    @unwrap_spec(w_groupnum=WrappedDefault(0))
    def end_w(self, w_groupnum):
        start, end = self.do_span(w_groupnum)
        end = self.bytepos_to_charindex(end)
        return self.space.newint(end)

    @unwrap_spec(w_groupnum=WrappedDefault(0))
    def span_w(self, w_groupnum):
        start, end = self.do_span(w_groupnum)
        return self.new_charindex_tuple(start, end)

    def new_charindex_tuple(self, start, end):
        start = self.bytepos_to_charindex(start)
        end = self.bytepos_to_charindex(end)
        return self.space.newtuple([self.space.newint(start),
                                    self.space.newint(end)])

    def bytepos_to_charindex(self, bytepos):
        # Transform a 'byte position', as returned by all methods from
        # rsre_core, back into a 'character index'.  This is for UTF8
        # handling.
        ctx = self.ctx
        if isinstance(ctx, rsre_utf8.Utf8MatchContext):
            return ctx.w_unicode_obj._byte_to_index(bytepos)
        else:
            return bytepos

    def flatten_marks(self):
        if self.flatten_cache is None:
            num_groups = self.srepat.num_groups
            self.flatten_cache = do_flatten_marks(self.ctx, num_groups)
        return self.flatten_cache

    def do_span(self, w_arg):
        # return a pair of integers, which are byte positions, not
        # character indexes (for utf8)
        space = self.space
        try:
            groupnum = space.int_w(w_arg)
        except OperationError as e:
            if not e.match(space, space.w_TypeError) and \
                    not e.match(space, space.w_OverflowError):
                raise
            try:
                w_groupnum = space.getitem(self.srepat.w_groupindex, w_arg)
            except OperationError as e:
                if not e.match(space, space.w_KeyError):
                    raise
                raise oefmt(space.w_IndexError, "no such group")
            groupnum = space.int_w(w_groupnum)
        if groupnum == 0:
            return self.ctx.match_start, self.ctx.match_end
        elif 1 <= groupnum <= self.srepat.num_groups:
            fmarks = self.flatten_marks()
            idx = 2*(groupnum-1)
            assert idx >= 0
            return fmarks[idx], fmarks[idx+1]
        else:
            raise oefmt(space.w_IndexError, "no such group")

    def _last_index(self):
        mark = self.ctx.match_marks
        if mark is not None:
            return mark.gid // 2 + 1
        return -1

    def fget_lastgroup(self, space):
        lastindex = self._last_index()
        if lastindex < 0:
            return space.w_None
        w_result = space.finditem(self.srepat.w_indexgroup,
                                  space.newint(lastindex))
        if w_result is None:
            return space.w_None
        return w_result

    def fget_lastindex(self, space):
        lastindex = self._last_index()
        if lastindex >= 0:
            return space.newint(lastindex)
        return space.w_None

    def fget_pos(self, space):
        return space.newint(self.bytepos_to_charindex(self.ctx.original_pos))

    def fget_endpos(self, space):
        return space.newint(self.bytepos_to_charindex(self.ctx.end))

    def fget_regs(self, space):
        space = self.space
        fmarks = self.flatten_marks()
        num_groups = self.srepat.num_groups
        result_w = [None] * (num_groups + 1)
        ctx = self.ctx
        result_w[0] = self.new_charindex_tuple(ctx.match_start,
                                               ctx.match_end)
        for i in range(num_groups):
            result_w[i + 1] = self.new_charindex_tuple(fmarks[i*2],
                                                       fmarks[i*2+1])
        return space.newtuple(result_w)

    def fget_string(self, space):
        ctx = self.ctx
        if isinstance(ctx, rsre_core.BufMatchContext):
            return space.newbytes(ctx._buffer.as_str())
        elif isinstance(ctx, UnicodeAsciiMatchContext):
            return space.newutf8(ctx._string, len(ctx._string))
        elif isinstance(ctx, rsre_core.StrMatchContext):
            return space.newbytes(ctx._string)
        elif isinstance(ctx, rsre_utf8.Utf8MatchContext):
            return ctx.w_unicode_obj
        else:
            raise SystemError


W_SRE_Match.typedef = TypeDef(
    'SRE_Match',
    __copy__     = interp2app(W_SRE_Match.cannot_copy_w),
    __deepcopy__ = interp2app(W_SRE_Match.cannot_copy_w),
    group        = interp2app(W_SRE_Match.group_w),
    groups       = interp2app(W_SRE_Match.groups_w),
    groupdict    = interp2app(W_SRE_Match.groupdict_w),
    start        = interp2app(W_SRE_Match.start_w),
    end          = interp2app(W_SRE_Match.end_w),
    span         = interp2app(W_SRE_Match.span_w),
    expand       = interp2app(W_SRE_Match.expand_w),
    #
    re           = interp_attrproperty_w('srepat', W_SRE_Match),
    string       = GetSetProperty(W_SRE_Match.fget_string),
    pos          = GetSetProperty(W_SRE_Match.fget_pos),
    endpos       = GetSetProperty(W_SRE_Match.fget_endpos),
    lastgroup    = GetSetProperty(W_SRE_Match.fget_lastgroup),
    lastindex    = GetSetProperty(W_SRE_Match.fget_lastindex),
    regs         = GetSetProperty(W_SRE_Match.fget_regs),
)
W_SRE_Match.typedef.acceptable_as_base_class = False

# ____________________________________________________________
#
# SRE_Scanner class
# This is mostly an internal class in CPython.
# Our version is also directly iterable, to make finditer() easier.

class W_SRE_Scanner(W_Root):
    def __init__(self, pattern, ctx, code):
        self.space = pattern.space
        self.srepat = pattern
        self.ctx = ctx
        self.code = code
        # 'self.ctx' is always a fresh context in which no searching
        # or matching succeeded so far.  It is None when the iterator is
        # exhausted.

    def iter_w(self):
        return self

    def next_w(self):
        if self.ctx is None:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        if not searchcontext(self.space, self.ctx, self.code):
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        return self.getmatch(True)

    def match_w(self):
        if self.ctx is None:
            return self.space.w_None
        return self.getmatch(matchcontext(self.space, self.ctx, self.code))

    def search_w(self):
        if self.ctx is None:
            return self.space.w_None
        return self.getmatch(searchcontext(self.space, self.ctx, self.code))

    def getmatch(self, found):
        ctx = self.ctx
        assert ctx is not None
        if found:
            nextstart = ctx.match_end
            exhausted = False
            if ctx.match_start == nextstart:
                if nextstart == ctx.end:
                    exhausted = True
                else:
                    nextstart = ctx.next_indirect(nextstart)
            if exhausted:
                self.ctx = None
            else:
                self.ctx = self.srepat.fresh_copy(ctx)
                self.ctx.match_start = nextstart
            match = W_SRE_Match(self.srepat, ctx)
            return match
        else:
            self.ctx = None
            return None

W_SRE_Scanner.typedef = TypeDef(
    'SRE_Scanner',
    __iter__ = interp2app(W_SRE_Scanner.iter_w),
    next     = interp2app(W_SRE_Scanner.next_w),
    match    = interp2app(W_SRE_Scanner.match_w),
    search   = interp2app(W_SRE_Scanner.search_w),
    pattern  = interp_attrproperty_w('srepat', W_SRE_Scanner),
)
W_SRE_Scanner.typedef.acceptable_as_base_class = False
