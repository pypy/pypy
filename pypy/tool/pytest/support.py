import autopath
import py
from py.__impl__.magic import exprinfo
from py.code import InspectableFrame
from pypy.objspace.std import StdObjSpace
from pypy.interpreter.gateway import app2interp_temp, interp2app_temp
from pypy.interpreter.argument import Arguments
from pypy.interpreter.error import OperationError

class AppRunnerFrame(InspectableFrame):

    def __init__(self, pyframe):
        lineno = pyframe.get_last_lineno() - 1
        super(AppRunnerFrame, self).__init__(pyframe.code, lineno)
        self.space = pyframe.space
        self.w_globals = pyframe.w_globals
        self.w_locals = pyframe.getdictscope()

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
        
        runner = AppRunnerFrame(frame)
        # XXX what if the source is not available?
        msg = exprinfo.interpret(str(runner.statement.deindent()), runner)
        if msg is None:
            msg = "(inconsistenty failed then succeeded)"
        elif msg.startswith('AssertionError: '):
            msg = msg[16:]
        space.setattr(w_self, space.wrap('args'),
                      space.newtuple([space.wrap(msg)]))

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

def setup_module(mod):
    mod.space = StdObjSpace()

def somefunc(x):
    print x

def test_AppRunnerFrame():
    from pypy.interpreter.pycode import PyCode
    from pypy.interpreter.pyframe import PyFrame
    import sys
    co = PyCode()._from_code(somefunc.func_code)
    pyframe = PyFrame(space, co, space.newdict([]), None)
    runner = AppRunnerFrame(pyframe)
    exprinfo.run("f = lambda x: x+1", runner)
    msg = exprinfo.interpret("assert isinstance(f(2), float)", runner)
    assert msg.startswith("AssertionError: assert isinstance(3, float)\n"
                          " +  where 3 = ")


def test_myexception():
    def app_test_func():
        x = 6*7
        assert x == 43
    t = app2interp_temp(app_test_func)
    f = t.get_function(space)
    space.setitem(space.w_builtins, space.wrap('AssertionError'), 
                  build_pytest_assertion(space))
    try:
        f.call_args(Arguments([]))
    except OperationError, e:
        assert e.match(space, space.w_AssertionError)
        assert space.unwrap(space.str(e.w_value)) == 'assert 42 == 43'
    else:
        assert False, "got no exception!"
