
from pypy.interpreter.baseobjspace import (W_Root, ObjSpace, Wrappable,
                                           Arguments)
from pypy.interpreter.typedef import (TypeDef, GetSetProperty,
                                      interp_attrproperty)
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.function import Method, Function
import time, sys

class W_StatsEntry(Wrappable):
    def __init__(self, space, frame, callcount, reccallcount, tt, it,
                 w_sublist):
        self.frame = frame
        self.callcount = callcount
        self.reccallcount = reccallcount
        self.it = it
        self.tt = tt
        self.w_calls = w_sublist

    def get_calls(space, self):
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
    repr.unwrap_spec = ['self', ObjSpace]

    def get_code(space, self):
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
    repr.unwrap_spec = ['self', ObjSpace]

    def get_code(space, self):
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
            l_w.append(v.stats(space, factor))
    return space.newlist(l_w)

class ProfilerEntry(object):
    def __init__(self, frame):
        self.frame = frame
        self.tt = 0
        self.it = 0
        self.callcount = 0
        self.recursivecallcount = 0
        self.recursionLevel = 0
        self.calls = {}

    def stats(self, space, factor):
        if self.calls:
            w_sublist = space.newlist([sub_entry.stats(space, self, factor)
                                       for sub_entry in self.calls.values()])
        else:
            w_sublist = space.w_None
        w_se = W_StatsEntry(space, self.frame, self.callcount,
                            self.recursivecallcount,
                            factor * self.tt, factor * self.it, w_sublist)
        return space.wrap(w_se)

class ProfilerSubEntry(object):
    def __init__(self, frame):
        self.frame = frame
        self.tt = 0
        self.it = 0
        self.callcount = 0
        self.recursivecallcount = 0
        self.recursionLevel = 0

    def stats(self, space, parent, factor):
        w_sse = W_StatsSubEntry(space, self.frame,
                                self.callcount, self.recursivecallcount,
                                factor * self.tt, factor * self.it)
        return space.wrap(w_sse)

class ProfilerContext(object):
    def __init__(self, profobj, entry):
        self.entry = entry
        self.subt = 0
        self.previous = profobj.current_context
        entry.recursionLevel += 1
        if profobj.subcalls and self.previous:
            caller = self.previous.entry
            try:
                subentry = caller.calls[entry]
            except KeyError:
                subentry = ProfilerSubEntry(entry.frame)
                caller.calls[entry] = subentry
            subentry.recursionLevel += 1
        self.t0 = profobj.timer()

    def _stop(self, profobj, entry):
        # XXX factor out two pieces of the same code
        tt = profobj.timer() - self.t0
        it = tt - self.subt
        if self.previous:
            self.previous.subt += tt
        entry.recursionLevel -= 1
        if entry.recursionLevel == 0:
            entry.tt += tt
        else:
            entry.recursivecallcount += 1
        entry.it += it
        entry.callcount += 1
        if profobj.subcalls and self.previous:
            caller = self.previous.entry
            try:
                subentry = caller.calls[entry]
            except KeyError:
                pass
            else:
                subentry.recursionLevel -= 1
                if subentry.recursionLevel == 0:
                    subentry.tt += tt
                else:
                    subentry.recursivecallcount += 1
                subentry.it += it
                subentry.callcount += 1

def create_spec(space, w_arg):
    if isinstance(w_arg, Method):
        w_function = w_arg.w_function
        class_name = w_arg.w_class.getname(space, '?')
        assert isinstance(w_function, Function)
        return "{method '%s' of '%s' objects}" % (w_function.name, class_name)
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
        return '{!!!unknown!!!}'
    
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

    def timer(self):
        if self.w_callable:
            space = self.space
            return space.float_w(space.call_function(self.w_callable))
        return time.time()

    def enable(self, space, w_subcalls=NoneNotWrapped,
               w_builtins=NoneNotWrapped):
        if w_subcalls is not None:
            self.subcalls = space.bool_w(w_subcalls)
        if w_builtins is not None:
            self.builtins = space.bool_w(w_builtins)
        # set profiler hook
        space.getexecutioncontext().setllprofile(lsprof_call, space.wrap(self))
    enable.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def _enter_call(self, f_code):
        # we have a superb gc, no point in freelist :)
        try:
            entry = self.data[f_code]
        except KeyError:
            entry = ProfilerEntry(f_code)
            self.data[f_code] = entry
        self.current_context = ProfilerContext(self, entry)

    def _enter_return(self, f_code):
        context = self.current_context
        if context is None:
            return
        try:
            entry = self.data[f_code]
            context._stop(self, entry)
        except KeyError:
            pass
        self.current_context = context.previous

    def _enter_builtin_call(self, key):
        try:
            entry = self.builtin_data[key]
        except KeyError:
            entry = ProfilerEntry(self.space.wrap(key))
            self.builtin_data[key] = entry
        self.current_context = ProfilerContext(self, entry)        

    def _enter_builtin_return(self, key):
        context = self.current_context
        if context is None:
            return
        try:
            entry = self.builtin_data[key]
            context._stop(self, entry)
        except KeyError:
            pass
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
        # unset profiler hook
        space.getexecutioncontext().setllprofile(None, None)
        self._flush_unmatched()
    disable.unwrap_spec = ['self', ObjSpace]

    def getstats(self, space):
        if self.w_callable is None:
            factor = 1. # we measure time.time in floats
        elif self.time_unit > 0.0:
            factor = self.time_unit
        else:
            factor = 1.0 / sys.maxint
        return stats(space, self.data.values() + self.builtin_data.values(),
                     factor)
    getstats.unwrap_spec = ['self', ObjSpace]

def descr_new_profile(space, w_type, w_callable=NoneNotWrapped, time_unit=0.0,
                      subcalls=True, builtins=True):
    p = space.allocate_instance(W_Profiler, w_type)
    p.__init__(space, w_callable, time_unit, subcalls, builtins)
    return space.wrap(p)
descr_new_profile.unwrap_spec = [ObjSpace, W_Root, W_Root, float, bool, bool]

W_Profiler.typedef = TypeDef(
    'Profiler',
    __new__ = interp2app(descr_new_profile),
    enable = interp2app(W_Profiler.enable),
    disable = interp2app(W_Profiler.disable),
    getstats = interp2app(W_Profiler.getstats),
)
