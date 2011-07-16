import sys
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.typedef import make_weakref_descr
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.rlib.rarithmetic import intmask
from pypy.tool.pairtype import extendabletype


# ____________________________________________________________
#
# Constants and exposed functions

from pypy.rlib.rsre import rsre_core
from pypy.rlib.rsre.rsre_char import CODESIZE, getlower, set_unicode_db

@unwrap_spec(char_ord=int, flags=int)
def w_getlower(space, char_ord, flags):
    return space.wrap(getlower(char_ord, flags))

def w_getcodesize(space):
    return space.wrap(CODESIZE)

# use the same version of unicodedb as the standard objspace
import pypy.objspace.std.unicodeobject
set_unicode_db(pypy.objspace.std.unicodeobject.unicodedb)

# ____________________________________________________________
#
# Additional methods on the classes XxxMatchContext

class __extend__(rsre_core.AbstractMatchContext):
    __metaclass__ = extendabletype
    def _w_slice(self, space, start, end):
        raise NotImplementedError
    def _w_string(self, space):
        raise NotImplementedError

class __extend__(rsre_core.StrMatchContext):
    __metaclass__ = extendabletype
    def _w_slice(self, space, start, end):
        return space.wrap(self._string[start:end])
    def _w_string(self, space):
        return space.wrap(self._string)

class __extend__(rsre_core.UnicodeMatchContext):
    __metaclass__ = extendabletype
    def _w_slice(self, space, start, end):
        return space.wrap(self._unicodestr[start:end])
    def _w_string(self, space):
        return space.wrap(self._unicodestr)

def slice_w(space, ctx, start, end, w_default):
    if 0 <= start <= end:
        return ctx._w_slice(space, start, end)
    return w_default

def do_flatten_marks(ctx, num_groups):
    # Returns a list of RPython-level integers.
    # Unlike the app-level groups() method, groups are numbered from 0
    # and the returned list does not start with the whole match range.
    if num_groups == 0:
        return None
    result = [-1] * (2*num_groups)
    mark = ctx.match_marks
    while mark is not None:
        index = mark.gid
        if result[index] == -1:
            result[index] = mark.position
        mark = mark.prev
    return result

def allgroups_w(space, ctx, fmarks, num_groups, w_default):
    grps = [slice_w(space, ctx, fmarks[i*2], fmarks[i*2+1], w_default)
            for i in range(num_groups)]
    return space.newtuple(grps)

def import_re(space):
    w_builtin = space.getbuiltinmodule('__builtin__')
    w_import = space.getattr(w_builtin, space.wrap("__import__"))
    return space.call_function(w_import, space.wrap("re"))

def matchcontext(space, ctx):
    try:
        return rsre_core.match_context(ctx)
    except rsre_core.Error, e:
        raise OperationError(space.w_RuntimeError, space.wrap(e.msg))

def searchcontext(space, ctx):
    try:
        return rsre_core.search_context(ctx)
    except rsre_core.Error, e:
        raise OperationError(space.w_RuntimeError, space.wrap(e.msg))

# ____________________________________________________________
#
# SRE_Pattern class

class W_SRE_Pattern(Wrappable):

    def cannot_copy_w(self):
        space = self.space
        raise OperationError(space.w_TypeError,
                             space.wrap("cannot copy this pattern object"))

    def make_ctx(self, w_string, pos=0, endpos=sys.maxint):
        """Make a StrMatchContext or a UnicodeMatchContext for searching
        in the given w_string object."""
        space = self.space
        if pos < 0: pos = 0
        if endpos < pos: endpos = pos
        if space.is_true(space.isinstance(w_string, space.w_unicode)):
            unicodestr = space.unicode_w(w_string)
            if pos > len(unicodestr): pos = len(unicodestr)
            if endpos > len(unicodestr): endpos = len(unicodestr)
            return rsre_core.UnicodeMatchContext(self.code, unicodestr,
                                                 pos, endpos, self.flags)
        else:
            str = space.bufferstr_w(w_string)
            if pos > len(str): pos = len(str)
            if endpos > len(str): endpos = len(str)
            return rsre_core.StrMatchContext(self.code, str,
                                             pos, endpos, self.flags)

    def getmatch(self, ctx, found):
        if found:
            return W_SRE_Match(self, ctx)
        else:
            return self.space.w_None

    @unwrap_spec(pos=int, endpos=int)
    def match_w(self, w_string, pos=0, endpos=sys.maxint):
        ctx = self.make_ctx(w_string, pos, endpos)
        return self.getmatch(ctx, matchcontext(self.space, ctx))

    @unwrap_spec(pos=int, endpos=int)
    def search_w(self, w_string, pos=0, endpos=sys.maxint):
        ctx = self.make_ctx(w_string, pos, endpos)
        return self.getmatch(ctx, searchcontext(self.space, ctx))

    @unwrap_spec(pos=int, endpos=int)
    def findall_w(self, w_string, pos=0, endpos=sys.maxint):
        space = self.space
        matchlist_w = []
        ctx = self.make_ctx(w_string, pos, endpos)
        while ctx.match_start <= ctx.end:
            if not searchcontext(space, ctx):
                break
            num_groups = self.num_groups
            w_emptystr = space.wrap("")
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
            no_progress = (ctx.match_start == ctx.match_end)
            ctx.reset(ctx.match_end + no_progress)
        return space.newlist(matchlist_w)

    @unwrap_spec(pos=int, endpos=int)
    def finditer_w(self, w_string, pos=0, endpos=sys.maxint):
        # this also works as the implementation of the undocumented
        # scanner() method.
        ctx = self.make_ctx(w_string, pos, endpos)
        scanner = W_SRE_Scanner(self, ctx)
        return self.space.wrap(scanner)

    @unwrap_spec(maxsplit=int)
    def split_w(self, w_string, maxsplit=0):
        space = self.space
        splitlist = []
        n = 0
        last = 0
        ctx = self.make_ctx(w_string)
        while not maxsplit or n < maxsplit:
            if not searchcontext(space, ctx):
                break
            if ctx.match_start == ctx.match_end:     # zero-width match
                if ctx.match_start == ctx.end:       # or end of string
                    break
                ctx.reset(ctx.match_end + 1)
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
        return space.newtuple([w_item, space.wrap(n)])

    def subx(self, w_ptemplate, w_string, count):
        space = self.space
        if space.is_true(space.callable(w_ptemplate)):
            w_filter = w_ptemplate
            filter_is_callable = True
        else:
            if space.is_true(space.isinstance(w_ptemplate, space.w_unicode)):
                filter_as_unicode = space.unicode_w(w_ptemplate)
                literal = u'\\' not in filter_as_unicode
            else:
                try:
                    filter_as_string = space.str_w(w_ptemplate)
                except OperationError, e:
                    if e.async(space):
                        raise
                    literal = False
                else:
                    literal = '\\' not in filter_as_string
            if literal:
                w_filter = w_ptemplate
                filter_is_callable = False
            else:
                # not a literal; hand it over to the template compiler
                w_re = import_re(space)
                w_filter = space.call_method(w_re, '_subx',
                                             space.wrap(self), w_ptemplate)
                filter_is_callable = space.is_true(space.callable(w_filter))
        #
        ctx = self.make_ctx(w_string)
        sublist_w = []
        n = last_pos = 0
        while not count or n < count:
            if not searchcontext(space, ctx):
                break
            if last_pos < ctx.match_start:
                sublist_w.append(slice_w(space, ctx, last_pos,
                                         ctx.match_start, space.w_None))
            start = ctx.match_end
            if start == ctx.match_start:
                start += 1
            nextctx = ctx.fresh_copy(start)
            if not (last_pos == ctx.match_start
                             == ctx.match_end and n > 0):
                # the above ignores empty matches on latest position
                if filter_is_callable:
                    w_match = self.getmatch(ctx, True)
                    w_piece = space.call_function(w_filter, w_match)
                    if not space.is_w(w_piece, space.w_None):
                        sublist_w.append(w_piece)
                else:
                    sublist_w.append(w_filter)
                last_pos = ctx.match_end
                n += 1
            elif last_pos >= ctx.end:
                break    # empty match at the end: finished
            ctx = nextctx

        if last_pos < ctx.end:
            sublist_w.append(slice_w(space, ctx, last_pos, ctx.end,
                                     space.w_None))
        if n == 0:
            # not just an optimization -- see test_sub_unicode
            return w_string, n

        if space.is_true(space.isinstance(w_string, space.w_unicode)):
            w_emptystr = space.wrap(u'')
        else:
            w_emptystr = space.wrap('')
        w_item = space.call_method(w_emptystr, 'join',
                                   space.newlist(sublist_w))
        return w_item, n


@unwrap_spec(flags=int, groups=int)
def SRE_Pattern__new__(space, w_subtype, w_pattern, flags, w_code,
              groups=0, w_groupindex=None, w_indexgroup=None):
    n = space.len_w(w_code)
    code = [intmask(space.uint_w(space.getitem(w_code, space.wrap(i))))
            for i in range(n)]
    #
    w_srepat = space.allocate_instance(W_SRE_Pattern, w_subtype)
    srepat = space.interp_w(W_SRE_Pattern, w_srepat)
    srepat.space = space
    srepat.w_pattern = w_pattern      # the original uncompiled pattern
    srepat.flags = flags
    srepat.code = code
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
    flags        = interp_attrproperty('flags', W_SRE_Pattern),
    groupindex   = interp_attrproperty_w('w_groupindex', W_SRE_Pattern),
    groups       = interp_attrproperty('num_groups', W_SRE_Pattern),
    pattern      = interp_attrproperty_w('w_pattern', W_SRE_Pattern),
)

# ____________________________________________________________
#
# SRE_Match class

class W_SRE_Match(Wrappable):
    flatten_cache = None

    def __init__(self, srepat, ctx):
        self.space = srepat.space
        self.srepat = srepat
        self.ctx = ctx

    def cannot_copy_w(self):
        space = self.space
        raise OperationError(space.w_TypeError,
                             space.wrap("cannot copy this match object"))

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

    def groups_w(self, w_default=None):
        fmarks = self.flatten_marks()
        num_groups = self.srepat.num_groups
        return allgroups_w(self.space, self.ctx, fmarks, num_groups, w_default)

    def groupdict_w(self, w_default=None):
        space = self.space
        w_dict = space.newdict()
        w_groupindex = self.srepat.w_groupindex
        w_iterator = space.iter(w_groupindex)
        while True:
            try:
                w_key = space.next(w_iterator)
            except OperationError, e:
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
        return space.call_method(w_re, '_expand', space.wrap(self.srepat),
                                 space.wrap(self), w_template)

    def start_w(self, w_groupnum=0):
        return self.space.wrap(self.do_span(w_groupnum)[0])

    def end_w(self, w_groupnum=0):
        return self.space.wrap(self.do_span(w_groupnum)[1])

    def span_w(self, w_groupnum=0):
        start, end = self.do_span(w_groupnum)
        return self.space.newtuple([self.space.wrap(start),
                                    self.space.wrap(end)])

    def flatten_marks(self):
        if self.flatten_cache is None:
            num_groups = self.srepat.num_groups
            self.flatten_cache = do_flatten_marks(self.ctx, num_groups)
        return self.flatten_cache

    def do_span(self, w_arg):
        space = self.space
        try:
            groupnum = space.int_w(w_arg)
        except OperationError, e:
            if not e.match(space, space.w_TypeError):
                raise
            w_groupnum = space.getitem(self.srepat.w_groupindex, w_arg)
            groupnum = space.int_w(w_groupnum)
        if groupnum == 0:
            return self.ctx.match_start, self.ctx.match_end
        elif 1 <= groupnum <= self.srepat.num_groups:
            fmarks = self.flatten_marks()
            idx = 2*(groupnum-1)
            assert idx >= 0
            return fmarks[idx], fmarks[idx+1]
        else:
            raise OperationError(space.w_IndexError,
                                 space.wrap("group index out of range"))

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
                                  space.wrap(lastindex))
        if w_result is None:
            return space.w_None
        return w_result

    def fget_lastindex(self, space):
        lastindex = self._last_index()
        if lastindex >= 0:
            return space.wrap(lastindex)
        return space.w_None

    def fget_pos(self, space):
        return space.wrap(self.ctx.original_pos)

    def fget_endpos(self, space):
        return space.wrap(self.ctx.end)

    def fget_regs(self, space):
        space = self.space
        fmarks = self.flatten_marks()
        num_groups = self.srepat.num_groups
        result_w = [None] * (num_groups + 1)
        ctx = self.ctx
        result_w[0] = space.newtuple([space.wrap(ctx.match_start),
                                      space.wrap(ctx.match_end)])
        for i in range(num_groups):
            result_w[i + 1] = space.newtuple([space.wrap(fmarks[i*2]),
                                              space.wrap(fmarks[i*2+1])])
        return space.newtuple(result_w)

    def fget_string(self, space):
        return self.ctx._w_string(space)


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
    re           = interp_attrproperty('srepat', W_SRE_Match),
    string       = GetSetProperty(W_SRE_Match.fget_string),
    pos          = GetSetProperty(W_SRE_Match.fget_pos),
    endpos       = GetSetProperty(W_SRE_Match.fget_endpos),
    lastgroup    = GetSetProperty(W_SRE_Match.fget_lastgroup),
    lastindex    = GetSetProperty(W_SRE_Match.fget_lastindex),
    regs         = GetSetProperty(W_SRE_Match.fget_regs),
)

# ____________________________________________________________
#
# SRE_Scanner class
# This is mostly an internal class in CPython.
# Our version is also directly iterable, to make finditer() easier.

class W_SRE_Scanner(Wrappable):

    def __init__(self, pattern, ctx):
        self.space = pattern.space
        self.srepat = pattern
        self.ctx = ctx
        # 'self.ctx' is always a fresh context in which no searching
        # or matching succeeded so far.

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.ctx.match_start > self.ctx.end:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        if not searchcontext(self.space, self.ctx):
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        return self.getmatch(True)

    def match_w(self):
        if self.ctx.match_start > self.ctx.end:
            return self.space.w_None
        return self.getmatch(matchcontext(self.space, self.ctx))

    def search_w(self):
        if self.ctx.match_start > self.ctx.end:
            return self.space.w_None
        return self.getmatch(searchcontext(self.space, self.ctx))

    def getmatch(self, found):
        if found:
            ctx = self.ctx
            nextstart = ctx.match_end
            nextstart += (ctx.match_start == nextstart)
            self.ctx = ctx.fresh_copy(nextstart)
            match = W_SRE_Match(self.srepat, ctx)
            return self.space.wrap(match)
        else:
            self.ctx.match_start += 1     # obscure corner case
            return None

W_SRE_Scanner.typedef = TypeDef(
    'SRE_Scanner',
    __iter__ = interp2app(W_SRE_Scanner.iter_w),
    next     = interp2app(W_SRE_Scanner.next_w),
    match    = interp2app(W_SRE_Scanner.match_w),
    search   = interp2app(W_SRE_Scanner.search_w),
    pattern  = interp_attrproperty('srepat', W_SRE_Scanner),
)
