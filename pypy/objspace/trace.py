""" 
   trace object space traces operations and bytecode execution
   in frames. 

"""
from __future__ import generators
from pypy.tool import pydis 

# __________________________________________________________________________
#
# Tracing Events 
# __________________________________________________________________________

class ExecBytecode:
    def __init__(self, frame):
        self.frame = frame
        self.index = frame.next_instr

class EnterFrame:
    def __init__(self, frame):
        self.frame = frame

class LeaveFrame:
    def __init__(self, frame):
        self.frame = frame

class CallBegin:
    def __init__(self, callinfo):
        self.callinfo = callinfo

class CallFinished:
    def __init__(self, callinfo):
        self.callinfo = callinfo

class CallException:
    def __init__(self, e, callinfo):
        self.ex = e
        self.callinfo = callinfo

# __________________________________________________________________________
#
# Tracer Proxy objects 
# __________________________________________________________________________
#
class ExecutionContextTracer:
    def __init__(self, result, ec):
        self.ec = ec
        self.result = result

    def __getattr__(self, name):
        """ generically pass through everything we don'T have explicit
            interceptors for. 
    
        """
        print "trying", name
        return getattr(self.ec, name)

    def enter(self, frame):
        """ called just before (continuing to) evaluating a frame. """
        self.result.append(EnterFrame(frame))
        return self.ec.enter(frame)

    def leave(self, previous_ec):
        """ called just after evaluating of a frame is suspended/finished. """
        frame = self.ec.framestack.top()
        self.result.append(LeaveFrame(frame))
        return self.ec.leave(previous_ec)

    def bytecode_trace(self, frame):
        "called just before execution of a bytecode."
        self.result.append(ExecBytecode(frame))

    #def exception_trace(self, operror):
    #    "called if the current frame raises an operation error. """

class CallInfo:
    """ encapsulates a function call with its arguments. """
    def __init__(self, name, func, args, kwargs):
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs

class CallableTracer:
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
            self.result.append(CallException(e, callinfo))
            raise 
        else:
            self.result.append(CallFinished(callinfo))
            return res


class TraceObjSpace:
    def __init__(self, space):
        self.space = space
        self.settrace()

    def settrace(self):
        self.result = TraceResult(self)

    def getresult(self):
        return self.result
        
    def __getattr__(self, name):
        obj = getattr(self.space, name)
        if callable(obj):
            return CallableTracer(self.result, name, obj)
        # XXX some attribute has been accessed, we don't care
        return obj

    def getexecutioncontext(self):
        ec = self.space.getexecutioncontext()
        if isinstance(ec, ExecutionContextTracer):
            return ec
        return ExecutionContextTracer(self.result, ec)

    def createexecutioncontext(self):
        ec = self.space.createexecutioncontext()
        return ExecutionContextTracer(self.result, ec)

    def __hash__(self):
        return hash(self.space)

class TraceResult:
    """ this is the state of tracing-in-progress. """
    def __init__(self, tracespace):
        self.tracespace = tracespace
        self.events = []  

    def append(self, arg):
        self.events.append(arg)

    def getdisresult(self, frame, _cache = {}):
        """ return (possibly cached) pydis result for the given frame. """
        try:
            return _cache[id(frame)]
        except KeyError:
            res = _cache[id(frame)] = pydis.pydis(frame.code)
            assert res is not None
            return res

    def getbytecodes(self):
        lastframe = None
        for event in self.events:
            #if isinstance(event, EnterFrame):
            #    lastframe = event.frame
            if isinstance(event, ExecBytecode):
                disres = self.getdisresult(event.frame)
                yield disres.getbytecode(event.index)

    def getoperations(self):
        for event in self.events:
            #if isinstance(event, EnterFrame):
            #    lastframe = event.frame
            if isinstance(event, CallBegin):
                yield event.callinfo

Space = TraceObjSpace

# ______________________________________________________________________
# End of trace.py

"""
def display(bytecodedict, codeobject):
    for i in range(len(codeobject.co_bytecode)):
        print display_bytecode(codeobject, i)
        if i in bytecodedict:
            for opinfo in bytecodedict[i]:
                print display(*opinfo)
           
class FrameIndex:
    def __init__(self, frame, index):
        self.frame = frame
        self.index = index

    def __hash__(self):
        return hash((id(frame), index))
    def _getframeindex(self):
        frame = self.tracespace.space.getexecutioncontext().framestack[-1] 
        index = frame.next_instr 
        return FrameIndex(frame, index)
            
"""
