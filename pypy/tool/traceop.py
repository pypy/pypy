
import autopath

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

    def __init__(self, show_applevel = False, recursive_operations = False, indentor = '  '):
        
        # Configurable stuff
        self.indentor = indentor        
        self.show_applevel = show_applevel
        self.recursive_operations = recursive_operations

        # Keeps a stack of current state to handle
        # showing of applevel and recursive operations
        self.indent_state = Stack()

    def reset(self):
        self.indent_state = Stack()

    def print_line(self, line, additional_indent = 0):
        state = self.indent_state.top()
        if state is not None and not state[0]:
            return  
        
        indent_count = len([c for c, t, f in self.indent_state if c])
        if indent_count:
            indent = indent_count + additional_indent - 1
            assert (indent >= 0)
            line = (self.indentor * indent) + "|-" + line 

        print line
        
    def print_line_operations(self, line, additional_indent = 0):
        self.print_line(line, additional_indent = additional_indent)
        
    def print_frame(self, print_type, frame):

        code = getattr(frame, 'code', None)
        filename = getattr(code, 'co_filename', "")
        lineno = getattr(code, 'co_firstlineno', "")

        s = "<<<<<%s %s @ %s>>>>>>>" % (print_type, filename, lineno)
        self.print_line(s)        

    def print_bytecode(self, index, bytecode):
        s = "%2d%s%s" % (index, (self.indentor * 2), bytecode)
        self.print_line(s)

    def print_op_enter(self, name, str_args):
        s = " " * 17
        s += ">> %s%s" % (name, str_args)
        self.print_line_operations(s)
        

    def print_op_leave(self, name, str_res):
        s = " " * 20
        s += "%s =: %s" % (name, str_res)
        self.print_line_operations(s)

    def print_op_exc(self, name, exc):
        s = " " * 17
        s += "x= %s %s" % (name, exc)
        self.print_line_operations(s)

    def print_result(self, space, event_result):
        for event in event_result.getevents():
            print_event(space, event, event_result)
            
    def print_event(self, space, event_result, event):
        from pypy.objspace import trace
        
        if isinstance(event, trace.EnterFrame):
            frame = event.frame
            if self.show_applevel or not frame.code.getapplevel():
                show = True
            else:
                show = False

            self.indent_state.append((show, trace.EnterFrame, frame))
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
            self.print_bytecode(event.index, bytecode)

        elif isinstance(event, trace.CallBegin):
            lastframe = self.get_last_frame()
            info = event.callinfo

            show = True

            # Check if we are in applevel?
            if not self.show_applevel:
                if lastframe is None or lastframe.code.getapplevel():
                    show = False

            # Check if recursive operations?
            prev_indent_state = self.indent_state.top()
            if not self.recursive_operations and prev_indent_state is not None:
                if prev_indent_state[1] == trace.CallBegin:
                    show = False

            self.indent_state.append((show, trace.CallBegin, None))
            self.print_op_enter(info.name, repr_args(space,
                                                     self.get_last_frame(),
                                                     info.args))

        elif isinstance(event, trace.CallFinished):
            info = event.callinfo

            self.print_op_leave(info.name, repr_value(space, event.res))
            self.indent_state.pop()

        elif isinstance(event, trace.CallException):
            info = event.callinfo

            self.print_op_exc(info.name, event.ex)
            self.indent_state.pop()                

    def get_last_frame(self):
        for c, t, f in self.indent_state[::-1]:
            if f is not None:
                return f
            
print_result = ResultPrinter().print_result

def repr_value(space, value):
    """ representations for debugging purposes """        
    try:
        # XXX Sure this won't go down well - didn't really want
        # to clutter up the interpeter code 
        from pypy.interpreter.function import Function, Method
        from pypy.interpreter.eval import Code

        if isinstance(value, Function):
            res = "Function(%s)" % value.name

        if isinstance(value, Method):
            res = "Method(%s)" % value.w_function.name
        raise Exception, "XXX only certain types or toooo slow"
    except:
        res = str(value)
    
    return res[:80]

def repr_args(space, frame, args):
    l = []
    for arg in args:
        if frame and space.is_true(space.is_(arg, frame.w_globals)):
            l.append('globals()')
        elif frame and space.is_true(space.is_(arg, space.builtin)):
            l.append('__builtin__')
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

    from pypy.objspace import trace
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

    # Note includes lazy loading of builtins
    res = perform_trace(tspace, app_test, tspace.wrap(5))
    print "Result:", res
