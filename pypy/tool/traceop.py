import autopath

from pypy.tool import pydis
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.objspace import trace

from pypy.objspace.trace import TraceObjSpace
from pypy.objspace.trivial import TrivialObjSpace

from pypy.interpreter.gateway import app2interp

# Global
operations = dict([(r[0], r[0]) for r in ObjSpace.MethodTable])


def perform_trace(space, app_func, *args, **kwds):
    # Wrap up our space, with a trace space
    tspace = TraceObjSpace(space)

    # Add our function
    func_gw = app2interp(app_func) 
    func = func_gw.get_function(tspace)

    # Run the func in the trace space and return results
    tspace.settrace()
    funcres = func(*args, **kwds) 
    traceres = tspace.getresult()
    return funcres, traceres  


def trace_function(space, fn, *arg, **kwds):
    funcres, traceres = perform_trace(space, fn, *arg, **kwds)
    disresult = pydis.pydis(fn)

    for event in traceres.getevents():
        if isinstance(event, trace.ExecBytecode):
            print event.index, "      ", disresult.getbytecode(event.index)
        elif isinstance(event, trace.CallBegin):
            info = event.callinfo
            if info.name in operations:
                print info.name, info.args, info.kwargs
        else:
            pass


    return funcres, traceres


def app_test():
    a = 1
    x = range(1)
    b = [1,2,3,4,5,6,7,8,9,10]
    for ii in b:
        a += ii

    return "Hello World"


def test():
    space = TrivialObjSpace()
    funcres, traceres =  trace_function(space, app_test)
    print "function result -->", funcres
    

test()
                   
"""
import repr
def get_repr():
    " Our own repr function for pretty print. "
    repr_obj = repr.Repr()
    repr_obj.maxstring = 120
    repr_obj.maxother = 120

    def our_repr(*args):
        try:
            return repr_obj.repr(*args)

        except:
            return "ERROR"

    return our_repr
"""
 
## def rpretty_print(spacedump):
##     " Pretty print for rdump() calls to Trace object spaces. "

##     Repr = get_repr()
##     for operation, bytecodes in spacedump:
##         for opcode, opname, oparg, ins_idx in bytecodes:
##             print "\t%s\t%s\t\t%s"  % (ins_idx, opname, oparg) 

##         if operation is not None:
##             op_name = operation[0]
##             args = operation[1:]
##             print " ***\t", op_name, " ->",
##             for a in args:
##                 print Repr(a),
##             print


## def add_func(space, func, w_globals):
##     """ Add a function to globals. """
##     func_name = func.func_name
##     w_func_name = space.wrap(func_name)
##     w_func = space.wrap(func)
##     space.setitem(w_globals, w_func_name, w_func)


## def run_in_space(space, func, *args):
##     # Get execution context and globals
##     ec = space.getexecutioncontext()
##     w_globals = ec.make_standard_w_globals()

##     # Add the function to globals
##     add_func(space, func, w_globals)

##     # Create wrapped args
##     args_w = [space.wrap(ii) for ii in args]
##     code = func.func_code
##     code = PyCode()._from_code(code)

##     # Create frame
##     frame = code.create_frame(space, w_globals)
##     frame.setfastscope(args_w)
    
##     # start/stop tracing while running frame
##     space.start_tracing()
##     res = frame.run()
##     space.stop_tracing()

##     return res


## def pretty_print(spacedump):
##     " Pretty print for rdump() calls to Trace object spaces. "
##     Repr = get_repr()

##     for line in spacedump:
##         ((opcode, opname, arg, ins_idx), spaceops) = line
##         start = "%4i %s " % (ins_idx, opname)
##         start = start + " " * (20 - len(start)) + str(arg)
##         start = start + " " * (30 - len(start))
##         if not spaceops:
##             print start
##         else:
##             op = spaceops.pop(0)
##             print start
##             for op_name, args in spaceops:
##                 print " " * 30, op_name, Repr(args)


## def _trace_function(space, reverse_pretty_print_flag, fn, *arg, **kwds):
##     res = run_in_space(space, fn, *arg, **kwds)
##     if reverse_pretty_print_flag:
##         # Get reverse dump
##         spacedump = space.rdump()

##         # Pretty print dump
##         rpretty_print(spacedump)
##     else:
##         # Get dump
##         spacedump = space.dump()

##         # Pretty dump
##         pretty_print(spacedump)

##     return res

## def trace_function(trace_space, fn, *arg, **kwds):
##     return _trace_function(trace_space, False, fn, *arg, **kwds)

## def rtrace_function(trace_space, fn, *arg, **kwds):
##     return _trace_function(trace_space, True, fn, *arg, **kwds)


## def trace_function2(space, fn, *arg, **kwds):
##     return _trace_function(Trace(space), False, fn, *arg, **kwds)

## def rtrace_function2(space, fn, *arg, **kwds):
##     return _trace_function(Trace(space), True, fn, *arg, **kwds)


                   
 
## ## # Create space
## ## if __name__ == "__main__":
## ##     try:
## ##         import readline
## ##     except ImportError:
## ##         pass

## ##     from pypy.tool import option
## ##     from pypy.tool import test
## ##     args = option.process_options(option.get_standard_options(),
## ##                                   option.Options)
## ##     objspace = option.objspace()


## ##     def run(*args, **kwds):
## ##     def run_function(space, func, *args):
## ##     from pypy.objspace.std import StdObjSpace
## ##     space = Trace(StdObjSpace)



