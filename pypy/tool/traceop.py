
import autopath

from pypy.tool import pydis
from pypy.objspace import trace

def getdisresult(obj, _cache={}):
    """ return dissassemble result for the given obj which can be a
        pyframe or function or a code object. 
    """
    obj = getattr(obj, 'func_code', obj)
    obj = getattr(obj, 'code', obj)
    try:
        return _cache[obj]
    except KeyError:
        disresult = _cache[obj] = pydis.pydis(obj)
        return disresult

def line_begin(indent):
    if indent:
        return ("  " * indent) + "|-"
    else:
        return ""
    
def print_result(space, traceres, operations_level = 1000):
    # XXX Refactor this - make more configurable.
    indentor = '    '
    lastframe = None
    frame_count = 0
    indent = ""
    skip_frame_count = None
    stack_info = []
    for event in traceres.getevents():
        
        if isinstance(event, trace.EnterFrame):
            if not skip_frame_count:
                print line_begin(frame_count) + ("<<<<<enter %s @ %s>>>>>>>" % (event.frame.code.co_filename, event.frame.code.co_firstlineno))

            lastframe = event.frame
            frame_count += 1

        elif isinstance(event, trace.LeaveFrame):
            frame_count -= 1

            # No more bytecodes to skip at this level
            if frame_count < skip_frame_count:
                skip_frame_count = 0

            if not skip_frame_count:
                print line_begin(frame_count) + ("<<<<<leave %s >>>>>>>" % lastframe.code.co_filename)
        elif isinstance(event, trace.ExecBytecode):

            if frame_count == skip_frame_count:
                skip_frame_count = 0

            disresult = getdisresult(event.frame) 
            bytecode = disresult.getbytecode(event.index)

            if not skip_frame_count:
                print line_begin(frame_count), "%2d" % event.index, "      ", bytecode
            lastframe = event.frame

            if bytecode.name in ["PRINT_EXPR", "PRINT_ITEM", "PRINT_NEWLINE"]:
                print line_begin(frame_count + 1), "..."
                skip_frame_count = frame_count           

        elif isinstance(event, trace.CallBegin):
            info = event.callinfo
            if not skip_frame_count:
                stack_info.append(info)
                if len(stack_info) <= operations_level:
                    print line_begin(frame_count), " " * 17 + ">> ", info.name, repr_args(space, lastframe, info.args)
                frame_count += 1
                    
        elif isinstance(event, trace.CallFinished):
            info = event.callinfo
            if not skip_frame_count:
                assert stack_info.pop(-1) == event.callinfo
                frame_count -= 1
                if len(stack_info) < operations_level:
                    print line_begin(frame_count), " " * 20, info.name, "=: ", repr_value(space, event.res)
        
        elif isinstance(event, trace.CallException):
            info = event.callinfo
            if not skip_frame_count:
                assert stack_info.pop(-1) == event.callinfo
                frame_count -= 1
                if len(stack_info) < operations_level:
                    print line_begin(frame_count), " " * 17 + "x= ", info.name, event.ex
        else:
            pass
    
def repr_value(space, value):
##     try:
##         res = str(space.unwrap(value))
##     except:
##         res = str(value)
    res = str(value)
    return res[:240]

def repr_args(space, frame, args):
    l = []
    for arg in args:
        if frame and space.is_true(space.is_(arg, frame.w_globals)):
            l.append('w_globals')
        elif frame and space.is_true(space.is_(arg, space.w_builtins)):
            l.append('w_builtins')
        else:
            l.append(repr_value(space, arg))
            
    return "(" + ", ".join(l) + ")"


def perform_trace(tspace, app_func, *args_w, **kwds_w):
    from pypy.interpreter.gateway import app2interp
    from pypy.interpreter.argument import Arguments    

    # Create our function
    func_gw = app2interp(app_func)
    func = func_gw.get_function(tspace)
    w_func = tspace.wrap(func)
    args = Arguments(tspace, args_w, kwds_w)

    # Run the func in the trace space and return results
    tspace.settrace()
    w_result = tspace.call_args(w_func, args)
    trace_result = tspace.getresult()
    tspace.settrace()
    return w_result, trace_result


if __name__ == '__main__':
    from pypy.tool import option
    args = option.process_options(option.get_standard_options(),
                                  option.Options)

    # Create objspace...
    space = option.objspace()

    # Wrap up our space, with a trace space
    tspace = trace.create_trace_space(space)

    def app_test(x):
        count = 0
        for ii in range(x):
            count += ii
        return count

    res, traceres = perform_trace(tspace, app_test, tspace.wrap(5))
    print_result(tspace, traceres)

    print "Result", res
