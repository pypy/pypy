import sys
import threadlocals

class ExecutionContext:

    def __init__(self, space):
        self.space = space
        self.framestack = Stack()

    def eval_frame(self, frame):
        locals = threadlocals.getlocals()
        self.framestack.push(frame)
        previous_ec = locals.executioncontext
        locals.executioncontext = self
        try:
            result = frame.eval(self)
        finally:
            locals.executioncontext = previous_ec
            self.framestack.pop()
        return result

    def get_w_builtins(self):
        if self.framestack.empty():
            return self.space.w_builtins
        else:
            return self.framestack.top().w_builtins

    def make_standard_w_globals(self):
        "Create a new empty 'globals' dictionary."
        w_key = self.space.wrap("__builtins__")
        w_value = self.get_w_builtins()
        w_globals = self.space.newdict([(w_key, w_value)])
        return w_globals

    def bytecode_trace(self, frame):
        "Trace function called before each bytecode."

    def exception_trace(self, operationerr):
        "Trace function called upon OperationError."
        operationerr.record_interpreter_traceback()
        #operationerr.print_detailed_traceback(self.space)

    def sys_exc_info(self):
        """Implements sys.exc_info().
        Return an OperationError instance or None."""
        for i in range(self.framestack.depth()):
            frame = self.framestack.top(i)
            if frame.last_exception is not None:
                return frame.last_exception
        return None


class OperationError(Exception):
    """Interpreter-level exception that signals an exception that should be
    sent to the application level.

    OperationError instances have three public attributes (and no .args),
    w_type, w_value and application_traceback, which contain the wrapped
    type and value describing the exception, and the unwrapped list of
    (frame, instruction_position) making the application-level traceback.
    """

    def __init__(self, w_type, w_value):
        self.w_type = w_type
        self.w_value = w_value
        self.application_traceback = []
        self.debug_tbs = []

    def record_application_traceback(self, frame, last_instruction):
        self.application_traceback.append((frame, last_instruction))

    def match(self, space, w_check_class):
        "Check if this application-level exception matches 'w_check_class'."
        return space.is_true(space.exception_match(self.w_type, w_check_class))

    def __str__(self):
        "Convenience for tracebacks."
        return '[%s: %s]' % (self.w_type, self.w_value)

    def errorstr(self, space):
        "The exception class and value, as a string."
        exc_type  = space.unwrap(
            space.getattr(self.w_type, space.wrap('__name__')))
        exc_value = space.unwrap(space.str(self.w_value))
        return '%s: %s' % (exc_type, exc_value)

    def getframe(self):
        "The frame this exception was raised in, or None."
        if self.application_traceback:
            frame, last_instruction = self.application_traceback[0]
            return frame
        else:
            return None

    def record_interpreter_traceback(self):
        """Records the current traceback inside the interpreter.
        This traceback is only useful to debug the interpreter, not the
        application."""
        self.debug_tbs.append(sys.exc_info()[2])

    def print_application_traceback(self, space, file=None):
        "Dump a standard application-level traceback."
        if file is None: file = sys.stderr
        self.print_app_tb_only(file)
        print >> file, self.errorstr(space)

    def print_app_tb_only(self, file):
        tb = self.application_traceback[:]
        if tb:
            import linecache
            tb.reverse()
            print >> file, "Traceback (application-level):"
            for f, i in tb:
                co = f.bytecode
                lineno = offset2lineno(co, i)
                fname = co.co_filename
                if fname.startswith('<inline>\n'):
                    lines = fname.split('\n')
                    fname = lines[0].strip()
                    try:
                        l = lines[lineno]
                    except IndexError:
                        l = ''
                else:
                    l = linecache.getline(fname, lineno)
                print >> file, "  File", `fname`+',',
                print >> file, "line", lineno, "in", co.co_name
                if l:
                    if l.endswith('\n'):
                        l = l[:-1]
                    print >> file, l

    def print_detailed_traceback(self, space=None, file=None):
        """Dump a nice detailed interpreter- and application-level traceback,
        useful to debug the interpreter."""
        if file is None: file = sys.stderr
        for i in range(len(self.debug_tbs)-1, -1, -1):
            import traceback
            interpr_file = LinePrefixer(file, '||')
            print >> interpr_file, "Traceback (interpreter-level):"
            traceback.print_tb(self.debug_tbs[i], file=interpr_file)
        self.print_app_tb_only(file)
        if space is None:
            exc_typename = str(self.w_type)
            exc_value    = self.w_value
        else:
            w = space.wrap
            exc_typename  = space.unwrap(
                space.getattr(self.w_type, w('__name__')))
            exc_value = space.unwrap(space.str(self.w_value))
            print >> file, '(application-level)',
        if exc_value is None:
            print >> file, exc_typename
        else:
            print >> file, exc_typename+':', exc_value


class NoValue(Exception):
    """Raised to signal absence of value, e.g. in the iterator accessing
    method 'op.next()' of object spaces."""


# Utilities

def inlinecompile(source, space, symbol='exec'):
    """Compile the given 'source' string.
    This function differs from the built-in compile() because it abuses
    co_filename to store a copy of the complete source code.
    This lets OperationError.print_application_traceback() print the
    actual source line in the traceback."""
    compile = space.builtin.compile
    w = space.wrap
    return compile(w(source), w('<inline>\n%s'%source), w(symbol), w(0), w(0))


def offset2lineno(c, stopat):
    tab = c.co_lnotab
    line = c.co_firstlineno
    addr = 0
    for i in range(0, len(tab), 2):
        addr = addr + ord(tab[i])
        if addr > stopat:
            break
        line = line + ord(tab[i+1])
    return line

class LinePrefixer:
    """File-like class that inserts a prefix string
    at the beginning of each line it prints."""
    def __init__(self, file, prefix):
        self.file = file
        self.prefix = prefix
        self.linestart = True
    def write(self, data):
        if self.linestart:
            self.file.write(self.prefix)
        if data.endswith('\n'):
            data = data[:-1]
            self.linestart = True
        else:
            self.linestart = False
        self.file.write(data.replace('\n', '\n'+self.prefix))
        if self.linestart:
            self.file.write('\n')

class Stack:
    """Utility class implementing a stack."""

    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop()

    def top(self, position=0):
        """'position' is 0 for the top of the stack, 1 for the item below,
        and so on.  It must not be negative."""
        return self.items[~position]

    def depth(self):
        return len(self.items)

    def empty(self):
        return not self.items

    def clone(self):
        s = Stack()
        s.items = self.items[:]
        return s


# installing the excepthook for OperationErrors
def operr_excepthook(exctype, value, traceback):
    if issubclass(exctype, OperationError):
        value.debug_tbs.append(traceback)
        value.print_detailed_traceback()
    else:
        old_excepthook(exctype, value, traceback)
old_excepthook = sys.excepthook
sys.excepthook = operr_excepthook
