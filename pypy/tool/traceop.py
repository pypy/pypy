
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
                 operations_level = 2,
                 indentor = '  ',
                 skip_bytecodes = ["PRINT_EXPR", "PRINT_ITEM", "PRINT_NEWLINE"]):
        
        # Configurable stuff
        self.indentor = indentor
        self.skip_bytecodes = skip_bytecodes
        self.operations_level = operations_level
        
        self.reset()

    def reset(self):
        # State stuff
        self.ops = Stack()
        self.frames = Stack()
        self.frame_count = 0
        self.skip_frame_count = None

    def print_line(self, line, additional_indent = 0):
        if self.skip_frame_count is not None:
            return

        if self.frame_count:
            indent = self.frame_count + additional_indent - 1
            assert (indent >= 0)
            line = (self.indentor * indent) + "|-" + line 

        print line

    def print_line_operations(self, line, additional_indent = 0):
        # Don't allow operations to be exposed if operations level is up
        # but do allow operations to be printed
        if len(self.ops) > self.operations_level:
            return

        self.print_line(line, additional_indent = additional_indent)
        
    def print_frame(self, print_type, frame):

        # Don't allow frames to be exposed if operations level is up
        if len(self.ops) >= self.operations_level:
            return

        code = getattr(frame, 'code', None)
        filename = getattr(code, 'co_filename', "")
        lineno = getattr(code, 'co_firstlineno', "")

        s = "<<<<<%s %s @ %s>>>>>>>" % (print_type, filename, lineno)
        self.print_line(s)        

    def print_bytecode(self, index, bytecode):

        # Don't allow bytecodes to be exposed if operations level is up
        if len(self.ops) >= self.operations_level:
            return

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

       
    def print_result(self, space, traceres):

        self.reset()

        for event in traceres.getevents():

            if isinstance(event, trace.EnterFrame):
                frame = event.frame
                self.print_frame("enter", frame)

                self.frames.push(frame)
                self.frame_count += 1
                
            elif isinstance(event, trace.LeaveFrame):
                lastframe = self.frames.pop()
                self.frame_count -= 1
                
                # Reset skip frame count?
                if self.frame_count < self.skip_frame_count:
                    self.skip_frame_count = None
                    
                self.print_frame("leave", lastframe)           
                
            elif isinstance(event, trace.ExecBytecode):

                # Reset skip frame count?
                if self.frame_count == self.skip_frame_count:
                    self.skip_frame_count = None

                frame = event.frame 
                assert (frame == self.frames.top())
                
                # Get bytecode from frame
                disresult = getdisresult(frame)
                bytecode = disresult.getbytecode(event.index)
                self.print_bytecode(event.index, bytecode)

                # When operations_level > 1, some bytecodes produce high number of
                # operations / bytecodes (usually because they have been written at app
                # level) - this hack avoids them recursing on them selves
                if bytecode.name in self.skip_bytecodes:
                    self.print_line("...", 1)
                    self.skip_frame_count = self.frame_count           

            elif isinstance(event, trace.CallBegin):
                info = event.callinfo

                self.ops.push(info)
                lastframe = self.frames.top()
                self.print_op_enter(info.name, repr_args(space, lastframe, info.args))
                self.frame_count += 1

            elif isinstance(event, trace.CallFinished):
                info = event.callinfo

                self.frame_count -= 1
                self.print_op_leave(info.name, repr_value(space, event.res))
                
                assert self.ops.pop() == event.callinfo
                    
            elif isinstance(event, trace.CallException):
                info = event.callinfo
                self.frame_count -= 1
                
                self.print_op_exc(info.name, event.ex)
                
                assert self.ops.pop() == event.callinfo

            else:
                pass

print_result = ResultPrinter().print_result

def repr_value(space, value):
    """ representations for debugging purposes """        
    res = str(value)
    try:
        # XXX Sure this won't go down well - didn't really want
        # to clutter up the interpeter code 
        from pypy.interpreter.function import Function, Method

        if isinstance(value, Function):
            res = "Function(%s, %s)" % (value.name, value.code)

        if isinstance(value, Method):
            res = "Method(%s, %s)" % (value.w_function.name, value.w_function.code)

    except Exception, exc:
        pass
    
    return res[:240]

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
    res, traceres = perform_trace(tspace, app_test, tspace.wrap(5))
    print_result(tspace, traceres)

    print "Result", res
