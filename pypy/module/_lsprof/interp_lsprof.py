import py

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Method, Function
from pypy.interpreter.gateway import interp2app, unwrap_spec, NoneNotWrapped
from pypy.interpreter.typedef import (TypeDef, GetSetProperty,
                                      interp_attrproperty)
from pypy.rlib import jit
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rtimer import read_timestamp
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.autopath import pypydir
from pypy.rlib.rarithmetic import r_longlong

import time, sys

# cpu affinity settings

srcdir = py.path.local(pypydir).join('translator', 'c', 'src')
eci = ExternalCompilationInfo(separate_module_files=
                              [srcdir.join('profiling.c')])
                                                     
c_setup_profiling = rffi.llexternal('pypy_setup_profiling',
                                  [], lltype.Void,
                                  compilation_info = eci)
c_teardown_profiling = rffi.llexternal('pypy_teardown_profiling',
                                       [], lltype.Void,
                                       compilation_info = eci)

class W_StatsEntry(Wrappable):
    def __init__(self, space, frame, callcount, reccallcount, tt, it,
                 w_sublist):
        self.frame = frame
        self.callcount = callcount
        self.reccallcount = reccallcount
        self.it = it
        self.tt = tt
        self.w_calls = w_sublist

    def get_calls(self, space):
        return self.w_calls

    def repr(self, space):
        frame_repr = space.str_w(space.repr(self.frame))
        if not self.w_calls:
            calls_repr = "None"
        else:
            calls_repr = space.str_w(space.repr(self.w_calls))
        return space.wrap('("%s", %d, %d, %f, %f, %s)' % (
            frame_repr, self.callcount, self.reccallcount,
            self.tt, self.it, calls_repr))

    def get_code(self, space):
        return self.frame

W_StatsEntry.typedef = TypeDef(
    'StatsEntry',
    code = GetSetProperty(W_StatsEntry.get_code),
    callcount = interp_attrproperty('callcount', W_StatsEntry),
    reccallcount = interp_attrproperty('reccallcount', W_StatsEntry),
    inlinetime = interp_attrproperty('it', W_StatsEntry),
    totaltime = interp_attrproperty('tt', W_StatsEntry),
    calls = GetSetProperty(W_StatsEntry.get_calls),
    __repr__ = interp2app(W_StatsEntry.repr),
)

class W_StatsSubEntry(Wrappable):
    def __init__(self, space, frame, callcount, reccallcount, tt, it):
        self.frame = frame
        self.callcount = callcount
        self.reccallcount = reccallcount
        self.it = it
        self.tt = tt

    def repr(self, space):
        frame_repr = space.str_w(space.repr(self.frame))
        return space.wrap('("%s", %d, %d, %f, %f)' % (
            frame_repr, self.callcount, self.reccallcount, self.tt, self.it))

    def get_code(self, space):
        return self.frame

W_StatsSubEntry.typedef = TypeDef(
    'SubStatsEntry',
    code = GetSetProperty(W_StatsSubEntry.get_code),
    callcount = interp_attrproperty('callcount', W_StatsSubEntry),
    reccallcount = interp_attrproperty('reccallcount', W_StatsSubEntry),
    inlinetime = interp_attrproperty('it', W_StatsSubEntry),
    totaltime = interp_attrproperty('tt', W_StatsSubEntry),
    __repr__ = interp2app(W_StatsSubEntry.repr),
)

def stats(space, values, factor):
    l_w = []
    for v in values:
        if v.callcount != 0:
            l_w.append(v.stats(space, None, factor))
    return space.newlist(l_w)

class ProfilerSubEntry(object):
    def __init__(self, frame):
        self.frame = frame
        self.ll_tt = r_longlong(0)
        self.ll_it = r_longlong(0)
        self.callcount = 0
        self.recursivecallcount = 0
        self.recursionLevel = 0

    def stats(self, space, parent, factor):
        w_sse = W_StatsSubEntry(space, self.frame,
                                self.callcount, self.recursivecallcount,
                                factor * float(self.ll_tt),
                                factor * float(self.ll_it))
        return space.wrap(w_sse)

    def _stop(self, tt, it):
        if not we_are_translated():
            assert type(tt) is r_longlong
            assert type(it) is r_longlong
        self.recursionLevel -= 1
        if self.recursionLevel == 0:
            self.ll_tt += tt
        else:
            self.recursivecallcount += 1
        self.ll_it += it
        self.callcount += 1

class ProfilerEntry(ProfilerSubEntry):
    def __init__(self, frame):
        ProfilerSubEntry.__init__(self, frame)
        self.calls = {}

    def stats(self, space, dummy, factor):
        if self.calls:
            w_sublist = space.newlist([sub_entry.stats(space, self, factor)
                                       for sub_entry in self.calls.values()])
        else:
            w_sublist = space.w_None
        w_se = W_StatsEntry(space, self.frame, self.callcount,
                            self.recursivecallcount,
                            factor * float(self.ll_tt),
                            factor * float(self.ll_it), w_sublist)
        return space.wrap(w_se)

    @jit.purefunction
    def _get_or_make_subentry(self, entry, make=True):
        try:
            return self.calls[entry]
        except KeyError:
            if make:
                subentry = ProfilerSubEntry(entry.frame)
                self.calls[entry] = subentry
                return subentry
            return None

class ProfilerContext(object):
    def __init__(self, profobj, entry):
        self.entry = entry
        self.ll_subt = r_longlong(0)
        self.previous = profobj.current_context
        entry.recursionLevel += 1
        if profobj.subcalls and self.previous:
            caller = jit.hint(self.previous.entry, promote=True)
            subentry = caller._get_or_make_subentry(entry)
            subentry.recursionLevel += 1
        self.ll_t0 = profobj.ll_timer()

    def _stop(self, profobj, entry):
        tt = profobj.ll_timer() - self.ll_t0
        it = tt - self.ll_subt
        if self.previous:
            self.previous.ll_subt += tt
        entry._stop(tt, it)
        if profobj.subcalls and self.previous:
            caller = jit.hint(self.previous.entry, promote=True)
            subentry = caller._get_or_make_subentry(entry, False)
            if subentry is not None:
                subentry._stop(tt, it)

def create_spec(space, w_arg):
    if isinstance(w_arg, Method):
        w_function = w_arg.w_function
        if isinstance(w_function, Function):
            name = w_function.name
        else:
            name = '?'
        # try to get the real class that defines the method,
        # which is a superclass of the class of the instance
        from pypy.objspace.std.typeobject import W_TypeObject   # xxx
        w_type = w_arg.w_class
        class_name = w_type.getname(space)    # if the rest doesn't work
        if isinstance(w_type, W_TypeObject) and name != '?':
            w_realclass, _ = space.lookup_in_type_where(w_type, name)
            if isinstance(w_realclass, W_TypeObject):
                class_name = w_realclass.get_module_type_name()
        return "{method '%s' of '%s' objects}" % (name, class_name)
    elif isinstance(w_arg, Function):
        if w_arg.w_module is None:
            module = ''
        else:
            module = space.str_w(w_arg.w_module)
            if module == '__builtin__':
                module = ''
            else:
                module += '.'
        return '{%s%s}' % (module, w_arg.name)
    else:
        class_name = space.type(w_arg).getname(space, '?')
        return "{'%s' object}" % (class_name,)

def lsprof_call(space, w_self, frame, event, w_arg):
    assert isinstance(w_self, W_Profiler)
    if event == 'call':
        code = frame.getcode()
        w_self._enter_call(code)
    elif event == 'return':
        code = frame.getcode()
        w_self._enter_return(code)
    elif event == 'c_call':
        if w_self.builtins:
            key = create_spec(space, w_arg)
            w_self._enter_builtin_call(key)
    elif event == 'c_return':
        if w_self.builtins:
            key = create_spec(space, w_arg)
            w_self._enter_builtin_return(key)
    else:
        # ignore or raise an exception???
        pass

class W_Profiler(Wrappable):
    
    def __init__(self, space, w_callable, time_unit, subcalls, builtins):
        self.subcalls = subcalls
        self.builtins = builtins
        self.current_context = None
        self.w_callable = w_callable
        self.time_unit = time_unit
        self.data = {}
        self.builtin_data = {}
        self.space = space
        self.is_enabled = False
        self.total_timestamp = r_longlong(0)
        self.total_real_time = 0.0

    def ll_timer(self):
        if self.w_callable:
            space = self.space
            try:
                return space.r_longlong_w(space.call_function(self.w_callable))
            except OperationError, e:
                e.write_unraisable(space, "timer function ",
                                   self.w_callable)
                return r_longlong(0)
        return read_timestamp()

    def enable(self, space, w_subcalls=NoneNotWrapped,
               w_builtins=NoneNotWrapped):
        if self.is_enabled:
            return      # ignored
        if w_subcalls is not None:
            self.subcalls = space.bool_w(w_subcalls)
        if w_builtins is not None:
            self.builtins = space.bool_w(w_builtins)
        # We want total_real_time and total_timestamp to end up containing
        # (endtime - starttime).  Now we are at the start, so we first
        # have to subtract the current time.
        self.is_enabled = True
        self.total_real_time -= time.time()
        self.total_timestamp -= read_timestamp()
        # set profiler hook
        c_setup_profiling()
        space.getexecutioncontext().setllprofile(lsprof_call, space.wrap(self))

    @jit.purefunction
    def _get_or_make_entry(self, f_code, make=True):
        try:
            return self.data[f_code]
        except KeyError:
            if make:
                entry = ProfilerEntry(f_code)
                self.data[f_code] = entry
                return entry
            return None

    @jit.purefunction
    def _get_or_make_builtin_entry(self, key, make=True):
        try:
            return self.builtin_data[key]
        except KeyError:
            if make:
                entry = ProfilerEntry(self.space.wrap(key))
                self.builtin_data[key] = entry
                return entry
            return None

    def _enter_call(self, f_code):
        # we have a superb gc, no point in freelist :)
        self = jit.hint(self, promote=True)
        entry = self._get_or_make_entry(f_code)
        self.current_context = ProfilerContext(self, entry)

    def _enter_return(self, f_code):
        context = self.current_context
        if context is None:
            return
        self = jit.hint(self, promote=True)
        entry = self._get_or_make_entry(f_code, False)
        if entry is not None:
            context._stop(self, entry)
        self.current_context = context.previous

    def _enter_builtin_call(self, key):
        self = jit.hint(self, promote=True)
        entry = self._get_or_make_builtin_entry(key)
        self.current_context = ProfilerContext(self, entry)

    def _enter_builtin_return(self, key):
        context = self.current_context
        if context is None:
            return
        self = jit.hint(self, promote=True)
        entry = self._get_or_make_builtin_entry(key, False)
        if entry is not None:
            context._stop(self, entry)
        self.current_context = context.previous

    def _flush_unmatched(self):
        context = self.current_context
        while context:
            entry = context.entry
            if entry:
                context._stop(self, entry)
            context = context.previous
        self.current_context = None

    def disable(self, space):
        if not self.is_enabled:
            return      # ignored
        # We want total_real_time and total_timestamp to end up containing
        # (endtime - starttime), or the sum of such intervals if
        # enable() and disable() are called several times.
        self.is_enabled = False
        self.total_timestamp += read_timestamp()
        self.total_real_time += time.time()
        # unset profiler hook
        space.getexecutioncontext().setllprofile(None, None)
        c_teardown_profiling()
        self._flush_unmatched()

    def getstats(self, space):
        if self.w_callable is None:
            if self.is_enabled:
                raise OperationError(space.w_RuntimeError,
                    space.wrap("Profiler instance must be disabled "
                               "before getting the stats"))
            if self.total_timestamp:
                factor = self.total_real_time / float(self.total_timestamp)
            else:
                factor = 1.0     # probably not used
        elif self.time_unit > 0.0:
            factor = self.time_unit
        else:
            factor = 1.0 / sys.maxint
        return stats(space, self.data.values() + self.builtin_data.values(),
                     factor)

@unwrap_spec(time_unit=float, subcalls=bool, builtins=bool)
def descr_new_profile(space, w_type, w_callable=NoneNotWrapped, time_unit=0.0,
                      subcalls=True, builtins=True):
    p = space.allocate_instance(W_Profiler, w_type)
    p.__init__(space, w_callable, time_unit, subcalls, builtins)
    return space.wrap(p)

W_Profiler.typedef = TypeDef(
    'Profiler',
    __module__ = '_lsprof',
    __new__ = interp2app(descr_new_profile),
    enable = interp2app(W_Profiler.enable),
    disable = interp2app(W_Profiler.disable),
    getstats = interp2app(W_Profiler.getstats),
)
