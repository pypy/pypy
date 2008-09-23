
from pypy.interpreter.baseobjspace import (W_Root, ObjSpace, Wrappable,
                                           Arguments)
from pypy.interpreter.typedef import (TypeDef, GetSetProperty,
                                      interp_attrproperty)
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
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

W_StatsEntry.typedef = TypeDef(
    'StatsEntry',
    code = interp_attrproperty('frame', W_StatsEntry),
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

W_StatsSubEntry.typedef = TypeDef(
    'SubStatsEntry',
    code = interp_attrproperty('frame', W_StatsSubEntry),
    callcount = interp_attrproperty('callcount', W_StatsSubEntry),
    reccallcount = interp_attrproperty('reccallcount', W_StatsSubEntry),
    inlinetime = interp_attrproperty('it', W_StatsSubEntry),
    totaltime = interp_attrproperty('tt', W_StatsSubEntry),
    __repr__ = interp2app(W_StatsSubEntry.repr),
)

def stats(space, data, factor):
    l_w = []
    for v in data.values():
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
    
def lsprof_call(space, w_self, frame, event, w_arg):
    assert isinstance(w_self, W_Profiler)
    if event == 'call':
        w_self._enter_call(frame.getcode())
    elif event == 'return':
        w_self._enter_return(frame.getcode())
    else:
        raise NotImplementedError("Call to %s" % event)
    # we don't support builtin calls here...

class W_Profiler(Wrappable):
    def __init__(self, space, w_callable, time_unit, subcalls, builtins):
        self.subcalls = subcalls
        self.builtins = builtins
        self.current_context = None
        self.w_callable = w_callable
        self.time_unit = time_unit
        # XXX _lsprof uses rotatingtree. We use plain dict here,
        #     not sure how big difference is, but we should probably
        #     implement rotating tree
        self.data = {}
        self.space = space

    def timer(self):
        if self.w_callable:
            space = self.space
            return space.float_w(space.call_function(self.w_callable))
        return time.time()

    def enable(self, space, subcalls=True, builtins=True):
        self.subcalls = subcalls
        self.builtins = builtins
        # set profiler hook
        space.getexecutioncontext().setllprofile(lsprof_call, space.wrap(self))
    enable.unwrap_spec = ['self', ObjSpace, bool, bool]

    def _enter_call(self, f_code):
        # we have superb gc, no point in freelist :)
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
        self._flush_unmatched()
        space.getexecutioncontext().setllprofile(None, None)
    disable.unwrap_spec = ['self', ObjSpace]

    def getstats(self, space):
        if self.w_callable is None:
            factor = 1. # we measure time.time in floats
        elif self.time_unit > 0.0:
            factor = self.time_unit
        else:
            factor = 1.0 / sys.maxint
        return stats(space, self.data, factor)
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
