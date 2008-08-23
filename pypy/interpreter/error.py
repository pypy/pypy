import os, sys
from pypy.rlib.objectmodel import we_are_translated

AUTO_DEBUG = os.getenv('PYPY_DEBUG')
RECORD_INTERPLEVEL_TRACEBACK = True


class OperationError(Exception):
    """Interpreter-level exception that signals an exception that should be
    sent to the application level.

    OperationError instances have three public attributes (and no .args),
    w_type, w_value and application_traceback, which contain the wrapped
    type and value describing the exception, and a chained list of
    PyTraceback objects making the application-level traceback.
    """

    def __init__(self, w_type, w_value, tb=None):
        if w_type is None:
            from pypy.tool.error import FlowingError
            raise FlowingError(w_value)
        self.w_type = w_type
        self.w_value = w_value
        self.application_traceback = tb
        if not we_are_translated():
            self.debug_excs = []

    def clear(self, space):
        # for sys.exc_clear()
        self.w_type = space.w_None
        self.w_value = space.w_None
        self.application_traceback = None
        if not we_are_translated():
            del self.debug_excs[:]

    def match(self, space, w_check_class):
        "Check if this application-level exception matches 'w_check_class'."
        return space.exception_match(self.w_type, w_check_class)

    def async(self, space):
        "Check if this is an exception that should better not be caught."
        return (self.match(space, space.w_SystemExit) or
                self.match(space, space.w_KeyboardInterrupt))

    def __str__(self):
        "NOT_RPYTHON: Convenience for tracebacks."
        return '[%s: %s]' % (self.w_type, self.w_value)

    def errorstr(self, space):
        "The exception class and value, as a string."
        if space is None:
            # this part NOT_RPYTHON
            exc_typename = str(self.w_type)
            exc_value    = str(self.w_value)
        else:
            w = space.wrap
            if space.is_w(space.type(self.w_type), space.w_str):
                exc_typename = space.str_w(self.w_type)
            else:
                exc_typename = space.str_w(
                    space.getattr(self.w_type, w('__name__')))
            if space.is_w(self.w_value, space.w_None):
                exc_value = ""
            else:
                try:
                    exc_value = space.str_w(space.str(self.w_value))
                except OperationError:
                    # oups, cannot __str__ the exception object
                    exc_value = "<oups, exception object itself cannot be str'd>"
        if not exc_value:
            return exc_typename
        else:
            return '%s: %s' % (exc_typename, exc_value)

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
        if not we_are_translated():
            if RECORD_INTERPLEVEL_TRACEBACK:
                self.debug_excs.append(sys.exc_info())

    def print_application_traceback(self, space, file=None):
        "NOT_RPYTHON: Dump a standard application-level traceback."
        if file is None: file = sys.stderr
        self.print_app_tb_only(file)
        print >> file, self.errorstr(space)

    def print_app_tb_only(self, file):
        "NOT_RPYTHON"
        tb = self.application_traceback
        if tb:
            import linecache
            print >> file, "Traceback (application-level):"
            while tb is not None:
                co = tb.frame.pycode
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
                    l = "    " + l.lstrip()
                    print >> file, l
                tb = tb.next

    def print_detailed_traceback(self, space=None, file=None):
        """NOT_RPYTHON: Dump a nice detailed interpreter- and
        application-level traceback, useful to debug the interpreter."""
        import traceback, cStringIO
        if file is None: file = sys.stderr
        f = cStringIO.StringIO()
        for i in range(len(self.debug_excs)-1, -1, -1):
            print >> f, "Traceback (interpreter-level):"
            traceback.print_tb(self.debug_excs[i][2], file=f)
        f.seek(0)
        debug_print(''.join(['|| ' + line for line in f.readlines()]), file)
        if self.debug_excs:
            from pypy.tool import tb_server
            tb_server.publish_exc(self.debug_excs[-1])
        self.print_app_tb_only(file)
        print >> file, '(application-level)', self.errorstr(space)
        if AUTO_DEBUG:
            import debug
            debug.fire(self)

    def normalize_exception(self, space):
        """Normalize the OperationError.  In other words, fix w_type and/or
        w_value to make sure that the __class__ of w_value is exactly w_type.
        """
        w_type  = self.w_type
        w_value = self.w_value
        if space.full_exceptions:
            while space.is_true(space.isinstance(w_type, space.w_tuple)):
                w_type = space.getitem(w_type, space.wrap(0))
        if space.full_exceptions and (
                space.is_true(space.abstract_isclass(w_type)) and 
                space.is_true(space.issubtype(w_type, space.w_BaseException))):
            if space.is_w(w_value, space.w_None):
                # raise Type: we assume we have to instantiate Type
                w_value = space.call_function(w_type)
                w_type = space.abstract_getclass(w_value)
            else:
                w_valuetype = space.abstract_getclass(w_value)
                if space.is_true(space.abstract_issubclass(w_valuetype,
                                                           w_type)):
                    # raise Type, Instance: let etype be the exact type of value
                    w_type = w_valuetype
                else:
                    if space.full_exceptions and space.is_true(
                        space.isinstance(w_value, space.w_tuple)):
                        # raise Type, tuple: assume the tuple contains the
                        #                    constructor args
                        w_value = space.call(w_type, w_value)
                    else:
                        # raise Type, X: assume X is the constructor argument
                        w_value = space.call_function(w_type, w_value)
                    w_type = space.abstract_getclass(w_value)

        elif space.full_exceptions and space.is_w(space.type(w_type),
                                                  space.w_str):
            space.warn("raising a string exception is deprecated", 
                       space.w_DeprecationWarning)

        elif space.full_exceptions and space.is_true(space.isinstance(w_type, 
                                                     space.w_BaseException)):
            if not space.is_w(w_value, space.w_None):
                raise OperationError(space.w_TypeError,
                                     space.wrap("instance exception may not "
                                                "have a separate value"))
            w_value = w_type
            w_type = space.abstract_getclass(w_value)

        else:
            if space.full_exceptions:
                msg = ("exceptions must be classes, or instances,"
                    "or strings (deprecated) not %s" % (w_type.typedef.name))
                raise OperationError(space.w_TypeError, space.wrap(msg))

        self.w_type  = w_type
        self.w_value = w_value

    def write_unraisable(self, space, where, w_object=None):
        if w_object is None:
            objrepr = ''
        else:
            try:
                objrepr = space.str_w(space.repr(w_object))
            except OperationError:
                objrepr = '?'
        msg = 'Exception "%s" in %s%s ignored\n' % (self.errorstr(space),
                                                    where, objrepr)
        try:
            space.call_method(space.sys.get('stderr'), 'write', space.wrap(msg))
        except OperationError:
            pass   # ignored


# Utilities
from pypy.tool.ansi_print import ansi_print

def debug_print(text, file=None, newline=True):
    # 31: ANSI color code "red"
    ansi_print(text, esc="31", file=file, newline=newline)

def wrap_oserror(space, e, exception_name='w_OSError'): 
    assert isinstance(e, OSError) 
    errno = e.errno
    try:
        msg = os.strerror(errno)
    except ValueError:
        msg = 'error %d' % errno
    exc = getattr(space, exception_name)
    w_error = space.call_function(exc,
                                  space.wrap(errno),
                                  space.wrap(msg))
    return OperationError(exc, w_error)
wrap_oserror._annspecialcase_ = 'specialize:arg(2)'

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
