from py.__impl__.magic import exprinfo
import py
py.magic.autopath()
from pypy.objspace.std import StdObjSpace
from pypy.interpreter.gateway import app2interp, interp2app
from pypy.interpreter.argument import Arguments

class AppRunnerFrame:

    def __init__(self, space, w_globals, w_locals):
        self.space = space
        self.w_globals = w_globals
        self.w_locals = w_locals

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
    def app_getmyassertion():
        class MyAssertionError(AssertionError):
            def __init__(self, *args):
                AssertionError.__init__(self, *args) 
                self.inspect_assertion()
        return MyAssertionError 
    getmyassertion = app2interp(app_getmyassertion)
    w_myassertion = getmyassertion(space) 

    def inspect_assertion(space, w_self): 
        pass 
        #print w_self 
        #print "got to interp-level inspect_assertion" 

    w_inspect_assertion = space.wrap(interp2app(inspect_assertion))
    space.setattr(w_myassertion, 
                  space.wrap('inspect_assertion'), 
                  w_inspect_assertion)
    return w_myassertion 

def setup_module(mod):
    mod.space = StdObjSpace()

def test_AppRunnerFrame():
    w_glob = space.newdict([])
    w_loc = space.newdict([])
    runner = AppRunnerFrame(space, w_glob, w_loc)
    exprinfo.run("f = lambda x: x+1", runner)
    exprinfo.check("isinstance(f(2), float)", runner)

def test_myexception():
    def app_test_func():
        assert 42 == 43 
    t = app2interp(app_test_func)
    f = t.get_function(space)
    #space.setitem(space.w_builtins, space.wrap('AssertionError'), 
    #              build_pytest_assertion(space)) 
    f.call_args(Arguments([]))

if __name__ == '__main__':
    test()
