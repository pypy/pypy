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
    """ bytecode trace. """
    def __init__(self, frame):
        self.frame = frame 
        self.code = frame.code 
        self.index = frame.next_instr
        #assert self.index < len(frame.code.co_code)

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
        self.__ec = ec
        self.__result = result

    def __getattr__(self, name):
        """ generically pass through everything else ... """
        return getattr(self.__ec, name)

    def enter(self, frame):
        """ called just before (continuing to) evaluating a frame. """
        self.__result.append(EnterFrame(frame))
        return self.__ec.enter(frame)

    def leave(self, previous_ec):
        """ called just after evaluating of a frame is suspended/finished. """
        frame = self.__ec.framestack.top()
        self.__result.append(LeaveFrame(frame))
        return self.__ec.leave(previous_ec)

    def bytecode_trace(self, frame):
        "called just before execution of a bytecode."
        self.__result.append(ExecBytecode(frame))

    #def exception_trace(self, operror):
    #    "called if the current frame raises an operation error. "
    #    print "exception trace", operror
    #    return self.__ec.exception_trace(operror)

class CallInfo:
    """ encapsulates a function call with its arguments. """
    def __init__(self, name, func, args, kwargs):
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs

class CallableTracer:
    def __init__(self, result, name, func):
        self.__result = result
        self.__name = name
        self.__func = func

    def __call__(self, *args, **kwargs):
        callinfo = CallInfo(self.__name, self.__func, args, kwargs) 
        self.__result.append(CallBegin(callinfo))
        #print "calling into", self.__name, [type(x).__name__ for x in args]
        #print args
        try:
            res = self.__func(*args, **kwargs)
        except Exception, e:
            #self.__result.append(CallException(e, callinfo))
            raise 
        else:
            self.__result.append(CallFinished(callinfo))
            return res

    def __getattr__(self, name):
        """ generically pass through everything we don't intercept. """
        return getattr(self.__func, name)

class TraceObjSpace:
    def __init__(self, space):
        self.__space = space
        self.settrace()

    def settrace(self):
        self.__result = TraceResult(self)

    def getresult(self):
        return self.__result

    def getexecutioncontext(self):
        ec = self.__space.getexecutioncontext()
        if isinstance(ec, ExecutionContextTracer):
            return ec
        return ExecutionContextTracer(self.__result, ec)

    def createexecutioncontext(self):
        ec = self.__space.createexecutioncontext()
        return ExecutionContextTracer(self.__result, ec)

    def __getattr__(self, name):
        obj = getattr(self.__space, name)
        if callable(obj) and not hasattr(obj, '__bases__'):
            return CallableTracer(self.__result, name, obj)
        return obj

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
            return _cache[id(frame.code)]
        except KeyError:
            res = _cache[id(frame.code)] = pydis.pydis(frame.code)
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

    def getevents(self):
        for event in self.events:
            yield event
            

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
