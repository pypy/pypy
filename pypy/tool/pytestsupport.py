import autopath
import py
from py.__impl__.magic import exprinfo
from pypy.interpreter.gateway import interp2app_temp
from pypy.interpreter.error import OperationError

# ____________________________________________________________

class AppFrame(py.code.Frame):

    def __init__(self, pyframe):
        self.code = py.code.Code(pyframe.code)
        self.lineno = pyframe.get_last_lineno() - 1
        self.space = pyframe.space
        self.w_globals = pyframe.w_globals
        self.w_locals = pyframe.getdictscope()
        self.f_locals = self.w_locals   # for py.test's recursion detection

    def eval(self, code, **vars):
        space = self.space
        for key, w_value in vars.items():
            space.setitem(self.w_locals, space.wrap(key), w_value)
        return space.eval(code, self.w_globals, self.w_locals)

    def exec_(self, code, **vars):
        space = self.space
        for key, w_value in vars.items():
            space.setitem(self.w_locals, space.wrap(key), w_value)
        space.exec_(code, self.w_globals, self.w_locals)

    def repr(self, w_value):
        return self.space.unwrap(self.space.repr(w_value))

    def is_true(self, w_value):
        return self.space.is_true(w_value)


class AppExceptionInfo(py.code.ExceptionInfo):
    """An ExceptionInfo object representing an app-level exception."""

    def __init__(self, space, operr):
        self.space = space
        self.operr = operr
        self.exprinfo = None

    def __str__(self):
        return '(app-level) ' + self.operr.errorstr(self.space)

    def reinterpret(self):
        # XXX we need to solve a general problem: how to prevent
        #     reinterpretation from generating a different exception?
        #     This problem includes the fact that exprinfo will generate
        #     its own long message that looks like
        #        OperationError:   << [<W_TypeObject(NameError)>: W_StringObj...
        #     which is much less nice than the one produced by str(self).
        # XXX this reinterpret() is only here to prevent reinterpretation.
        return self.exprinfo

    def __iter__(self):
        tb = self.operr.application_traceback
        while tb is not None:
            yield AppTracebackEntry(tb)
            tb = tb.next

class AppTracebackEntry(py.code.TracebackEntry):
    def __init__(self, tb):
        self.frame = AppFrame(tb.frame)
        self.lineno = tb.lineno - 1

# ____________________________________________________________

def build_pytest_assertion(space):
    def my_init(space, w_self, __args__):
        "Our new AssertionError.__init__()."
        w_parent_init = space.getattr(w_BuiltinAssertionError,
                                      space.wrap('__init__'))
        space.call_args(w_parent_init, __args__.prepend(w_self))
        framestack = space.getexecutioncontext().framestack
        frame = framestack.top(0)
        # Argh! we see app-level helpers in the frame stack!
        #       that's very probably very bad...
        assert frame.code.co_name == 'app_normalize_exception'
        frame = framestack.top(1)
        
        runner = AppFrame(frame)
        try:
            source = runner.statement
            source = str(source).strip()
        except py.path.NotFound:
            source = None
        if source:
            msg = exprinfo.interpret(source, runner, should_fail=True)
            space.setattr(w_self, space.wrap('args'),
                          space.newtuple([space.wrap(msg)]))
            w_msg = space.wrap(msg)
        else:
            w_msg = space.w_None
        space.setattr(w_self, space.wrap('msg'), w_msg)

    # build a new AssertionError class to replace the original one.
    w_BuiltinAssertionError = space.getitem(space.w_builtins,
                                            space.wrap('AssertionError'))
    w_metaclass = space.type(w_BuiltinAssertionError)
    w_init = space.wrap(interp2app_temp(my_init))
    w_dict = space.newdict([])
    space.setitem(w_dict, space.wrap('__init__'), w_init)
    return space.call_function(w_metaclass,
                               space.wrap('AssertionError'),
                               space.newtuple([w_BuiltinAssertionError]),
                               w_dict)

def pypyraises(space, w_ExpectedException, w_expr, __args__):
    """A built-in function providing the equivalent of py.test.raises()."""
    args_w, kwds_w = __args__.unpack()
    if space.is_true(space.isinstance(w_expr, space.w_str)):
        if args_w:
            raise OperationError(space.w_TypeError,
                                 space.wrap("raises() takes no argument "
                                            "after a string expression"))
        expr = space.unwrap(w_expr)
        source = py.code.Source(expr)
        frame = space.executioncontext.framestack.top()
        w_locals = frame.getdictscope()
        w_locals = space.call_method(w_locals, 'copy')
        for key, w_value in kwds_w.items():
            space.setitem(w_locals, space.wrap(key), w_value)
        try:
            space.call_method(space.w_builtin, 'eval',
                              space.wrap(str(source)),
                              frame.w_globals,
                              w_locals)
        except OperationError, e:
            if e.match(space, w_ExpectedException):
                return space.sys.exc_info()
            raise
    else:
        try:
            space.call_args(w_expr, __args__)
        except OperationError, e:
            if e.match(space, w_ExpectedException):
                return space.sys.exc_info()
            raise
    raise OperationError(space.w_AssertionError,
                         space.wrap("DID NOT RAISE"))

app_raises = interp2app_temp(pypyraises)
