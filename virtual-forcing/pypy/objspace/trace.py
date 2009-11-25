"""
   Trace object space traces operations and bytecode execution
   in frames.
"""

from pypy.tool import pydis
from pypy.rlib.rarithmetic import intmask
# __________________________________________________________________________
#
# Tracing Events 
# __________________________________________________________________________
#

class ExecBytecode(object):
    """ bytecode trace. """
    def __init__(self, frame):
        self.frame = frame
        self.code = frame.pycode
        self.index = intmask(frame.last_instr)

class EnterFrame(object):
    def __init__(self, frame):
        self.frame = frame

class LeaveFrame(object):
    def __init__(self, frame):
        self.frame = frame

class CallInfo(object):
    """ encapsulates a function call with its arguments. """
    def __init__(self, name, func, args, kwargs):
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs

class CallBegin(object):
    def __init__(self, callinfo):
        self.callinfo = callinfo

class CallFinished(object):
    def __init__(self, callinfo, res):
        self.callinfo = callinfo
        self.res = res
        
class CallException(object):
    def __init__(self, callinfo, e):
        self.callinfo = callinfo
        self.ex = e
                
class TraceResult(object):
    """ This is the state of tracing-in-progress. """
    def __init__(self, tracespace, **printer_options):
        self.events = []
        self.reentrant = True
        self.tracespace = tracespace
        result_printer_clz = printer_options["result_printer_clz"]
        self.printer = result_printer_clz(**printer_options)
        self._cache = {}
        
    def append(self, event):
        if self.reentrant:
            self.reentrant = False
            self.events.append(event)
            self.printer.print_event(self.tracespace, self, event)
            self.reentrant = True

    def getbytecodes(self):
        for event in self.events:
            if isinstance(event, ExecBytecode):
                disres = self.getdisresult(event.frame)
                yield disres.getbytecode(event.index)

    def getoperations(self):
        for event in self.events:
            if isinstance(event, (CallBegin, CallFinished, CallException)):
                yield event
                
    def getevents(self):
        for event in self.events:
            yield event

    def getdisresult(self, frame):
        """ return (possibly cached) pydis result for the given frame. """

        try:
            return self._cache[id(frame.pycode)]
        except KeyError:
            res = self._cache[id(frame.pycode)] = pydis.pydis(frame.pycode)
            assert res is not None
            return res

# __________________________________________________________________________
#
# Tracer Proxy objects 
# __________________________________________________________________________
#

class ExecutionContextTracer(object):
    def __init__(self, result, ec):
        self.ec = ec
        self.result = result
        
    def __getattr__(self, name):
        """ generically pass through everything else ... """
        return getattr(self.ec, name)

    def enter(self, frame):
        """ called just before (continuing to) evaluating a frame. """
        self.result.append(EnterFrame(frame))
        self.ec.enter(frame)

    def leave(self, frame):
        """ called just after evaluating of a frame is suspended/finished. """
        self.result.append(LeaveFrame(frame))
        self.ec.leave(frame)

    def bytecode_trace(self, frame):
        """ called just before execution of a bytecode. """
        self.result.append(ExecBytecode(frame))
        self.ec.bytecode_trace(frame)

class CallableTracer(object):
    def __init__(self, result, name, func):
        self.result = result
        self.name = name
        self.func = func
        
    def __call__(self, *args, **kwargs):
        callinfo = CallInfo(self.name, self.func, args, kwargs) 
        self.result.append(CallBegin(callinfo))

        try:
            res = self.func(*args, **kwargs)
        except Exception, e:
            self.result.append(CallException(callinfo, e))
            raise 
        else:
            self.result.append(CallFinished(callinfo, res))
            return res

    def __getattr__(self, name):
        """ generically pass through everything we don't intercept. """
        return getattr(self.func, name)

    def __str__(self):
        return "%s - CallableTracer(%s)" % (self.name, self.func)

    __repr__ = __str__

# __________________________________________________________________________
#
# Tracer factory 
# __________________________________________________________________________
#            

def create_trace_space(space):    
    """ Will turn the supplied into a traceable space by extending its class."""

    # Don't trace an already traceable space
    if hasattr(space, "__pypytrace__"):
        return space

    class Trace(space.__class__):

        def __getattribute__(self, name):
            obj = super(Trace, self).__getattribute__(name)
            if name in ["_result", "_in_cache", "_ect_cache",
                        "_tracing", "_config_options"]:
                return obj

            if not self._tracing or self._in_cache:
                return obj

            if name in self._config_options["operations"]:
                assert callable(obj)
                obj = CallableTracer(self._result, name, obj)
                            
            return obj

        def __pypytrace__(self):
            pass

        def enter_cache_building_mode(self):
            self._in_cache += 1

        def leave_cache_building_mode(self, val):
            self._in_cache -= 1

        def settrace(self):
            self._result = TraceResult(self, **self._config_options)
            self._ect_cache = {}
            self._tracing = True

        def unsettrace(self):
            self._tracing = False
            
        def getresult(self):
            return self._result
            
        def getexecutioncontext(self):
            ec = super(Trace, self).getexecutioncontext()
            if not self._in_cache:
                try:
                    ect = self._ect_cache[ec]
                except KeyError:
                    assert not isinstance(ec, ExecutionContextTracer)
                    ect = ExecutionContextTracer(self._result, ec)
                    self._ect_cache[ec] = ect
                return ect
            return ec
        
        # XXX Rename
        def reset_trace(self):
            """ Returns the class to its original form. """
            space.__class__ = space.__oldclass__
            del space.__oldclass__

            for k in ["_result", "_in_cache", "_ect_cache",
                      "_config_options", "_operations"]:
                if hasattr(self, k):
                    delattr(self, k)
            
    trace_clz = type("Trace%s" % repr(space), (Trace,), {})
    space.__oldclass__, space.__class__ = space.__class__, trace_clz

    # Do config
    from pypy.tool.traceconfig import config
    space._tracing = False
    space._result = None
    space._ect_cache = {}
    space._in_cache = 0
    space._config_options = config

    space.settrace()
    return space

# ______________________________________________________________________
# End of trace.py
