import os, sys

AUTO_DEBUG = os.getenv('PYPY_DEBUG')


class PyPyError(Exception):
    "Raise this when you encounter an exceptional situation in PyPy itself."
    def __init__(self, space, operationerr):
        self.space = space
        self.operationerr = operationerr


class OperationError(Exception):
    """Interpreter-level exception that signals an exception that should be
    sent to the application level.

    OperationError instances have three public attributes (and no .args),
    w_type, w_value and application_traceback, which contain the wrapped
    type and value describing the exception, and the unwrapped list of
    (frame, instruction_position) making the application-level traceback.
    """

    def __init__(self, w_type, w_value, tb=None):
        self.w_type = w_type
        self.w_value = w_value
        self.application_traceback = tb
        self.debug_excs = []

    def match(self, space, w_check_class):
        "Check if this application-level exception matches 'w_check_class'."
        return space.exception_match(self.w_type, w_check_class)

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
            return self.application_traceback.frame
        else:
            return None

    def record_interpreter_traceback(self):
        """Records the current traceback inside the interpreter.
        This traceback is only useful to debug the interpreter, not the
        application."""
        self.debug_excs.append(sys.exc_info())

    def print_application_traceback(self, space, file=None):
        "Dump a standard application-level traceback."
        if file is None: file = sys.stderr
        self.print_app_tb_only(file)
        print >> file, self.errorstr(space)

    def print_app_tb_only(self, file):
        tb = self.application_traceback
        if tb:
            import linecache
            print >> file, "Traceback (application-level):"
            while tb is not None:
                co = tb.frame.code
                lineno = tb.lineno
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
                print >> file, "  File \"%s\"," % fname,
                print >> file, "line", lineno, "in", co.co_name
                if l:
                    if l.endswith('\n'):
                        l = l[:-1]
                    print >> file, l
                tb = tb.next

    def print_detailed_traceback(self, space=None, file=None):
        """Dump a nice detailed interpreter- and application-level traceback,
        useful to debug the interpreter."""
        if file is None: file = sys.stderr
        for i in range(len(self.debug_excs)-1, -1, -1):
            import traceback
            interpr_file = LinePrefixer(file, '||')
            print >> interpr_file, "Traceback (interpreter-level):"
            traceback.print_tb(self.debug_excs[i][2], file=interpr_file)
        if self.debug_excs:
            from pypy.tool import tb_server
            tb_server.publish_exc(self.debug_excs[-1])
        self.print_app_tb_only(file)
        if space is None:
            exc_typename = str(self.w_type)
            exc_value    = self.w_value
        else:
            w = space.wrap
            if space.is_true(space.is_(space.type(self.w_type), space.w_str)):
                exc_typename = space.unwrap(self.w_type)
            else:
                exc_typename = space.unwrap(
                    space.getattr(self.w_type, w('__name__')))
            if self.w_value == space.w_None:
                exc_value = None
            else:
                exc_value = space.unwrap(space.str(self.w_value))
            print >> file, '(application-level)',
        if not exc_value:
            print >> file, exc_typename
        else:
            print >> file, exc_typename+':', exc_value
        if AUTO_DEBUG:
            import debug
            debug.fire(self)


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

### installing the excepthook for OperationErrors
##def operr_excepthook(exctype, value, traceback):
##    if issubclass(exctype, OperationError):
##        value.debug_excs.append((exctype, value, traceback))
##        value.print_detailed_traceback()
##    else:
##        old_excepthook(exctype, value, traceback)
##        from pypy.tool import tb_server
##        tb_server.publish_exc((exctype, value, traceback))

##old_excepthook = sys.excepthook
##sys.excepthook = operr_excepthook
