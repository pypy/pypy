import autopath
import repr

from pypy.interpreter.pycode import PyCode
from pypy.objspace.std import StdObjSpace
from pypy.objspace.trivial import TrivialObjSpace
from pypy.objspace.trace import Trace


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

 
def rpretty_print(spacedump):
    " Pretty print for rdump() calls to Trace object spaces. "

    Repr = get_repr()
    for operation, bytecodes in spacedump:
        for opcode, opname, oparg, ins_idx in bytecodes:
            print "\t%s\t%s\t\t%s"  % (ins_idx, opname, oparg) 

        if operation is not None:
            op_name = operation[0]
            args = operation[1:]
            print " ***\t", op_name, " ->",
            for a in args:
                print Repr(a),
            print


def add_func(space, func, w_globals):
    """ Add a function to globals. """
    func_name = func.func_name
    w_func_name = space.wrap(func_name)
    w_func = space.wrap(func)
    space.setitem(w_globals, w_func_name, w_func)


def run_in_space(space, func, *args):
    # Get execution context and globals
    ec = space.getexecutioncontext()
    w_globals = ec.make_standard_w_globals()

    # Add the function to globals
    add_func(space, func, w_globals)

    # Create wrapped args
    args_w = [space.wrap(ii) for ii in args]
    code = func.func_code
    code = PyCode()._from_code(code)

    # Create frame
    frame = code.create_frame(space, w_globals)
    frame.setfastscope(args_w)
    
    # start/stop tracing while running frame
    space.start_tracing()
    res = frame.run()
    space.stop_tracing()

    return res


def pretty_print(spacedump):
    " Pretty print for rdump() calls to Trace object spaces. "
    Repr = get_repr()

    for line in spacedump:
        ((opcode, opname, arg, ins_idx), spaceops) = line
        start = "%4i %s " % (ins_idx, opname)
        start = start + " " * (20 - len(start)) + str(arg)
        start = start + " " * (30 - len(start))
        if not spaceops:
            print start
        else:
            op = spaceops.pop(0)
            print start
            for op_name, args in spaceops:
                print " " * 30, op_name, Repr(args)


def _trace_function(space, reverse_pretty_print_flag, fn, *arg, **kwds):
    res = run_in_space(space, fn, *arg, **kwds)
    if reverse_pretty_print_flag:
        # Get reverse dump
        spacedump = space.rdump()

        # Pretty print dump
        rpretty_print(spacedump)
    else:
        # Get dump
        spacedump = space.dump()

        # Pretty dump
        pretty_print(spacedump)

    return res

def trace_function(trace_space, fn, *arg, **kwds):
    return _trace_function(trace_space, False, fn, *arg, **kwds)

def rtrace_function(trace_space, fn, *arg, **kwds):
    return _trace_function(trace_space, True, fn, *arg, **kwds)


                   
 
## # Create space
## if __name__ == "__main__":
##     try:
##         import readline
##     except ImportError:
##         pass

##     from pypy.tool import option
##     from pypy.tool import test
##     args = option.process_options(option.get_standard_options(),
##                                   option.Options)
##     objspace = option.objspace()


##     def run(*args, **kwds):
##     def run_function(space, func, *args):
##     from pypy.objspace.std import StdObjSpace
##     space = Trace(StdObjSpace)
