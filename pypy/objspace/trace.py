"""
   Trace object space traces operations and bytecode execution
   in frames.
"""

from __future__ import generators
from pypy.tool import pydis
from pypy.tool.traceop import ResultPrinter
from pypy.interpreter.baseobjspace import ObjSpace

# __________________________________________________________________________
#
# Tracing Events 
# __________________________________________________________________________
#

class ExecBytecode(object):
    """ bytecode trace. """
    def __init__(self, frame):
        self.frame = frame
        self.code = frame.code
        self.index = frame.next_instr

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
    def __init__(self, tracespace):
        self.events = []
        self.reentrant = True
        self.tracespace = tracespace
        self.printer = ResultPrinter()

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

    def getdisresult(self, frame, _cache = {}): # XXX Should perhaps be local to TraceResult
        """ return (possibly cached) pydis result for the given frame. """

        try:
            return _cache[id(frame.code)]
        except KeyError:
            res = _cache[id(frame.code)] = pydis.pydis(frame.code)
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
        return self.ec.enter(frame)

    def leave(self, previous_ec, frame):
        """ called just after evaluating of a frame is suspended/finished. """
        self.result.append(LeaveFrame(frame))
        return self.ec.leave(previous_ec, frame)

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

operations = None
def get_operations():
    global operations
    if operations is None:
        operations = dict([(r[0], r[0]) for r in ObjSpace.MethodTable])
        for name in ObjSpace.IrregularOpTable + ["get_and_call_function"]:
            operations[name] = name

    # Remove list
    for name in ["wrap", "unwrap"]:
        if name in operations:
            del operations[name]
    return operations

def create_trace_space(space = None, operations = None):    
    """ Will create a trace object space if no space supplied.  Otherwise
    will turn the supplied into a tracable space by extending its class."""

    # Don't trace an already tracable space
    if hasattr(space, "__pypytrace__"):
        return space
    
    if space is None:
        # make up a TrivialObjSpace by default
        # ultimately, remove this hack and fix the -P option of tests
        from pypy.objspace import trivial
        space = trivial.TrivialObjSpace()

    if operations is None:
        operations = get_operations()

    class Trace(space.__class__):

        def __getattribute__(self, name):
            obj = super(Trace, self).__getattribute__(name)
            if name in operations:
                assert callable(obj)
                obj = CallableTracer(self._result, name, obj)
            return obj

        def __pypytrace__(self):
            pass

        def settrace(self):
            self._result = TraceResult(self)

        def getresult(self):
            return self._result
            
        def getexecutioncontext(self):
            ec = super(Trace, self).getexecutioncontext()
            assert not isinstance(ec, ExecutionContextTracer)
            return ExecutionContextTracer(self._result, ec)
        
        def reset_trace(self):
            """ Returns the class to it's original form. """
            space.__class__ = space.__oldclass__
            del space.__oldclass__

            if hasattr(self, "_result"):
                del self._result            

    trace_clz = type("Trace%s" % repr(space), (Trace,), {})
    space.__oldclass__, space.__class__ = space.__class__, trace_clz
    
    space.settrace()
    return space

# ______________________________________________________________________
# End of trace.py
