#
# support code for the trace object space
#
from __future__ import generators

import autopath

import sys

def reversed(seq):
    length = len(seq)
    for index in range(length-1, -1, -1):
        yield seq[index]

class Stack(list):
    push = list.append

    def pop(self):
        return super(Stack, self).pop(-1)

    def top(self):
        try:
            return self[-1]
        except IndexError:
            return None

class ResultPrinter:

    def __init__(self,
                 output_filename = None,
                 show_hidden_applevel = False,
                 recursive_operations = False,
                 show_bytecode = True,
                 indentor = '  ',
                 show_wrapped_consts_bytecode = True):

        if output_filename is None:
            self.out = sys.stdout
        else:
            self.out = open(output_filename, "w")
            
        # Configurable stuff
        self.indentor = indentor        
        self.show_bytecode = show_bytecode
        self.show_hidden_applevel = show_hidden_applevel
        self.recursive_operations = recursive_operations
        self.show_wrapped_consts_bytecode = show_wrapped_consts_bytecode

        # Keeps a stack of current state to handle
        # showing of applevel and recursive operations
        self.indent_state = Stack()

        # Some printing state
        self.last_line_was_new = True

    def reset(self):
        self.indent_state = Stack()

    def valid_state(self):
        state = self.indent_state.top()
        if state is not None and not state[0]:
            return False
        return True

    def print_line(self, line, new_line = True):
        if self.last_line_was_new:
            indent_count = len([c for c, t, f in self.indent_state if c])
            if indent_count:
                indent = indent_count - 1
                assert (indent >= 0)
                line = (self.indentor * indent) + "|-" + line 

        if new_line:
            self.last_line_was_new = True
            print >>self.out, line
        else:
            print >>self.out, line,
            self.last_line_was_new = False
                
    def print_frame(self, print_type, frame):
        if not self.valid_state():
            return
        
        # Force new line if not the case
        if not self.last_line_was_new:
            print >>self.out, ""
            self.last_line_was_new = True
            
        code = getattr(frame, 'code', None)
        filename = getattr(code, 'co_filename', "")
        filename = filename.replace("\n", "\\n")
        lineno = getattr(code, 'co_firstlineno', "")

        s = " <<<< %s %s @ %s >>>>" % (print_type, filename, lineno)
        self.print_line(s)        

    def print_bytecode(self, index, bytecode, space):
        if not self.valid_state():
            return
            
        if self.show_bytecode:
            if self.show_wrapped_consts_bytecode:
                bytecode_str = repr(bytecode)
            else:
                bytecode_str = bytecode.repr_with_space(space)

            s = "%2d%s%s" % (index, (self.indentor * 2), bytecode_str)
            self.print_line(s)

    def print_op_enter(self, space, name, args):
        if not self.valid_state():
            return

        s = " " * 4
        s += "%s" % name
        s += "(" + ", ".join([repr_value(space, ii) for ii in args]) + ")"
        self.print_line(s, new_line=False)
        
    def print_op_leave(self, space, name, res):
        if not self.valid_state():
            return

        if self.last_line_was_new:
            s = " " * 4
        else:
            s = "  "

        s += "-> %s" % repr_value(space, res)
        self.print_line(s)

    def print_op_exc(self, name, exc, space):
        if not self.valid_state():
            return

        if self.last_line_was_new:
            s = " " * 4
        else:
            s = "  "
        s += "-> <raised> (%s)" % repr_value(space, exc)

        self.print_line(s)

    def print_result(self, space, event_result):
        for event in event_result.getevents():
            print_event(space, event, event_result)
            
    def print_event(self, space, event_result, event):
        from pypy.objspace import trace
        
        if isinstance(event, trace.EnterFrame):
            frame = event.frame
            if self.show_hidden_applevel or not frame.code.hidden_applevel:
                show = True
            else:
                show = False

            self.indent_state.push((show, trace.EnterFrame, frame))
            self.print_frame("enter", frame)

        elif isinstance(event, trace.LeaveFrame):

            lastframe = self.indent_state.top()[2]
            assert lastframe is not None

            self.print_frame("leave", lastframe)           
            self.indent_state.pop()

        elif isinstance(event, trace.ExecBytecode):

            frame = event.frame
            assert (frame == self.get_last_frame())

            # Get bytecode from frame
            disresult = event_result.getdisresult(frame)
            bytecode = disresult.getbytecode(event.index)
            self.print_bytecode(event.index, bytecode, space)

        elif isinstance(event, trace.CallBegin):
            lastframe = self.get_last_frame()
            info = event.callinfo

            show = True

            # Check if we are in applevel?
            if not self.show_hidden_applevel:
                if lastframe is None or lastframe.code.hidden_applevel:
                    show = False

            # Check if recursive operations?
            prev_indent_state = self.indent_state.top()
            if not self.recursive_operations and prev_indent_state is not None:
                if prev_indent_state[1] == trace.CallBegin:
                    show = False

            self.indent_state.push((show, trace.CallBegin, None))
            self.print_op_enter(space, info.name, info.args)

        elif isinstance(event, trace.CallFinished):
            info = event.callinfo
            self.print_op_leave(space, info.name, event.res)
            self.indent_state.pop()

        elif isinstance(event, trace.CallException):
            info = event.callinfo

            self.print_op_exc(info.name, event.ex, space)
            self.indent_state.pop()                

    def get_last_frame(self):
        for c, t, f in reversed(self.indent_state):
            if f is not None:
                return f
            
print_result = ResultPrinter().print_result

## XXX Sort out for next release :-(

## def isinstance2(space, w_obj, cls):
##     return space.is_true(space.appexec([w_obj, (space.wrap(cls.__name__))],
## """(o,c):
##     return o.__class__.__name__ == c"""))

## def get_dict_repr(space, w_obj):
##     return space.str_w(space.appexec([w_obj],"""(d):
##     s = "{"
##     it = iter(d.items())
##     ii = 3
##     try:
##         k, v = it.next()
##         while True:
##             s += "%s=%s" % (k,v)
##             ii -= 1
##             if ii == 0:
##                 break
##             k, v = it.next()
##             s += ", "
##     except StopIteration:
##         pass
##     s += "}"
##     return s"""))
    
## def repr_value(space, obj):
##     """ representations for debugging purposes """        

##     # Special case true and false (from space.is_true()) - we use a
##     # different representation from a wrapped object reprs method.
##     if obj == True:
##         return "TRUE"

##     elif obj == False:
##         return "FALSE"

##     # Special case - arguments
##     from pypy.interpreter.argument import Arguments    
##     if isinstance(obj, Arguments):
##         return "Arguments XXX"
    
##     # Special case - operation error
##     from pypy.interpreter.error import OperationError
##     if isinstance(obj, OperationError):
##         return "OperationError(%s, %s)" % (repr_value(space, obj.w_type),
##                                            repr_value(space, obj.w_value))


##     if hasattr(obj, "iter"):
##         return repr([repr_value(x) for x in obj])
##     # pypy isintacnce macro type
##       # if dict/list/tuple
##          # iter over first 3 types
##     try:
##         if isinstance2(space, obj, dict):
##             return simple_repr(obj)
##         if isinstance2(space, obj, tuple):
##             return simple_repr2(obj)
##         if isinstance2(space, obj, list):
##             return simple_repr2(obj)
##     except:
##         pass

##     # Ok belows might take a long time...
    
##     # Try object's repr
##     try:
##         return space.str_w(space.repr(obj))
##     except:
##         pass

##     # Arggh - unwrap repr
##     try:
##         return repr(space.unwrap(obj))
##     except:
##         pass

##     # Give up...
##     return repr(obj)


##     res = simple_repr(obj)

##     try:
##         from pypy.interpreter.baseobjspace import W_Root
##         from pypy.interpreter.argument import Argument
##         if isinstance(obj, W_Root):
##             return simple_repr(space.unwrap(obj))

##         if isinstance(obj, Argument):
##             args_w, kwds_w = obj.unpack()
##             res = "Argument("
##             res += ", ".join([repr_value(ii) for ii in args_w])
##             res += ")"
##     except:
##         pass


##     elif space.is_true(space.appexec([w_value, space.wrap("keys")], """(x,y):
##     return hasattr(x,y)""")):
##         res = "Dict(%s)" % (space.str_w(space.repr(space.call_method(w_value, "keys")))[:40])


##     except:
##         try:
##             # XXX Sure this won't go down well - didn't really want
##             # to clutter up the interpeter code 
##             from pypy.interpreter.function import Function, Method
##             from pypy.interpreter.eval import Code
            
##             if isinstance(w_value, Function):
##                 res = "Function(%s)" % value.name
                
##             if isinstance(w_value, Method):
##                 res = "Method(%s)" % value.w_function.name

##             raise Exception, "XXX only certain types or toooo slow"
##         except:
##             res = str(w_value)

##     return res[:80]


def simple_repr(space, obj):
    res = repr(obj)
    if len(res) > 80:
        res = res[:76] + "..."
    return res
repr_value = simple_repr

# __________________________________________________________________________

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

    from pypy.objspace import trace
    from pypy.tool import option
    args = option.process_options(option.get_standard_options(),
                                  option.Options)

    # Create objspace...
    space = option.objspace()

    # Wrap up our space, with a trace space
    tspace = trace.create_trace_space(space)

    def func(x):
        count = 0
        for ii in range(x):
            count += ii
        return count

    # Note includes lazy loading of builtins
    res = perform_trace(tspace, func, tspace.wrap(5))
    print "Result:", res
