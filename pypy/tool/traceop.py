#
# support code for the trace object space
#
import autopath

import sys


class Stack(list):
    push = list.append

    def pop(self):
        return super(Stack, self).pop(-1)

    def top(self):
        try:
            return self[-1]
        except IndexError:
            return None

class ResultPrinter(object):

    def __init__(self,
                 indentor = '  ',
                 repr_type_simple = True,
                 show_bytecode = True,
                 output_filename = None,
                 tree_pos_indicator = "|-",
                 show_hidden_applevel = False,
                 recursive_operations = False,
                 show_wrapped_consts_bytecode = True,
                 **kwds
                 ):

        if output_filename is None:
            self.out = sys.stdout
        else:
            self.out = open(output_filename, "w")
            
        # Configurable stuff
        self.indentor = indentor        
        self.tree_pos_indicator = tree_pos_indicator
        self.show_bytecode = show_bytecode
        self.show_hidden_applevel = show_hidden_applevel
        self.recursive_operations = recursive_operations
        self.show_wrapped_consts_bytecode = show_wrapped_consts_bytecode
        if repr_type_simple:
            self.repr_value = simple_repr
        else:
            self.repr_value = repr_value
        
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
                line = (self.indentor * indent) + self.tree_pos_indicator + line 

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
            
        code = getattr(frame, 'pycode', None)
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
        s += "(" + ", ".join([self.repr_value(space, ii) for ii in args]) + ")"
        self.print_line(s, new_line=False)
        
    def print_op_leave(self, space, name, res):
        if not self.valid_state():
            return

        if self.last_line_was_new:
            s = " " * 4
        else:
            s = "  "

        s += "-> %s" % self.repr_value(space, res)
        self.print_line(s)

    def print_op_exc(self, name, exc, space):
        if not self.valid_state():
            return

        if self.last_line_was_new:
            s = " " * 4
        else:
            s = "  "
        s += "-> <raised> (%s)" % self.repr_value(space, exc)

        self.print_line(s)
            
    def print_event(self, space, event_result, event):
        from pypy.objspace import trace
        
        if isinstance(event, trace.EnterFrame):
            frame = event.frame
            if self.show_hidden_applevel or not frame.pycode.hidden_applevel:
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
                if lastframe is None or lastframe.pycode.hidden_applevel:
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
        for c, t, f in self.indent_state[::-1]:
            if f is not None:
                return f

class ResultPrinterVerbose(ResultPrinter):
    """ Puts result on same line """
    def print_op_enter(self, space, name, args):
        if not self.valid_state():
            return

        s = " " * 4
        s += "%s" % name
        s += "(" + ", ".join([self.repr_value(space, ii) for ii in args]) + ")"
        self.print_line(s)

    def print_op_exc(self, name, exc, space):
        if not self.valid_state():
            return

        if self.last_line_was_new:
            s = " " * 4
        else:
            s = "  "
        s += "x-> %s" % self.repr_value(space, exc)

        self.print_line(s)

    
def simple_repr(space, obj):
    res = repr(obj)
    if len(res) > 80:
        res = res[:76] + "..."
    return res


def repr_value_complex(space, obj):
    """ representations - very slow """

    from pypy.interpreter.argument import Arguments    
    from pypy.interpreter.error import OperationError

    # Special case true and false (from space.is_true()) - we use a
    # different representation from a wrapped object reprs method.
    if obj is True:
        return "TRUE"

    elif obj is False:
        return "FALSE"

    if hasattr(obj, "__iter__"):
        return ", ".join([repr_value(space, ii) for ii in obj])

    # Special case - arguments
    if isinstance(obj, Arguments):
        args = [repr_value(space, ii) for ii in obj.arguments_w]
        if obj.kwds_w:
            args += ["%s = %s" % (k, repr_value(space, v))
                     for k, v in obj.kwds_w.items()]
        if not obj.w_stararg is None:
            args.append("*" + repr_value_complex(space, obj.w_stararg))
        if not obj.w_starstararg is None:
            args.append("**" + repr_value_complex(space, obj.w_starstararg))
        return "Args(%s)" % (", ".join(args))

    # Special case - operation error
    if isinstance(obj, OperationError):
        return "OpError(%s, %s)" % (repr_value(space, obj.w_type),
                                    repr_value(space, obj.w_value))

    # Try object repr
    try:
        return space.str_w(space.repr(obj))
    except:
        # Give up
        return repr(obj)


def repr_value(space, obj):
    return repr_value_complex(space, obj)[:120]

# __________________________________________________________________________

def perform_trace(tspace, app_func, *args_w):
    from pypy.interpreter.gateway import app2interp
    from pypy.interpreter.argument import Arguments    

    # Create our function
    func_gw = app2interp(app_func)
    w_func = func_gw.get_function(tspace)

    # Run the func in the trace space and return results
    tspace.settrace()
    w_result = tspace.call_function(w_func, *args_w)
    trace_result = tspace.getresult()
    tspace.settrace()
    return w_result, trace_result

if __name__ == '__main__':

    from pypy.objspace import std, trace

    # Wrap up std space, with a trace space
    tspace = trace.create_trace_space(std.Space())

    def func(x):
        count = 0
        for ii in range(x):
            count += ii
        return count

    # Note includes lazy loading of builtins
    res = perform_trace(tspace, func, tspace.wrap(5))
    print "Result:", res
